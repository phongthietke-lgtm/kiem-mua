"""EMA10 + Supertrend(10,3) cho biểu đồ chi tiết. Chép nguyên từ candle-radar/job/trend.py (ema, atr_wilder,
supertrend) để số khớp tuyệt đối với app gốc; đừng sửa riêng ở đây.
"""
from __future__ import annotations

ATR_PERIOD = 10
ATR_MULT = 3.0
EMA_PERIOD = 10


def ema(bars: list[dict], n: int = EMA_PERIOD) -> list[float | None]:
    """EMA đóng cửa, mồi bằng SMA n phiên đầu. Cùng độ dài với bars, warm-up là None."""
    out: list[float | None] = [None] * len(bars)
    if n < 1 or len(bars) < n:
        return out
    v = sum(b["c"] for b in bars[:n]) / n
    out[n - 1] = v
    a = 2.0 / (n + 1)
    for i in range(n, len(bars)):
        v = a * bars[i]["c"] + (1 - a) * v
        out[i] = v
    return out


def atr_wilder(bars: list[dict], n: int = ATR_PERIOD) -> list[float | None]:
    """ATR làm mượt kiểu Wilder: atr = (atr₋₁·(n−1) + TR)/n, mồi bằng SMA của TR."""
    out: list[float | None] = [None] * len(bars)
    if len(bars) < n:
        return out
    tr = []
    for i, b in enumerate(bars):
        if i == 0:
            tr.append(b["h"] - b["l"])
        else:
            pc = bars[i - 1]["c"]
            tr.append(max(b["h"] - b["l"], abs(b["h"] - pc), abs(b["l"] - pc)))
    v = sum(tr[:n]) / n
    out[n - 1] = v
    for i in range(n, len(bars)):
        v = (v * (n - 1) + tr[i]) / n
        out[i] = v
    return out


def supertrend(bars: list[dict], n: int = ATR_PERIOD, mult: float = ATR_MULT) -> list[dict | None]:
    """Mỗi phần tử: {"up": bool, "line": float, "fu": float, "fl": float} hoặc None khi chưa đủ dữ liệu.
    Dải "final" chỉ siết vào, không nới ra, trừ khi giá đã vượt qua nó (thuật toán chuẩn/TradingView)."""
    atr = atr_wilder(bars, n)
    out: list[dict | None] = [None] * len(bars)
    prev: dict | None = None
    for i, b in enumerate(bars):
        if atr[i] is None:
            continue
        hl2 = (b["h"] + b["l"]) / 2
        bu, bl = hl2 + mult * atr[i], hl2 - mult * atr[i]
        if prev is None:
            fu, fl, up = bu, bl, False          # TradingView khởi tạo hướng xuống
        else:
            pc = bars[i - 1]["c"]
            fu = bu if (bu < prev["fu"] or pc > prev["fu"]) else prev["fu"]
            fl = bl if (bl > prev["fl"] or pc < prev["fl"]) else prev["fl"]
            up = (not (b["c"] < fl)) if prev["up"] else (b["c"] > fu)
        prev = {"up": up, "line": fl if up else fu, "fu": fu, "fl": fl}
        out[i] = prev
    return out
