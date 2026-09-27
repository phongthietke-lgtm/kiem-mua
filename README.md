# Kiểm Mua

Soát mã KingStock báo MUA qua 4 app khác và tin UBCKNN, sau phiên. App thứ 12, dựng ngày 26/09/2026. Kế hoạch gốc nằm ở
`C:\Users\IT\.claude\plans\b-n-l-nh-l-p-vectorized-knuth.md`.

**App chỉ liệt kê, không kết luận.** Chưa tiêu chí riêng lẻ nào được đo là hơn mua đại: Order Flow Lab 0/16,
Volume Profile Lab 0/9, Spring/Test ≈ mua đại. Điểm mỗi ngày được lưu vào `docs/data/daily/` để khoảng
12/2026 đo xem điểm cao có thật sự tốt hơn không.

## Cách chạy
- **GitHub Actions** chạy lúc 16:30 VN, thứ Hai đến thứ Sáu, dự phòng 17:15 và 18:45 (`.github/workflows/daily.yml`).
- **Trên máy:** chạy `install.bat` một lần. Sau đó chạy `run-daily-local.bat --date 2026-09-25`: lệnh này ghi file nhưng không gửi push.
- **Test:** `venv\Scripts\python -m pytest -q`.

Job làm lần lượt:
1. `job/sources.py` tải các nguồn.
2. Kiểm xem 4 app cuối ngày đã có phiên hôm nay chưa.
3. `job/checks.py` chấm 17 tiêu chí cho cả danh mục (39 mã).
4. Lọc các mã KingStock báo MUA hôm nay: `direction=buy`, chưa `invalidated`, mỗi mã lấy lần báo sớm nhất.
5. Ghi `docs/data/latest.json` (gồm cả biểu đồ 46 phiên), `daily/<ngày>.json` (điểm + chuỗi trạng thái) và `state.json`.
6. Gửi một thông báo tổng kết nếu có mã báo MUA.

**Chờ nguồn.** Nếu một trong 4 app cuối ngày chưa có phiên hôm nay, lần chạy 16:30 và 17:15 thoát để lần sau thử lại. Lần 18:45 chấm luôn, và nguồn nào còn cũ thì các tiêu chí của nó ghi "thiếu dữ liệu", không tính điểm. Nếu không nguồn nào có phiên hôm nay (ngày nghỉ), job không ghi gì. **Job luôn thoát mã 0**, vì thoát mã khác 0 làm bước commit bị bỏ qua (bẫy price-path 23/09).

## Nguồn (đã soát code thật ngày 26/09/2026)
| Nguồn | Đọc gì |
|---|---|
| KingStock | `kingstock-deptlink.fly.dev/api/signals?limit=200` và `/api/watchlist`. Không có webhook, không có CORS, nên phải đọc từ phía máy chủ. |
| Tin UBCKNN | KingStock `/api/issuance?limit=200`: tin "UBCKNN nhận tài liệu báo cáo phát hành" loại trả cổ tức / tăng vốn từ VCSH, đã gắn mã. Công khai, không token. Nhóm A lấy tin 30 ngày. Từ 26/09/2026 thay cho app information. |
| candle-radar | `latest.json` (`trend[]`, `signals[]`, `history`), `daily/<ngày>.json` của 2 phiên trước, `bars.json` |
| price-path | `zone/latest.json`: hồ sơ 40 phiên, `daily[]`, `fp[]` (khoảng 1,2 MB) |
| wyckoff-radar | `bars.json` (`marks` ≈ 6 tháng) và `latest.json` (`board`) |
| order-flow | `latest.json` (`items[]`) và `daily/<mã>.json` (39 tệp) |

## 17 tiêu chí (`job/checks.py`)
Luật lấy đúng như app gốc, xem docstring đầu tệp. Có mấy chỗ chủ ý khác yêu cầu ban đầu, đều đã được anh chốt ngày 26/09:
- **Cá mập:** tiêu chí là "cá mập mua > cá mập bán", thay cho "> 50 % KL ngày". Với ngưỡng cũ, phiên 25/09 không mã nào đạt (0/39). Tỷ lệ % KL ngày vẫn hiện để tham khảo.
- **Spring #2:** bỏ hẳn, không chấm, không vẽ lên biểu đồ. Nhóm D chỉ xét SC, Spring #3 và Test trong 20 phiên.
- **POC:** tách thành 2 dòng, "Giá trên POC 10 phiên" và "Giá trên POC 20 phiên", mỗi dòng một điểm. Không dùng POC 40 phiên nữa.
- **Cá mập 5 phiên (thêm 27/09):** đếm trong 5 phiên gần nhất số phiên cá mập mua chủ động > bán chủ động (`bb > bs` trong `daily/<mã>.json` của order-flow, chính là ô "Delta cá mập"), đạt khi từ 3 phiên. Chưa đủ 5 phiên thì ghi thiếu dữ liệu. Dòng cá mập 1 phiên ở nhóm C vẫn giữ.
- **Giá vốn cá mập (thêm 27/09):** đạt khi giá đóng cửa > giá mua bình quân của lệnh cá mập, cộng dồn `blv` tối đa 20 phiên (bỏ phiên `blv_ok=false`) — đúng đường vàng "Giá vốn CM" của order-flow (`drawWhale`). Chưa có lệnh cá mập mua thì ghi thiếu dữ liệu.
- **Đẩy giá và tăng 2 % (tách 27/09):** "Mua đẩy giá lên" (dòng chủ động ≥ +5 % và giá > +0,3 %, luật fvForce của price-path) và "Giá tăng > 2%" là 2 dòng riêng, mỗi dòng một điểm. Dòng tăng 2 % không cần chiều mua-bán.
- **Delta và mua/bán chủ động:** "delta dương" và "mua chủ động > bán chủ động" là cùng một phép so sánh (delta = mua − bán), nên gộp thành một dòng để không bị tính điểm hai lần.

EMA10 và Supertrend của biểu đồ dùng `job/trend.py`, chép nguyên từ `candle-radar/job/trend.py`. Nếu sửa thì phải sửa ở cả hai nơi.

## GitHub
- Repo `phongthietke-lgtm/kiem-mua` (công khai). Pages: `https://phongthietke-lgtm.github.io/kiem-mua/`, lấy từ nhánh `main`, thư mục `/docs`.
- Máy này đẩy code qua tài khoản collaborator `deptlink2025-bctc` (Git Credential Manager), bằng lệnh `git push origin master:main`.

**Thông báo điện thoại: chưa làm (để sau).** Chưa làm thì job chấm bình thường, chỉ không gửi gì; `state.json` sẽ ghi "Thiếu VAPID". Khi làm:
1. Chạy `venv\Scripts\python -m job.gen_vapid`. Dán 3 dòng in ra vào Secrets của repo. Chép riêng `VAPID_PUBLIC_KEY` vào `docs/config.js`.
2. Mở app trên điện thoại, vào Cài đặt, bấm Bật thông báo, rồi dán đoạn mã hiện ra vào Secret `PUSH_SUBS_FALLBACK`.
3. Vào Actions, chạy `daily` với `test_push=true`.

## Bẫy đã biết
- **Đổi JS/CSS:** phải tăng `?v=` trong `index.html`, rồi đóng hẳn PWA và mở lại.
- **Ngày dữ liệu:** các app không cập nhật cùng ngày. Mỗi nguồn được so `trade_date` với hôm nay (`stale_reasons`).
- **Nguồn thiếu dữ liệu, ghi "thiếu dữ liệu", không tính là trượt:** phiên `est` hoặc mã `no_side` của price-path, và mã bị `stale` ở candle-radar hay wyckoff.
- **order-flow đến 26/09 mới có 6 phiên.** Tiêu chí "CVD & giá cùng lên" cần ít nhất 3 phiên.
