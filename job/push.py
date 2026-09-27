"""Web Push qua pywebpush + VAPID. Chép từ wyckoff-radar/job/push.py, bỏ phần Worker: địa chỉ máy nằm trong
Secret PUSH_SUBS_FALLBACK (điện thoại hiện đoạn mã để dán, một lần mỗi máy).

- configured() đòi CẢ HAI khoá: thiếu public key thì lỗi im lặng (bài học KingStock).
- Một thông báo tổng kết mỗi phiên, không gửi từng mã.
"""
from __future__ import annotations

import hashlib
import json
import logging

from pywebpush import WebPushException, webpush

from common.config import PUSH_SUBS_FALLBACK, VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, VAPID_SUBJECT

logger = logging.getLogger(__name__)
TTL = 16 * 3600


def configured() -> bool:
    return bool(VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY)


def subscriptions() -> list[dict]:
    if not PUSH_SUBS_FALLBACK.strip():
        return []
    try:
        subs = json.loads(PUSH_SUBS_FALLBACK)
        return subs if isinstance(subs, list) else [subs]
    except json.JSONDecodeError as exc:
        logger.error("PUSH_SUBS_FALLBACK không phải JSON: %s", exc)
        return []


def _sub_id(sub: dict) -> str:
    return hashlib.sha256(sub["endpoint"].encode()).hexdigest()[:16]


def send(payload: dict, subs: list[dict]) -> dict:
    res = {"sent": 0, "gone": 0, "failed": 0, "errors": []}
    if not configured():
        res["errors"].append("Thiếu VAPID_PUBLIC_KEY/VAPID_PRIVATE_KEY")
        return res
    data = json.dumps(payload, ensure_ascii=False)
    for sub in subs:
        try:
            webpush(subscription_info={"endpoint": sub["endpoint"], "keys": sub["keys"]}, data=data, ttl=TTL,
                    vapid_private_key=VAPID_PRIVATE_KEY, vapid_claims={"sub": VAPID_SUBJECT},
                    headers={"Urgency": "high"})
            res["sent"] += 1
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in (404, 410):
                res["gone"] += 1
            else:
                res["failed"] += 1
                res["errors"].append(f"{_sub_id(sub)}: {status} {exc}"[:200])
        except Exception as exc:  # noqa: BLE001
            res["failed"] += 1
            res["errors"].append(f"{_sub_id(sub)}: {exc}"[:200])
    return res


def summary_payload(alerts: list[dict], board: dict, trade_date: str) -> dict:
    """Vd: title 'Kiểm Mua · 3 mã báo MUA · 25/09', body 'TPB 6/12 · VDS 0/12 (1 cảnh báo) · …' — điểm cao trước."""
    rows = sorted(alerts, key=lambda a: -(board[a["sym"]]["pass"] / max(board[a["sym"]]["total"], 1)))
    bits = []
    for a in rows:
        b = board[a["sym"]]
        bits.append(f"{a['sym']} {b['pass']}/{b['total']}" + (f" ({b['warn']} cảnh báo)" if b["warn"] else ""))
    return {"kind": "summary", "title": f"Kiểm Mua · {len(alerts)} mã báo MUA · {trade_date[8:10]}/{trade_date[5:7]}",
            "body": " · ".join(bits), "url": "./", "tag": f"km-{trade_date}", "hot": True}


def test_payload() -> dict:
    return {"kind": "test", "title": "Kiểm Mua — máy này đã nhận được",
            "body": "Sau 16:30, khi KingStock có mã báo MUA, bảng soát 14 tiêu chí sẽ tới như thế này.",
            "url": "./", "tag": "km-test"}


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    subs = subscriptions()
    print(f"{len(subs)} thiết bị · VAPID {'OK' if configured() else 'THIẾU'}")
    if "--test" in sys.argv:
        print(send(test_payload(), subs))
