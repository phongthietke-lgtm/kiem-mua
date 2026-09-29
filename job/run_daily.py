"""Job sau phiên — GitHub Actions 16:30 T2–T6 (dự phòng 17:15, 18:45).
Local: python -m job.run_daily [--force] [--no-push] [--dry-run] [--date YYYY-MM-DD]

Luồng: tải các nguồn (KingStock + tin UBCKNN, 4 app cuối ngày) (job/sources.py) → kiểm nguồn đã có phiên hôm nay chưa → chấm 17 tiêu chí cho cả danh mục
(job/checks.py) → lọc mã KingStock báo MUA hôm nay → ghi docs/data/latest.json, daily/<ngày>.json, state.json
→ một push tổng kết nếu có mã báo mua.

Phiên cần chấm = phiên mới nhất các app cuối ngày đã có (session_date), không theo đồng hồ — GitHub có khi trễ lịch
qua nửa đêm (28/09/2026). Đã có daily/<phiên>.json thì thoát. Nếu một trong 4 app cuối ngày (candle, price-path,
wyckoff, order-flow) chưa có phiên đó thì lượt 16:30/17:15 trong chính ngày phiên thoát 0 để lần sau thử lại; từ 18:40
hoặc sang ngày sau thì chấm luôn, tiêu chí của nguồn cũ thành "thiếu dữ liệu". Lượt 08:15 sáng hôm sau bù khi cả 3
lượt chiều trễ/hỏng. LUÔN thoát mã 0: mã ≠ 0 làm bước commit bị bỏ qua (bẫy price-path 23/09/2026).
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime

from common.config import SITE_DATA, TZ

from . import checks, push, sources

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("job")

LATEST, STATE, DAILY = SITE_DATA / "latest.json", SITE_DATA / "state.json", SITE_DATA / "daily"
EOD = ("candle", "pricepath", "wyckoff", "orderflow")
FINAL_HHMM = "18:40"            # từ giờ này, nguồn nào chưa có hôm nay thì chấm luôn với "thiếu dữ liệu"
HISTORY_DAYS = 30
PUSH_MIN = 15                   # báo điện thoại khi một mã đạt từ ngần này tiêu chí (app tô xanh từ 10, docs/app.js HI)


def _load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _dump(path, obj, indent=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=indent, separators=None if indent else (",", ":")),
                    encoding="utf-8")


def stale_reasons(status: dict, trade_date: str) -> dict[str, str | None]:
    out = {}
    for name, st in status.items():
        if name == "kingstock":
            continue
        if not st.get("ok"):
            out[name] = f"Không đọc được nguồn: {st.get('error') or 'lỗi'}"
        elif name != "ssc" and st.get("date") != trade_date:          # tin UBCKNN là nguồn sống, không có "phiên"
            out[name] = f"Nguồn mới có phiên {checks.dm(st['date'])}" if st.get("date") else "Nguồn chưa có ngày"
        else:
            out[name] = None
    return out


def session_date(status: dict) -> str | None:
    """Phiên cần chấm = phiên mới nhất mà các app cuối ngày đã có — KHÔNG theo đồng hồ. GitHub có khi trễ lịch qua nửa
    đêm: 28/09/2026 cả 3 lượt chạy lúc 00:45–01:43 ngày 29/09, job cũ tìm "phiên 29/09", không nguồn nào có nên mất trắng
    phiên 28/09. Lấy theo nguồn thì lượt trễ (kể cả thứ Sáu trễ sang thứ Bảy) vẫn chấm đúng phiên còn thiếu."""
    ds = [st["date"] for n, st in status.items() if n in EOD and st.get("ok") and st.get("date")]
    return max(ds) if ds else None


def must_wait(now: datetime, trade_date: str, fresh: list) -> bool:
    """Còn nguồn chưa có phiên này: chỉ chờ lượt sau khi đang trong chính ngày phiên và trước giờ chót."""
    return len(fresh) < len(EOD) and now.strftime("%Y-%m-%d") == trade_date and now.strftime("%H:%M") < FINAL_HHMM


def strong(board: dict) -> list[str]:
    """Mã (trong cả danh mục, không chỉ mã KingStock báo MUA) đạt từ PUSH_MIN tiêu chí — điểm cao trước.
    Anh chốt 29/09/2026: đạt ≥ 15 tiêu chí mới báo điện thoại (trước đó: báo mỗi khi KingStock có mã MUA)."""
    return sorted((s for s, b in board.items() if b["pass"] >= PUSH_MIN), key=lambda s: (-board[s]["pass"], s))


def buy_alerts(signals: list | None, trade_date: str) -> list[dict]:
    """Mã KingStock báo MUA trong ngày, chưa bị huỷ; mỗi mã giữ lần báo sớm nhất."""
    seen, out = set(), []
    for s in sorted(signals or [], key=lambda x: x.get("at") or ""):
        if s.get("direction") != "buy" or s.get("date") != trade_date or s.get("invalidated") or s["symbol"] in seen:
            continue
        seen.add(s["symbol"])
        out.append({"sym": s["symbol"], "date": s["date"], "at": s.get("at"), "k": s.get("k"), "d": s.get("d"),
                    "price": s.get("price"), "confirmed": s.get("confirmed")})
    return out


def history(trade_date: str) -> list[dict]:
    """Tóm tắt các ngày trước (từ daily/*.json) cho tab Lịch sử — mới nhất trước."""
    out = []
    for p in sorted(DAILY.glob("*.json"), reverse=True)[:HISTORY_DAYS]:
        d = _load(p, None)
        if not d or d.get("trade_date") == trade_date:
            continue
        out.append({"date": d["trade_date"], "alerts": [
            {**a, **{k: d["scores"][a["sym"]][k] for k in ("pass", "total", "warn")}} for a in d.get("alerts", [])
            if a["sym"] in d.get("scores", {})]})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="chạy lại dù hôm nay đã có file / nguồn chưa đủ")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="không ghi file, không push")
    ap.add_argument("--date", help="coi ngày này là 'hôm nay' (chạy thử cuối tuần)")
    a = ap.parse_args(argv)

    now = datetime.now(TZ)
    if a.date and (DAILY / f"{a.date}.json").exists() and not a.force:
        log.info("Đã có %s.json — bỏ qua (dùng --force để chạy lại)", a.date)
        return 0

    S = sources.load(now)
    if S.signals is None and S.status.get("kingstock", {}).get("ok"):
        S.status["kingstock"]["ok"] = False
    log.info("Nguồn: %s", {k: (v["ok"], v["date"]) for k, v in S.status.items()})
    trade_date = a.date or session_date(S.status)
    if not trade_date:
        log.info("Không nguồn cuối ngày nào đọc được ngày phiên — không ghi gì")
        return 0
    day_file = DAILY / f"{trade_date}.json"
    if day_file.exists() and not a.force:
        log.info("Phiên %s đã chấm (%s) — bỏ qua (dùng --force để chạy lại)", trade_date, day_file.name)
        return 0
    stale = stale_reasons(S.status, trade_date)
    fresh = [n for n in EOD if not stale.get(n)]
    if not fresh:
        log.info("Không nguồn cuối ngày nào có phiên %s — không ghi gì", trade_date)
        return 0
    if must_wait(now, trade_date, fresh) and not a.force:
        log.info("Phiên %s: còn chờ %s — thoát để lần chạy sau thử lại", trade_date, [n for n in EOD if n not in fresh])
        return 0

    symbols = [w["symbol"] for w in S.watchlist or []] or sorted(((S.pp or {}).get("symbols") or {}).keys())
    board = {sym: checks.score(sym, S, trade_date, stale) for sym in symbols}
    alerts = [x for x in buy_alerts(S.signals, trade_date) if x["sym"] in board]
    log.info("%d mã chấm · %d mã báo MUA: %s", len(board), len(alerts),
             [(x["sym"], f"{board[x['sym']]['pass']}/{board[x['sym']]['total']}") for x in alerts])

    src = {k: {"ok": v["ok"], "date": v["date"], "stale": stale.get(k), "error": v["error"]} for k, v in S.status.items()}
    latest = {"trade_date": trade_date, "generated_at": now.isoformat(timespec="seconds"), "sources": src,
              "alerts": alerts, "board": board, "history": history(trade_date)}
    daily = {"trade_date": trade_date, "generated_at": latest["generated_at"], "sources": src, "alerts": alerts,
             "scores": {s: {"pass": b["pass"], "total": b["total"], "warn": b["warn"], "code": checks.code(b)}
                        for s, b in board.items()}}

    hot = strong(board)
    log.info("Mã đạt từ %d tiêu chí: %s", PUSH_MIN, [(s, board[s]["pass"]) for s in hot])
    pushed = {"skipped": f"không mã nào đạt từ {PUSH_MIN} tiêu chí"} if not hot else {"skipped": "--no-push"}
    if hot and not (a.no_push or a.dry_run):
        subs = push.subscriptions()
        pushed = push.send(push.strong_payload(hot, board, alerts, trade_date, PUSH_MIN), subs) | {"devices": len(subs)}
        log.info("Push: %s", pushed)

    if a.dry_run:
        log.info("--dry-run: không ghi file")
        return 0
    _dump(LATEST, latest)
    _dump(day_file, daily, indent=1)
    _dump(STATE, {"last_run": now.isoformat(timespec="seconds"), "trade_date": trade_date, "push": pushed,
                  "vapid": push.configured(), "devices": len(push.subscriptions())}, indent=1)
    log.info("Đã ghi %s (%d KB)", LATEST.name, LATEST.stat().st_size // 1024)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 — luôn thoát 0 để bước commit vẫn chạy
        log.exception("Job lỗi")
        sys.exit(0)
