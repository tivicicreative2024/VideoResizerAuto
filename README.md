# 🎬 Video Resizer Tool (Windows & macOS)

Công cụ chuyển đổi tỉ lệ khung hình video hàng loạt (**Batch Video Resizer**), tự động ghép Outro và chèn Watermark/Icon với giao diện trực quan (**GUI**) hiện đại viết bằng **Python** & **PyQt5**, tích hợp bộ xử lý đa luồng siêu tốc với **FFmpeg**, tối ưu hóa đặc biệt cho cả **máy tính cấu hình yếu lẫn máy đồ họa mạnh**, hỗ trợ đầy đủ cả **Windows** và **macOS**.

---

## ✨ Tính năng nổi bật (Key Features)

### 📐 1. Chuyển đổi đa tỉ lệ cùng lúc (Batch Multi-format Resize)
- **Vuông (1:1)**: `1080 x 1080` (Instagram Post, Facebook Feed)
- **Ngang (16:9)**: `1920 x 1080` (YouTube, Desktop Display)
- **Dọc (9:16)**: `1080 x 1920` (TikTok, YouTube Shorts, Reels)
- Hỗ trợ co dãn tỉ lệ (Scale %) video chính độc lập cho từng file trong danh sách.

### 🚀 2. Tối ưu hóa render đột phá cho máy cấu hình yếu (Low-spec Optimization)
- **Thuật toán Bicubic Pyramid Blur**:
  - Khắc phục triệt để tình trạng đơ, chậm khi làm mờ nền 1080p trên các máy không có GPU rời.
  - Tăng tốc độ render nền **nhanh gấp 5 - 6 lần** mà hình ảnh vẫn mịn màng, mềm mại tự nhiên (độ đo PSNR 36.6 dB, không bị ô vuông hay răng cưa).
- **3 Chế độ Hiệu năng linh hoạt**:
  - 🚀 **Tối ưu máy yếu (Low-spec)**: Tăng tốc tối đa với Bicubic Blur 1/4, encoder `superfast`, cắt giảm tối đa tải CPU.
  - ⚖️ **Cân bằng (Balanced - Mặc định)**: Cân bằng hoàn hảo giữa tốc độ và độ mịn mượt của nền.
  - 💎 **Chất lượng cao (High Quality)**: Full Gaussian Blur 40px cho máy cấu hình mạnh.
- **Hỗ trợ phần cứng đa dạng & Tùy chọn Encoder**:
  - Tự động nhận diện GPU tăng tốc: **NVIDIA NVENC**, **Intel QSV** (rất hữu ích cho laptop chip Intel UHD / Iris Xe), **AMD AMF**, **Apple VideoToolbox** (macOS).
  - Cho phép người dùng chuyển đổi linh hoạt giữa GPU và CPU tùy ý ngay trên giao diện.
- **Tùy chọn Giới hạn 30 FPS**:
  - Tự động hạ khung hình cho các video nguồn 60 FPS, giúp giảm ngay 50% khối lượng tính toán cho CPU yếu.
- **Chế độ chạy êm ái (Anti-Lag Priority)**:
  - Điều phối luồng xử lý thông minh trên Windows, đảm bảo máy tính vẫn thao tác mượt mà các tác vụ văn phòng khác trong khi đang render 100% CPU.
- **Xem trước (Preview) tức thì**:
  - Mở cửa sổ xem trước vị trí Icon và nền mờ chỉ trong chưa đầy 0.2 giây.

### 🎞️ 3. Tự động ghép Outro (Auto Outro Stitching)
- Nối video outro riêng biệt tương ứng từng tỉ lệ khung hình (Vuông, Ngang, Dọc) chỉ với 1 click.
- Tự động đồng bộ âm thanh Stereo 44.1kHz và chuẩn hóa kích thước để video không bị lệch tiếng hay giật khung hình.

### 🎨 4. Chèn Watermark / Icon trực quan (Interactive Overlay)
- Hỗ trợ chèn logo/watermark định dạng PNG, JPG, WebP.
- Cửa sổ Preview tương tác: Cho phép **kéo thả chuột trực tiếp** để di chuyển logo đến vị trí mong muốn.
- Hỗ trợ nút sao chép (Copy) và dán (Paste) thông số hoặc áp dụng nhanh logo cho toàn bộ danh sách video.

### 📂 5. Quản lý cấu hình Profiles (Profile Presets)
- Lưu và tải nhanh toàn bộ thiết lập: đường dẫn Outro, thông số Icon, chế độ render, encoder cho từng dự án/kênh riêng biệt.

---

## 💻 Hướng dẫn trên Windows (Quick Start for Windows)

### 1. Yêu cầu hệ thống
- Hệ điều hành: **Windows 10 / 11** (64-bit)
- Đã cài đặt **Python 3.8+** (Lưu ý tích chọn *"Add Python to PATH"* khi cài đặt).

### 2. Khởi chạy nhanh (1-Click)
- **Cách đơn giản nhất:** Nhấp đúp chuột vào file **`run_video_resizer.bat`**. 
  - Script sẽ tự động kiểm tra, cài đặt thư viện cần thiết (nếu thiếu) và mở ứng dụng ngay lập tức.
- **Hoặc chạy bằng Command Prompt / PowerShell:**
  ```cmd
  pip install -r requirements.txt
  python video_resizer.py
  ```

### 3. Đóng gói thành file `.exe` độc lập trên Windows
Nếu muốn tạo file ứng dụng `.exe` để sử dụng trực tiếp hoặc gửi cho người khác mà không cần cài Python:
- Nhấp đúp chuột vào file **`build_exe.bat`** (hoặc chạy lệnh: `pyinstaller VideoResizer_win.spec`).
- Sau khi đóng gói hoàn tất, file chạy sẽ nằm tại thư mục: **`dist\VideoResizer\VideoResizer.exe`**.

---

## 🍏 Hướng dẫn trên macOS (Quick Start for macOS)

### 1. Cài đặt các thư viện phụ thuộc
Mở ứng dụng **Terminal** và chạy:
```bash
pip3 install -r requirements.txt
```

### 2. Khởi động ứng dụng
- **Cách 1 (Click chuột):** Nhấp đúp vào file `run_video_resizer.command` *(Nếu macOS báo quyền chạy, mở Terminal gõ `chmod +x run_video_resizer.command`)*.
- **Cách 2 (Terminal):**
  ```bash
  python3 video_resizer.py
  ```

### 3. Đóng gói file `.app` cho macOS
```bash
pyinstaller VideoResizer.spec
```
File ứng dụng `VideoResizer.app` sẽ xuất hiện trong thư mục `dist/`.

---

## 📁 Cấu trúc dự án (Project Structure)

```text
├── video_resizer.py            # Mã nguồn chính PyQt5 & xử lý tối ưu render FFmpeg
├── run_video_resizer.bat       # [Windows] Kịch bản 1-click khởi chạy nhanh
├── build_exe.bat               # [Windows] Kịch bản 1-click đóng gói ra file .exe
├── VideoResizer_win.spec       # [Windows] Cấu hình đóng gói PyInstaller cho Windows
├── run_video_resizer.command   # [macOS] Script nhấp đúp chạy nhanh trên macOS
├── VideoResizer.spec           # [macOS] Cấu hình đóng gói PyInstaller tạo .app
├── requirements.txt            # Danh sách thư viện Python cần thiết (PyQt5, imageio-ffmpeg)
├── profiles.example.json       # File cấu hình profile mẫu
├── profiles.json               # File cấu hình profile người dùng
├── .gitignore                  # Bỏ qua các file rác, build, dist, cache
├── LICENSE                     # Giấy phép mã nguồn mở MIT
└── README.md                   # Hướng dẫn chi tiết dự án
```

---

## 📄 Bản quyền (License)
Dự án được phân phối dưới giấy phép **MIT License**. Xem chi tiết tại [LICENSE](LICENSE).
