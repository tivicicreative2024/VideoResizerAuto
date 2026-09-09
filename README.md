# 🎬 Video Resizer Tool (macOS & Windows)

Công cụ chuyển đổi tỉ lệ khung hình video hàng loạt (Batch Video Resizer), tự động ghép Outro và chèn Watermark/Icon với giao diện trực quan (GUI) hiện đại viết bằng **Python** & **PyQt5**, tối ưu xử lý đa luồng với **FFmpeg**. Hỗ trợ đầy đủ cả hai hệ điều hành **macOS** và **Windows**.

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
  - Chạy ngầm không mở cửa sổ đen (`CREATE_NO_WINDOW` trên Windows).
  - Tiến trình xử lý chạy đa luồng (`QThread`), hiển thị thanh tiến trình và log thời gian thực, không bị đơ giao diện.

---

## 🚀 Hướng dẫn cài đặt & Khởi chạy (Quick Start)

### 🪟 Dành cho Windows:
1. Tải source code hoặc file zip về máy và giải nén.
2. Cài đặt Python 3 (từ [python.org](https://www.python.org/downloads/), **nhớ tích chọn "Add python.exe to PATH"** khi cài).
3. **Cài đặt thư viện:** Nhấp đúp chuột vào file `install_requirements.bat`.
4. **Khởi chạy ứng dụng:** Nhấp đúp chuột vào file `run_video_resizer.bat`.

### 🍎 Dành cho macOS:
1. Mở Terminal và di chuyển vào thư mục dự án:
   ```bash
   cd VideoResizerAuto
   pip3 install -r requirements.txt
   ```
2. **Khởi chạy ứng dụng:**
   - Hoặc gõ `python3 video_resizer.py`
   - Hoặc nhấp đúp vào file `run_video_resizer.command`.

---

## 📦 Đóng gói thành phần mềm độc lập (.exe / .app)

### 🪟 Trên Windows (Tạo file `VideoResizer.exe`):
Nhấp đúp chuột vào file **`build_windows_exe.bat`** (hoặc chạy `pyinstaller VideoResizer_Windows.spec`).  
File `.exe` sẽ được tạo trong thư mục `dist\VideoResizer\VideoResizer.exe`.

### 🍎 Trên macOS (Tạo ứng dụng `VideoResizer.app`):
Chạy lệnh trong Terminal:
```bash
pyinstaller VideoResizer.spec
```
File ứng dụng sẽ được tạo trong thư mục `dist/VideoResizer.app`.


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
