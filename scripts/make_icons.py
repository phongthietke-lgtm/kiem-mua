r"""Vẽ PNG icon PWA từ toạ độ logo (docs/icons/logo.svg) bằng Pillow. Khuôn chép wyckoff-radar/scripts/make_icons.py.
Chạy: venv\Scripts\python -m scripts.make_icons   (chỉ máy dev; Actions không gọi).

Logo "Kính lúp" (anh chọn 27/09/2026 trong 3 phương án): vòng kính trắng, dấu tích xanh chanh bên trong, cán vàng,
trên nền tím #3B1A78 — ý "soát kỹ từng mã". Toạ độ trong hệ 120×120 khớp logo.svg.
"""
from pathlib import Path

from PIL import Image, ImageDraw

PURPLE, WHITE, LIME, YELLOW = (0x3B, 0x1A, 0x78), (255, 255, 255), (0x7D, 0xBA, 0x2F), (0xF6, 0xC1, 0x2E)
OUT = Path(__file__).resolve().parent.parent / "docs" / "icons"
LENS = (54, 54, 28, 11)                      # tâm x, tâm y, bán kính, độ dày vòng
HANDLE = ((75, 75), (95, 95), 14)            # cán kính: 2 đầu + độ dày
CHECK = ([(41, 55), (51, 65), (68, 45)], 9)  # dấu tích + độ dày


def draw(size: int, maskable: bool) -> Image.Image:
    S = size * 4                              # vẽ 4× rồi thu nhỏ cho nét mượt
    img = Image.new("RGBA", (S, S), PURPLE if maskable else (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if not maskable:
        d.rounded_rectangle((0, 0, S - 1, S - 1), radius=int(S * 28 / 120), fill=PURPLE)
    k = (S * 0.8 / 120) if maskable else (S / 120)   # maskable: thu hình vào vùng an toàn 80 %
    off = (S - 120 * k) / 2
    P = lambda x, y: (off + x * k, off + y * k)  # noqa: E731

    def cap(xy, w, col):                      # đầu nét tròn
        x, y = P(*xy)
        d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=col)

    (a, b), hw = HANDLE[:2], HANDLE[2] * k
    d.line([P(*a), P(*b)], fill=YELLOW, width=int(hw))
    cap(a, hw, YELLOW)
    cap(b, hw, YELLOW)

    cx, cy, r, w = LENS
    ro, ri = (r + w / 2) * k, (r - w / 2) * k
    X, Y = P(cx, cy)
    d.ellipse((X - ro, Y - ro, X + ro, Y + ro), fill=WHITE)
    d.ellipse((X - ri, Y - ri, X + ri, Y + ri), fill=PURPLE)

    pts, cw = CHECK[0], CHECK[1] * k
    d.line([P(*p) for p in pts], fill=LIME, width=int(cw), joint="curve")
    for p in pts:
        cap(p, cw, LIME)
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    draw(192, False).save(OUT / "icon-192.png")
    draw(512, False).save(OUT / "icon-512.png")
    draw(512, True).convert("RGB").save(OUT / "icon-maskable.png")
    print("wrote icon-192.png, icon-512.png, icon-maskable.png ->", OUT)


if __name__ == "__main__":
    main()
