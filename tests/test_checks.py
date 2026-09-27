"""Mỗi tiêu chí có ca đạt, ca trượt và ca thiếu dữ liệu. Dữ liệu dựng tay theo đúng khuôn JSON của từng app."""
from job import checks as C
from job.run_daily import buy_alerts, stale_reasons
from job.sources import Sources

TD = "2026-09-25"


def st(rows, id_):
    return next(r for r in rows if r["id"] == id_)["s"]


# ---------------------------------------------------------------- A
SSC = [{"symbol": "GMD", "kind": "equity", "date": "2026-09-24", "title": "UBCKNN nhận… Gemadept", "url": "https://ssc.gov.vn/a"},
       {"symbol": "GMD", "kind": "dividend", "date": "2026-07-01", "title": "cũ quá 30 ngày", "url": "https://ssc.gov.vn/b"},
       {"symbol": "TLD", "kind": "dividend", "date": "2026-09-26", "title": "sau ngày phiên", "url": "https://ssc.gov.vn/c"},
       {"symbol": None, "kind": "dividend", "date": "2026-09-20", "title": "không khớp được mã"}]


def test_ssc():
    rows = C.ssc("GMD", SSC, TD, None)
    assert st(rows, "ssc") == "ok" and "Tăng vốn từ vốn chủ sở hữu (24/09)" in rows[0]["d"]
    assert len(rows[0]["links"]) == 1                          # tin 01/07 nằm ngoài 30 ngày
    assert st(C.ssc("TLD", SSC, TD, None), "ssc") == "no"      # tin sau ngày phiên đang chấm không tính
    assert st(C.ssc("HPG", SSC, TD, None), "ssc") == "no"
    assert st(C.ssc("HPG", None, TD, "Không đọc được nguồn"), "ssc") == "na"


# ---------------------------------------------------------------- B
CANDLE = {"trend": [{"symbol": "HPG", "up": True, "line": 25.0, "since": "2026-09-01", "days": 18, "ema": 26.0, "above_ema": True},
                    {"symbol": "FPT", "up": False, "line": 70.0, "since": "2026-08-01", "days": 40, "ema": 68.0, "above_ema": False}]}
DAYS = {"2026-09-25": [{"symbol": "HPG", "kind": "candle", "direction": "buy", "name": "Sao mai"},
                       {"symbol": "FPT", "kind": "candle", "direction": "sell", "name": "Sao hôm"}],
        "2026-09-24": [{"symbol": "FPT", "kind": "trend", "direction": "buy", "name": "Supertrend xanh"}]}


def test_candle():
    h = C.candle("HPG", CANDLE, DAYS, None)
    assert [r["s"] for r in h] == ["ok", "ok", "ok"] and "Sao mai (25/09)" in h[0]["d"]
    f = C.candle("FPT", CANDLE, DAYS, None)
    assert [r["s"] for r in f] == ["no", "no", "no"]          # nến bán và tín hiệu trend không tính là cụm nến mua
    assert [r["s"] for r in C.candle("VCB", CANDLE, DAYS, None)][1:] == ["na", "na"]
    assert {r["s"] for r in C.candle("HPG", CANDLE, DAYS, "Nguồn mới có phiên 24/09")} == {"na"}


# ---------------------------------------------------------------- C
def pp_sym(price=10.5, buy=600, sell=300, c=10.5, pc=10.0, big=(200, 100), est=False, no_side=False, closes=None):
    closes = closes or [9.6, 9.8, 9.9, 10.0, 10.0, c]
    daily = [{"d": f"2026-09-{18 + i}", "est": False, "buy": 500, "sell": 400, "x": 0, "total": 900, "c": x, "pc": x,
              "no_side": False} for i, x in enumerate(closes[:-1])]
    daily.append({"d": TD, "est": est, "buy": buy, "sell": sell, "x": 100, "total": buy + sell + 100, "c": c, "pc": pc,
                  "no_side": no_side})
    fp = [[TD, 1 if est else 0, pc, c, pc, c, [[c, buy, sell, 0, big[0], big[1]]]]]
    return {"price": price, "price_date": TD, "name": "X",
            "profiles": {n: {"bin": 0.1, "base": 9.0, "poc": p, "bins": [[9.0 + i * 0.1, 1, 1, 0, 0, 0, 0] for i in range(20)]}
                         for n, p in (("10", 5), ("20", 8))},
            "daily": daily, "fp": fp}


def test_pricepath_all_pass():
    rows, poc = C.pricepath("A", {"symbols": {"A": pp_sym()}}, TD, None)
    assert poc == {"10": 9.55, "20": 9.85}                     # bins[poc][0] + bin/2
    assert [r["s"] for r in rows] == ["ok", "ok", "ok", "ok", "ok", "ok"]


def test_pricepath_fails():
    s = pp_sym(price=9.0, buy=300, sell=600, c=10.1, pc=10.0, big=(50, 90), closes=[10.5, 10.4, 10.3, 10.2, 10.1, 10.1])
    rows, _ = C.pricepath("A", {"symbols": {"A": s}}, TD, None)
    assert [r["s"] for r in rows] == ["no", "no", "no", "no", "no", "no"]


def test_push_and_up2_independent():
    rows, _ = C.pricepath("A", {"symbols": {"A": pp_sym(c=10.1, pc=10.0)}}, TD, None)   # mua đẩy nhưng chỉ +1 %
    assert st(rows, "push") == "ok" and st(rows, "up2") == "no"
    rows, _ = C.pricepath("A", {"symbols": {"A": pp_sym(buy=300, sell=600, c=10.3, pc=10.0)}}, TD, None)  # +3 %, bán áp đảo
    assert st(rows, "push") == "no" and st(rows, "up2") == "ok"
    rows, _ = C.pricepath("A", {"symbols": {"A": pp_sym(no_side=True)}}, TD, None)
    assert st(rows, "push") == "na" and st(rows, "up2") == "ok"             # tăng 2 % không cần chiều mua-bán


def test_pricepath_missing():
    rows, _ = C.pricepath("A", {"symbols": {"A": pp_sym(est=True)}}, TD, None)
    assert st(rows, "whale") == "na"
    rows, _ = C.pricepath("A", {"symbols": {"A": pp_sym(no_side=True)}}, TD, None)
    assert st(rows, "push") == "na" and st(rows, "pp_cvd") == "na"
    old = pp_sym(); old["price_date"] = "2026-09-24"
    rows, poc = C.pricepath("A", {"symbols": {"A": old}}, TD, None)
    assert {r["s"] for r in rows} == {"na"} and poc == {}


# ---------------------------------------------------------------- D
def wy(marks):
    bars = [[f"2026-08-{i:02d}" if i < 32 else f"2026-09-{i - 31:02d}", 1, 1, 1, 1] for i in range(1, 57)]
    return {"bars": {"A": bars}, "marks": {"A": marks}}


def test_wyckoff():
    assert st(C.wyckoff("A", wy([["2026-09-20", "sc"]]), None, None), "wy") == "ok"
    rows = C.wyckoff("A", wy([["2026-09-20", "spring2"], ["2026-09-21", "st"]]), None, None)
    assert [r["id"] for r in rows] == ["wy"] and rows[0]["s"] == "no"   # Spring #2 bỏ hẳn (chốt 26/09)
    assert st(C.wyckoff("A", wy([["2026-07-01", "sc"]]), None, None), "wy") == "no"   # quá 20 phiên
    assert st(C.wyckoff("B", wy([]), None, None), "wy") == "na"


# ---------------------------------------------------------------- E
def of_data(delta=500, cvd=(1, 2, 3, 4, 5, 6), close=(10, 10.1, 10.2, 10.3, 10.4, 10.5), cvw=0.4, day=TD,
            big=(1, 1, 1, 1, 1, 1), cost=10.0):
    it = {"sym": "A", "day": day, "close": close[-1], "chg": 1.0, "buy": 1000 + delta, "sell": 1000, "delta": delta,
          "share": 55.0, "no_side": False}
    days = [{"d": f"2026-09-{20 + i}" if i < len(cvd) - 1 else TD, "cvd": c, "close": p, "vw": 10.3, "cvw": cvw,
             "bb": 1000 if b > 0 else 0, "bs": 1000 if b < 0 else 0,
             "blv": [] if cost is None else [[cost, 0, 1000]], "blv_ok": True}
            for i, (c, p, b) in enumerate(zip(cvd, close, big))]
    return {"items": [it]}, {"A": {"days": days}}


def test_orderflow():
    lat, dy = of_data()
    assert [r["s"] for r in C.orderflow("A", lat, dy, TD, None)] == ["ok", "ok", "ok", "ok", "ok", "ok"]
    lat, dy = of_data(delta=-5, cvd=(6, 5, 4, 3, 2, -1), close=(11, 10.9, 10.8, 10.7, 10.6, 10.5), cvw=-0.2,
                      big=(-1, -1, -1, -1, -1, -1), cost=11.0)
    assert [r["s"] for r in C.orderflow("A", lat, dy, TD, None)] == ["no", "no", "no", "no", "no", "no"]
    lat, dy = of_data(cvd=(1, 2), close=(10, 10.1))
    assert st(C.orderflow("A", lat, dy, TD, None), "of_cvd") == "na"      # mới 2 phiên
    assert st(C.orderflow("A", lat, dy, TD, None), "whale5") == "na"


def test_whale5_counts_last_5_sessions():
    lat, dy = of_data(big=(1, -1, 1, -1, 1, 1))          # phiên đầu nằm ngoài 5 phiên → 3/5
    assert st(C.orderflow("A", lat, dy, TD, None), "whale5") == "ok"
    lat, dy = of_data(big=(1, 1, 1, -1, -1, 0))          # 2/5, phiên bằng nhau không tính mua ròng
    assert st(C.orderflow("A", lat, dy, TD, None), "whale5") == "no"
    lat, dy = of_data(cvd=(1, 2, 3, 4), close=(10, 10.1, 10.2, 10.3), big=(1, 1, 1, 1))
    assert st(C.orderflow("A", lat, dy, TD, None), "whale5") == "na"      # mới 4 phiên


def test_whale_cost():
    lat, dy = of_data(cost=10.4)                         # đóng 10,5 > 10,4
    assert st(C.orderflow("A", lat, dy, TD, None), "whale_cost") == "ok"
    days = dy["A"]["days"]
    days[0]["blv"] = [[5.0, 0, 100000]]                  # phiên rẻ nhưng chưa lưu theo mức giá → bỏ qua
    days[0]["blv_ok"] = False
    assert st(C.orderflow("A", lat, dy, TD, None), "whale_cost") == "ok"
    days[0]["blv_ok"] = True                             # tính vào → giá vốn kéo xuống, vẫn đạt
    for d in days[1:]:
        d["blv"] = [[10.6, 0, 1000]]
    days[0]["blv"] = [[10.6, 0, 1000]]
    assert st(C.orderflow("A", lat, dy, TD, None), "whale_cost") == "no"   # đóng 10,5 < 10,6
    lat, dy = of_data(cost=None)
    assert st(C.orderflow("A", lat, dy, TD, None), "whale_cost") == "na"
    lat, dy = of_data(day="2026-09-24")
    assert {r["s"] for r in C.orderflow("A", lat, dy, TD, None)} == {"na"}


# ---------------------------------------------------------------- tổng hợp
def test_score_counts_only_ok_and_no():
    lat, dy = of_data()
    S = Sources(watchlist=[{"symbol": "A", "company_name": "Công ty A"}], ssc=[], candle=CANDLE, candle_days=DAYS,
                pp={"symbols": {"A": pp_sym()}}, wy_bars=wy([["2026-09-20", "spring2"]]), wy_latest={"board": []},
                of_latest=lat, of_daily=dy)
    b = C.score("A", S, TD, {})
    assert b["name"] == "Công ty A" and b["warn"] == 0
    assert b["total"] == 1 + 1 + 6 + 1 + 6          # A:1 · B: cdl tính, st/ema na (A không có trong trend) · C:6 · D:1 · E:6
    assert b["na"] == 2
    assert b["pass"] == 12 and C.code(b).count("|") == 4
    assert b["chart"] is None                       # không có nến candle-radar → không vẽ


def test_buy_alerts_filters_and_dedupes():
    sig = [{"symbol": "HPG", "direction": "buy", "date": TD, "at": "2026-09-25T10:00", "invalidated": False},
           {"symbol": "HPG", "direction": "buy", "date": TD, "at": "2026-09-25T09:00", "invalidated": False},
           {"symbol": "FPT", "direction": "buy", "date": TD, "at": "2026-09-25T09:30", "invalidated": True},
           {"symbol": "VCB", "direction": "sell", "date": TD, "at": "2026-09-25T09:30", "invalidated": False},
           {"symbol": "ACB", "direction": "buy", "date": "2026-09-24", "at": "2026-09-24T09:30", "invalidated": False}]
    out = buy_alerts(sig, TD)
    assert [(a["sym"], a["at"]) for a in out] == [("HPG", "2026-09-25T09:00")]


def test_stale_reasons():
    s = stale_reasons({"kingstock": {"ok": True, "date": "x"}, "ssc": {"ok": False, "error": "Fly chết"}, "x": {"ok": True, "date": "2026-09-20"},
                       "candle": {"ok": True, "date": "2026-09-24"}, "wyckoff": {"ok": True, "date": TD}}, TD)
    assert "kingstock" not in s and "Fly chết" in s["ssc"] and "20/09" in s["x"] and "24/09" in s["candle"] and s["wyckoff"] is None
