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


def strong_payload(hot: list[str], board: dict, alerts: list[dict], trade_date: str, need: int) -> dict:
    """Vd: title 'Kiểm Mua · 1 mã đạt ≥ 15 tiêu chí · 25/09', body 'VPB 15/17 · TCB 16/17 (▲ KS báo MUA)'."""
    ks = {a["sym"] for a in alerts}
    bits = [f"{s} {board[s]['pass']}/{board[s]['total']}" + (" (▲ KS báo MUA)" if s in ks else "")
            + (f" ({board[s]['warn']} cảnh báo)" if board[s]["warn"] else "") for s in hot]
    return {"kind": "summary", "title": f"Kiểm Mua · {len(hot)} mã đạt ≥ {need} tiêu chí · {trade_date[8:10]}/{trade_date[5:7]}",
            "body": " · ".join(bits), "url": "./", "tag": f"km-{trade_date}", "hot": True}


def test_payload() -> dict:
    return {"kind": "test", "title": "Kiểm Mua — máy này đã nhận được",
            "body": "Sau 16:30, khi có mã đạt từ 15 tiêu chí, thông báo sẽ tới như thế này.",
            "url": "./", "tag": "km-test"}


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    subs = subscriptions()
    print(f"{len(subs)} thiết bị · VAPID {'OK' if configured() else 'THIẾU'}")
    if "--test" in sys.argv:
        print(send(test_payload(), subs))
