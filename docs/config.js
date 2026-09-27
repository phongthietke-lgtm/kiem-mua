// Cấu hình giao diện. VAPID_PUBLIC phải TRÙNG Secret VAPID_PUBLIC_KEY trên GitHub
// (sinh bằng venv\Scripts\python -m job.gen_vapid). Để trống = nút "Bật thông báo" bị khoá.
window.KM_CONFIG = {
  VAPID_PUBLIC: "",
};
