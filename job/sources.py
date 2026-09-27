"""Tải các nguồn. Mỗi nguồn lỗi thì ghi lỗi và trả None, không làm hỏng cả job: một app chết thì các
tiêu chí của nó thành "thiếu dữ liệu", các nhóm còn lại vẫn chấm.

Đọc phía máy chủ (GitHub Actions) vì KingStock chưa bật CORS. Tin UBCKNN (trả cổ tức / tăng vốn từ VCSH) lấy
từ KingStock /api/issuance — bộ đọc ssc.gov.vn đã chạy thật ở đó từ 11/09/2026, không cần token.
Đường dẫn/khuôn JSON đã soát trong code từng app ngày 26/09/2026 — xem README.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from common.config import (
    BROWSER_HEADERS, CANDLE, HTTP_TIMEOUT, KINGSTOCK, ORDERFLOW, PRICEPATH, WYCKOFF,
)

log = logging.getLogger(__name__)


@dataclass
class Sources:
    """Dữ liệu thô của 6 app + tình trạng từng nguồn ({ok, date, error}) để giao diện hiện chấm xanh/đỏ."""
    signals: list | None = None          # KingStock /api/signals
    watchlist: list | None = None        # KingStock /api/watchlist
    ssc: list | None = None              # KingStock /api/issuance: tin UBCKNN nhận hồ sơ phát hành
    candle: dict | None = None           # candle-radar latest.json
    candle_days: dict = field(default_factory=dict)   # ngày -> signals[] của daily/<ngày>.json
    candle_bars: dict | None = None      # candle-radar bars.json
    pp: dict | None = None               # price-path zone/latest.json
    wy_bars: dict | None = None          # wyckoff-radar bars.json (marks)
    wy_latest: dict | None = None        # wyckoff-radar latest.json (board)
    of_latest: dict | None = None        # order-flow latest.json
    of_daily: dict = field(default_factory=dict)      # mã -> daily/<mã>.json
    status: dict = field(default_factory=dict)


def _get(client: httpx.Client, url: str, headers: dict | None = None):
    r = client.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def load(now: datetime, client: httpx.Client | None = None) -> Sources:
    own = client is None
    client = client or httpx.Client(timeout=HTTP_TIMEOUT, headers=BROWSER_HEADERS, follow_redirects=True)
    S = Sources()

    def grab(name: str, fn, date_of=None):
        try:
            val = fn()
            S.status[name] = {"ok": True, "date": date_of(val) if date_of else None, "error": None}
            return val
        except Exception as exc:  # noqa: BLE001
            log.warning("nguồn %s lỗi: %s", name, exc)
            S.status[name] = {"ok": False, "date": None, "error": str(exc)[:160]}
            return None

    try:
        S.watchlist = grab("kingstock", lambda: _get(client, f"{KINGSTOCK}/api/watchlist"))
        S.signals = _safe(lambda: _get(client, f"{KINGSTOCK}/api/signals?limit=200"), S, "kingstock")
        if S.status["kingstock"]["ok"]:
            S.status["kingstock"]["date"] = now.strftime("%Y-%m-%d")

        S.ssc = grab("ssc", lambda: _get(client, f"{KINGSTOCK}/api/issuance?limit=200"),
                     lambda v: now.strftime("%Y-%m-%d"))

        S.candle = grab("candle", lambda: _get(client, f"{CANDLE}/latest.json"), lambda v: v.get("trade_date"))
        if S.candle:
            for h in (S.candle.get("history") or [])[:3]:
                d = h.get("date")
                if d == S.candle.get("trade_date"):
                    S.candle_days[d] = S.candle.get("signals") or []
                elif d:
                    try:
                        S.candle_days[d] = _get(client, f"{CANDLE}/daily/{d}.json").get("signals") or []
                    except Exception as exc:  # noqa: BLE001
                        log.info("candle daily %s: %s", d, exc)
            S.candle_bars = _safe(lambda: _get(client, f"{CANDLE}/bars.json"), S, "candle")

        S.pp = grab("pricepath", lambda: _get(client, f"{PRICEPATH}/zone/latest.json"), lambda v: v.get("trade_date"))

        S.wy_latest = grab("wyckoff", lambda: _get(client, f"{WYCKOFF}/latest.json"), lambda v: v.get("trade_date"))
        if S.wy_latest:
            S.wy_bars = _safe(lambda: _get(client, f"{WYCKOFF}/bars.json"), S, "wyckoff")

        S.of_latest = grab("orderflow", lambda: _get(client, f"{ORDERFLOW}/latest.json"), lambda v: v.get("day"))
        if S.of_latest:
            for it in S.of_latest.get("items") or []:
                try:
                    S.of_daily[it["sym"]] = _get(client, f"{ORDERFLOW}/daily/{it['sym']}.json")
                except Exception as exc:  # noqa: BLE001
                    log.info("order-flow daily %s: %s", it.get("sym"), exc)
    finally:
        if own:
            client.close()
    return S


def _safe(fn, S: Sources, name: str):
    """File phụ của một nguồn: lỗi thì đánh dấu nguồn đó hỏng một phần, không ném."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        log.warning("nguồn %s (file phụ) lỗi: %s", name, exc)
        st = S.status.setdefault(name, {"ok": True, "date": None, "error": None})
        st["error"] = (st.get("error") or "") + f" · file phụ: {str(exc)[:100]}"
        return None
