# 🎬 Video Resizer Tool (macOS)

Công cụ chuyển đổi tỉ lệ khung hình video hàng loạt (Batch Video Resizer), tự động ghép Outro và chèn Watermark/Icon với giao diện trực quan (GUI) hiện đại viết bằng **Python** & **PyQt5**, tối ưu xử lý đa luồng với **FFmpeg**.

---

## ✨ Tính năng chính (Key Features)

- 📐 **Chuyển đổi đa tỉ lệ cùng lúc (Batch Multi-format Resize):**
  - **Vuông (1:1)**: `1080 x 1080` (Instagram Post, Facebook Feed)
  - **Ngang (16:9)**: `1920 x 1080` (YouTube, Desktop Display)
  - **Dọc (9:16)**: `1080 x 1920` (TikTok, YouTube Shorts, Reels)
- 🎞️ **Tự động ghép Outro (Auto Outro Stitching):**
  - Nối video outro riêng biệt tương ứng từng tỉ lệ khung hình chỉ với 1 click.
- 🎨 **Chèn Watermark / Icon & Thu phóng tùy chỉnh (Custom Overlay & Scaling):**
  - Hỗ trợ chèn logo/watermark vào các góc màn hình hoặc căn giữa với kích thước tùy chỉnh.
  - Tùy chỉnh tỉ lệ co dãn (Scale) video độc lập cho từng file trong danh sách.
- 📂 **Quản lý cấu hình Profiles (Profile Presets):**
  - Lưu và tải nhanh các bộ cấu hình đường dẫn Outro theo từng thương hiệu/chiến dịch.
- ⚡ **Xử lý nhanh & mượt mà (High Performance):**
  - Tận dụng `imageio-ffmpeg` tự động tích hợp FFmpeg, không cần cài đặt phức tạp.
  - Tiến trình xử lý chạy đa luồng (`QThread`), hiển thị thanh tiến trình và log thời gian thực, không bị đơ giao diện.

---

## 🚀 Hướng dẫn cài đặt & Chạy (Quick Start)

### 1. Yêu cầu hệ thống (Prerequisites)
- Hệ điều hành: **macOS** (hoặc Windows / Linux)
- Đã cài đặt **Python 3.8+**

### 2. Cài đặt các thư viện phụ thuộc (Install Dependencies)
Mở ứng dụng **Terminal** và chạy các lệnh sau:

```bash
# Clone repository về máy
git clone https://github.com/tivicicreative2024/VideoResizerAuto.git
cd VideoResizerAuto

# Cài đặt thư viện yêu cầu
pip3 install -r requirements.txt
```

### 3. Khởi động ứng dụng (Run Application)
Bạn có thể khởi động ứng dụng bằng một trong các cách:

- **Cách 1 (Terminal):**
  ```bash
  python3 video_resizer.py
  ```
- **Cách 2 (Click chuột trên macOS):**
  Nhấp đúp chuột vào file `run_video_resizer.command` để mở ngay. *(Nếu macOS báo quyền, chạy `chmod +x run_video_resizer.command`)*.

---

## 📦 Hướng dẫn đóng gói file `.app` độc lập (Build macOS App)

Nếu muốn đóng gói thành file ứng dụng `.app` để chạy trực tiếp không cần cài Python:

```bash
pip3 install pyinstaller
pyinstaller VideoResizer.spec
```

Sau khi hoàn tất, file ứng dụng `VideoResizer.app` sẽ xuất hiện trong thư mục `dist/`.

---

## 📁 Cấu trúc dự án (Project Structure)

```text
├── video_resizer.py            # Mã nguồn chính giao diện PyQt5 & xử lý FFmpeg
├── VideoResizer.spec           # Cấu hình đóng gói PyInstaller tạo macOS .app
├── run_video_resizer.command   # Script nhấp đúp chạy nhanh trên macOS
├── requirements.txt            # Danh sách thư viện Python cần thiết
├── profiles.example.json       # File cấu hình profile mẫu
├── .gitignore                  # Bỏ qua các file rác, build, dist, cache
├── LICENSE                     # Giấy phép mã nguồn mở MIT
└── README.md                   # Hướng dẫn chi tiết dự án
```

---

## 🤝 Đóng góp (Contributing)
Mọi đóng góp, báo lỗi (Issues) hoặc Pull Requests đều được hoan nghênh để hoàn thiện công cụ hơn nữa!

## 📄 Bản quyền (License)
Dự án được phân phối dưới giấy phép **MIT License**. Xem chi tiết tại [LICENSE](LICENSE).
