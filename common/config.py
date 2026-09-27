"""Cấu hình chung. Mọi thứ qua biến môi trường: local đọc .env, GitHub Actions đọc Secrets.
Khuôn chép từ wyckoff-radar/common/config.py.
"""
from __future__ import annotations

import os
from datetime import timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
SITE_DATA = ROOT / "docs" / "data"          # GitHub Pages phục vụ /docs

# utf-8-sig: Notepad ghi BOM → biến đầu tiên hỏng tên, thông báo im lặng (bài học KingStock).
load_dotenv(ROOT / ".env", encoding="utf-8-sig")

TZ = timezone(timedelta(hours=7), name="Asia/Ho_Chi_Minh")
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "40"))

# ---- 5 nguồn (tin UBCKNN đọc qua KingStock /api/issuance — thay app information từ 26/09/2026) ----
KINGSTOCK = os.getenv("KINGSTOCK_URL", "https://kingstock-deptlink.fly.dev").rstrip("/")
CANDLE = os.getenv("CANDLE_URL", "https://deptlink2025-bctc.github.io/candle-radar/data").rstrip("/")
PRICEPATH = os.getenv("PRICEPATH_URL", "https://tamabc906-coder.github.io/price-path/data").rstrip("/")
WYCKOFF = os.getenv("WYCKOFF_URL", "https://tamabc906-coder.github.io/wyckoff-radar/data").rstrip("/")
ORDERFLOW = os.getenv("ORDERFLOW_URL", "https://tamabc906-coder.github.io/order-flow/data").rstrip("/")

# ---- push (giống wyckoff-radar: không Worker, địa chỉ máy nằm trong Secret PUSH_SUBS_FALLBACK) ----
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_SUBJECT = os.getenv("VAPID_SUBJECT", "mailto:admin@example.com")
PUSH_SUBS_FALLBACK = os.getenv("PUSH_SUBS_FALLBACK", "")

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}
