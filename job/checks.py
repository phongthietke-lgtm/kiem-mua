"""13 tiêu chí (A–E) cho một mã. Hàm thuần: nhận dữ liệu thô của Sources, trả dòng {id, s, t, d[, links]}.
Nhóm A là tin UBCKNN (cổ tức / tăng vốn), thay tin của app information theo yêu cầu 26/09/2026.

Trạng thái `s`: ok (đạt) · no (chưa đạt) · warn (cảnh báo đỏ, không tính điểm) · na (thiếu dữ liệu, không tính)
· info (dòng tham khảo). Điểm = số ok / số (ok + no).

Luật lấy đúng như app gốc (đã soát 26/09/2026):
  POC 10 & 20 phiên  price-path/docs/app.js:345 profileChart → bins[poc][0] + bin/2 (hai dòng, chốt 26/09)
  "mua đẩy giá lên"  price-path/docs/app.js:502 fvForce → flow=(mua−bán)/(mua+bán) ≥ 5 % và giá > +0,3 %
  CVD                price-path/docs/app.js:612 fvCvd → cộng dồn mua−bán theo phiên
  cá mập             lệnh gộp ≥ 500 triệu đồng (price-path/zone/collect.py, order-flow/flow/ticks.py)
  Spring #2          bỏ hẳn, không chấm, không vẽ (người dùng chốt 26/09)
  Cá mập             "mua > bán" thay cho "> 50 % KL ngày" (ngưỡng cũ 0/39 mã đạt phiên 25/09; chốt 26/09)
"""
from __future__ import annotations

from datetime import date, timedelta

from .trend import ema as _ema, supertrend as _supertrend

OK, NO, WARN, NA, INFO = "ok", "no", "warn", "na", "info"
FLOW_T, PX_FLAT = 0.05, 0.003      # ngưỡng fvForce của price-path
BREAKOUT = 0.02                     # "bứt phá tăng > 2 %" — yêu cầu của anh
WINDOW = 5                          # "cùng chiều đi lên": so với 5 phiên trước
WY_LOOKBACK = 20
WY_GOOD = {"sc": "SC", "spring3": "Spring #3", "test": "Test sau Spring"}
CHART_N = 46
POC_WINDOWS = ("10", "20")
SSC_DAYS = 30                       # hồ sơ phát hành còn "nóng" tới ngày chốt quyền, thường vài tuần

GROUPS = {"A": "Tin UBCKNN", "B": "Nến & xu hướng", "C": "Vùng giá & dòng tiền", "D": "Wyckoff", "E": "Order flow"}


def R(id_: str, s: str, t: str, d: str = "", **kw) -> dict:
    return {"id": id_, "s": s, "t": t, "d": d, **kw}


# ---------------------------------------------------------------- định dạng kiểu Việt
def f2(x: float) -> str:
    return f"{x:,.2f}".replace(",", " ").replace(".", ",")


def pct(x: float) -> str:
    return f"{x * 100:+.1f}%".replace(".", ",").replace("-", "−")


def vol(x: float, sign: bool = True) -> str:
    if not x:
        return "0"
    a = abs(x)
    s = f"{a / 1e6:.2f} tr" if a >= 1e6 else f"{a / 1e3:.0f} ng"
    s = s.replace(".", ",")
    return (("+" if x > 0 else "−") + s) if sign else s


def dm(d: str) -> str:
    return f"{d[8:10]}/{d[5:7]}"


def rising(xs: list) -> bool | None:
    xs = [x for x in xs if x is not None]
    return None if len(xs) < 3 else xs[-1] > xs[0]


def arrow(up: bool | None) -> str:
    return "↑" if up else "↓"


# ---------------------------------------------------------------- A. tin UBCKNN (qua KingStock)
def ssc(sym: str, notices: list | None, trade_date: str, stale: str | None) -> list[dict]:
    """Đạt khi UBCKNN đã nhận hồ sơ phát hành cổ phiếu trả cổ tức hoặc tăng vốn từ VCSH của mã trong SSC_DAYS ngày.
    KingStock rút mã từ thân bài; ~1/6 tin không ghi mã nên khớp theo tên công ty — có thể sót (xem memory
    kingstock-ssc-issuance). Tin chỉ có từ 11/09/2026, ngày bộ đọc bắt đầu chạy."""
    t = f"Tin UBCKNN: cổ tức / tăng vốn ({SSC_DAYS} ngày)"
    if notices is None:
        return [R("ssc", NA, t, stale or "Chưa đọc được tin UBCKNN từ KingStock")]
    since = (date.fromisoformat(trade_date) - timedelta(days=SSC_DAYS)).isoformat()
    mine = sorted((n for n in notices if n.get("symbol") == sym and since <= (n.get("date") or "") <= trade_date),
                  key=lambda n: n["date"], reverse=True)
    kinds = {"dividend": "Trả cổ tức bằng cổ phiếu", "equity": "Tăng vốn từ vốn chủ sở hữu"}
    return [R("ssc", OK if mine else NO, t,
              " · ".join(f"{kinds.get(n.get('kind'), n.get('kind_label', ''))} ({dm(n['date'])})" for n in mine)
              or "Không có hồ sơ phát hành nào",
              links=[{"t": n.get("title", ""), "u": n.get("url", ""), "src": "ssc.gov.vn"} for n in mine[:3]])]


# ---------------------------------------------------------------- B. candle-radar
def candle(sym: str, latest: dict | None, days: dict, stale: str | None) -> list[dict]:
    if latest is None or stale:
        m = stale or "Chưa đọc được candle-radar"
        return [R("cdl", NA, "Cụm nến mua 3 phiên", m), R("st", NA, "Supertrend xanh", m), R("ema", NA, "Giá trên EMA10", m)]
    hits = [f"{s.get('name')} ({dm(d)})" for d in sorted(days, reverse=True) for s in days[d]
            if s.get("symbol") == sym and s.get("kind") == "candle" and s.get("direction") == "buy"]
    out = [R("cdl", OK if hits else NO, "Cụm nến mua 3 phiên", ", ".join(hits) or "Không có mẫu nến mua nào trong 3 phiên")]
    t = next((x for x in latest.get("trend") or [] if x.get("symbol") == sym), None)
    if not t:
        m = "Mã bị candle-radar loại hôm nay (thiếu nến)"
        return out + [R("st", NA, "Supertrend xanh", m), R("ema", NA, "Giá trên EMA10", m)]
    out.append(R("st", OK if t["up"] else NO, "Supertrend xanh",
                 f"{'Xanh' if t['up'] else 'Đỏ'} {t['days']} phiên (từ {dm(t['since'])}) · đường {f2(t['line'])}"))
    out.append(R("ema", OK if t["above_ema"] else NO, "Giá trên EMA10", f"EMA10 {f2(t['ema'])}"))
    return out


# ---------------------------------------------------------------- C. price-path
def pricepath(sym: str, pp: dict | None, trade_date: str, stale: str | None) -> tuple[list[dict], dict]:
    """Trả (các dòng, {"10": POC10, "20": POC20}) — POC dùng lại cho biểu đồ."""
    ids = [("poc10", "Giá trên POC 10 phiên"), ("poc20", "Giá trên POC 20 phiên"), ("whale", "Cá mập mua > cá mập bán"),
           ("push", "Mua đẩy giá lên & tăng > 2%"), ("pp_cvd", "Giá & CVD cùng lên 5 phiên")]
    s = (pp or {}).get("symbols", {}).get(sym)
    why = stale or (None if s else "Chưa đọc được price-path" if pp is None else "Mã không có trong price-path")
    if not why and s.get("price_date") != trade_date:
        why = f"Giá price-path dừng ở {dm(s['price_date'])}"
    if why:
        return [R(i, NA, t, why) for i, t in ids], {}
    out, pocs = [], {}
    for n in POC_WINDOWS:                   # anh chọn 26/09: POC 10 và 20 phiên, mỗi cái một dòng (bỏ 40 phiên)
        pr = (s.get("profiles") or {}).get(n)
        if not pr or pr.get("poc") is None:
            out.append(R(f"poc{n}", NA, f"Giá trên POC {n} phiên", "price-path không có hồ sơ này"))
            continue
        poc = pr["bins"][pr["poc"]][0] + pr["bin"] / 2
        pocs[n] = round(poc, 3)
        out.append(R(f"poc{n}", OK if s["price"] > poc else NO, f"Giá trên POC {n} phiên",
                     f"Giá {f2(s['price'])} · POC {n} phiên {f2(poc)}"))

    d, fp = s["daily"][-1], s["fp"][-1]
    if d.get("est") or d.get("no_side") or not d.get("total") or fp[0] != d["d"] or fp[1]:
        out.append(R("whale", NA, ids[2][1], "Phiên ước lượng / không có chiều mua-bán"))
    else:
        bb = sum(lv[4] or 0 for lv in fp[6])
        bs = sum(lv[5] or 0 for lv in fp[6])
        out.append(R("whale", OK if bb > bs else NO, ids[2][1],
                     f"Mua {vol(bb, False)} · bán {vol(bs, False)} cp · cá mập mua = {bb / d['total'] * 100:.0f}% KL ngày"))

    if d.get("no_side") or not (d["buy"] + d["sell"]) or not d.get("pc"):
        out.append(R("push", NA, ids[3][1], "Không có chiều mua-bán"))
    else:
        flow = (d["buy"] - d["sell"]) / (d["buy"] + d["sell"])
        chg = d["c"] / d["pc"] - 1
        pushing = flow >= FLOW_T and chg > PX_FLAT
        state = "mua đẩy giá lên" if pushing else "không phải mua đẩy"
        out.append(R("push", OK if pushing and chg > BREAKOUT else NO, ids[3][1],
                     f"Dòng chủ động {pct(flow)} ({state}) · giá {pct(chg)}"))

    if s["daily"][-1].get("no_side"):
        out.append(R("pp_cvd", NA, ids[4][1], "Không có chiều mua-bán"))
    else:
        acc, cvd = 0, []
        for x in s["daily"]:
            acc += (x["buy"] or 0) - (x["sell"] or 0)
            cvd.append(acc)
        cv, px = cvd[-(WINDOW + 1):], [x["c"] for x in s["daily"][-(WINDOW + 1):]]
        up_c, up_p = rising(cv), rising(px)
        out.append(R("pp_cvd", OK if up_c and up_p else NO, ids[4][1],
                     f"Giá {arrow(up_p)} {pct(px[-1] / px[0] - 1)} · CVD {arrow(up_c)} {vol(cv[-1] - cv[0])} cp"))
    return out, pocs


# ---------------------------------------------------------------- D. wyckoff-radar
def wyckoff(sym: str, wy_bars: dict | None, wy_latest: dict | None, stale: str | None) -> list[dict]:
    t = "SC / Spring #3 / Test (20 phiên)"
    if wy_bars is None or stale:
        return [R("wy", NA, t, stale or "Chưa đọc được wyckoff-radar")]
    bars = (wy_bars.get("bars") or {}).get(sym)
    if not bars:
        return [R("wy", NA, t, "Mã bị wyckoff-radar loại hôm nay (thiếu nến)")]
    cutoff = bars[-WY_LOOKBACK][0] if len(bars) >= WY_LOOKBACK else bars[0][0]
    ev = [(d, e) for d, e in (wy_bars.get("marks") or {}).get(sym, []) if d >= cutoff]
    good = [f"{WY_GOOD[e]} {dm(d)}" for d, e in ev if e in WY_GOOD]
    out = [R("wy", OK if good else NO, t, ", ".join(good) or "Không có")]
    b = next((x for x in (wy_latest or {}).get("board") or [] if x.get("symbol") == sym), None)
    if b and b.get("phase") not in (None, "-") and b.get("tr_lo") is not None:
        out.append(R("wy_phase", INFO, "Pha Wyckoff",
                     f"Pha {b['phase']} · vùng {f2(b['tr_lo'])}–{f2(b['tr_hi'])} · {b['tr_age']} phiên"))
    return out


# ---------------------------------------------------------------- E. order-flow
def orderflow(sym: str, of_latest: dict | None, of_daily: dict, trade_date: str, stale: str | None) -> list[dict]:
    ids = [("delta", "Delta dương · mua CĐ > bán CĐ"), ("cvd", "CVD dương"),
           ("vwap", "Giá trên VWAP"), ("of_cvd", "CVD & giá cùng lên 5 phiên")]
    it = next((x for x in (of_latest or {}).get("items") or [] if x.get("sym") == sym), None)
    dy = (of_daily.get(sym) or {}).get("days") or []
    why = stale or (None if it else "Chưa đọc được order-flow" if of_latest is None else "Mã không có trong order-flow")
    if not why and it.get("day") != trade_date:
        why = f"order-flow dừng ở {dm(it['day'])}"
    if not why and it.get("no_side"):
        why = "Không có chiều mua-bán"
    if why:
        return [R(i, NA, t, why) for i, t in ids]
    out = [R("delta", OK if it["delta"] > 0 else NO, ids[0][1],
             f"Delta {vol(it['delta'])} cp · mua {it['share']:.0f}% / bán {100 - it['share']:.0f}%")]
    last = dy[-1] if dy and dy[-1].get("d") == trade_date else None
    if not last:
        return out + [R(i, NA, t, "Thiếu file ngày của order-flow") for i, t in ids[1:]]
    out.append(R("cvd", OK if last["cvd"] > 0 else NO, ids[1][1], f"CVD cộng dồn {vol(last['cvd'])} cp ({len(dy)} phiên)"))
    out.append(R("vwap", OK if last["cvw"] > 0 else NO, ids[2][1],
                 f"Đóng {f2(last['close'])} · VWAP {f2(last['vw'])} ({last['cvw']:+.2f}%)".replace(".", ",").replace("-", "−")))
    cv = [x["cvd"] for x in dy[-(WINDOW + 1):]]
    px = [x["close"] for x in dy[-(WINDOW + 1):]]
    up_c, up_p = rising(cv), rising(px)
    if up_c is None:
        out.append(R("of_cvd", NA, ids[3][1], f"order-flow mới có {len(dy)} phiên"))
    else:
        out.append(R("of_cvd", OK if up_c and up_p else NO, ids[3][1],
                     f"Giá {arrow(up_p)} · CVD {arrow(up_c)} ({len(cv) - 1} phiên)"))
    return out


# ---------------------------------------------------------------- biểu đồ 46 phiên
def chart(sym: str, candle_bars: dict | None, poc: dict, wy_bars: dict | None) -> dict | None:
    raw = ((candle_bars or {}).get("bars") or {}).get(sym)
    if not raw or len(raw) < 20:
        return None
    bars = [{"d": r[0], "o": r[1], "h": r[2], "l": r[3], "c": r[4]} for r in raw]
    em, st = _ema(bars), _supertrend(bars)
    k = max(0, len(bars) - CHART_N)
    first = bars[k]["d"]
    marks = [[d, e] for d, e in ((wy_bars or {}).get("marks") or {}).get(sym, [])
             if d >= first and e in WY_GOOD]
    return {"b": [[x["d"], x["o"], x["h"], x["l"], x["c"]] for x in bars[k:]],
            "ema": [round(v, 3) if v is not None else None for v in em[k:]],
            "st": [[round(x["line"], 3), 1 if x["up"] else 0] if x else None for x in st[k:]],
            "poc": poc, "marks": marks}


# ---------------------------------------------------------------- tổng hợp một mã
def score(sym: str, S, trade_date: str, stale: dict[str, str | None], with_chart: bool = True) -> dict:
    """S: job.sources.Sources. stale[nguồn] = lý do nguồn cũ (None nếu tươi)."""
    c_rows, poc = pricepath(sym, S.pp, trade_date, stale.get("pricepath"))
    groups = {
        "A": ssc(sym, S.ssc, trade_date, stale.get("ssc")),
        "B": candle(sym, S.candle, S.candle_days, stale.get("candle")),
        "C": c_rows,
        "D": wyckoff(sym, S.wy_bars, S.wy_latest, stale.get("wyckoff")),
        "E": orderflow(sym, S.of_latest, S.of_daily, trade_date, stale.get("orderflow")),
    }
    rows = [r for g in groups.values() for r in g]
    counted = [r for r in rows if r["s"] in (OK, NO)]
    wl = next((w for w in S.watchlist or [] if w.get("symbol") == sym), {})
    pps = ((S.pp or {}).get("symbols") or {}).get(sym) or {}
    of = next((x for x in (S.of_latest or {}).get("items") or [] if x.get("sym") == sym), {})
    price = pps.get("price") if pps.get("price_date") == trade_date else of.get("close")
    last = (pps.get("daily") or [{}])[-1]
    chg = of.get("chg") if of.get("day") == trade_date else (
        round((last["c"] / last["pc"] - 1) * 100, 2) if last.get("pc") and last.get("d") == trade_date else None)
    out = {
        "sym": sym, "name": wl.get("company_name") or pps.get("name") or "", "price": price, "chg": chg,
        "groups": groups, "pass": sum(r["s"] == OK for r in counted), "total": len(counted),
        "warn": sum(r["s"] == WARN for r in rows), "na": sum(r["s"] == NA for r in rows),
    }
    if with_chart:
        out["chart"] = chart(sym, S.candle_bars, poc, S.wy_bars)
    return out


def code(rec: dict) -> str:
    """Chuỗi trạng thái gọn cho daily/<ngày>.json (để sau này đo điểm cao có tốt hơn không), vd 'x|xxo|oxxo|x|ooxo' (o đạt, x chưa, ! cảnh báo, - thiếu)."""
    m = {OK: "o", NO: "x", WARN: "!", NA: "-", INFO: ""}
    return "|".join("".join(m[r["s"]] for r in g) for g in rec["groups"].values())
