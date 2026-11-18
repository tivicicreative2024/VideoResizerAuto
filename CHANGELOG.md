# Nhật ký thay đổi · Changelog

## 1.1.2 · Sửa lỗi treo khi ghép outro

Video nguồn hoặc outro không có âm thanh không còn làm FFmpeg chạy mãi: track im lặng được cắt đúng bằng thời lượng của file.

## 1.1.1 · Giao diện gọn hơn

Header và thanh bước được thu gọn. Sidebar chỉ giữ xem trước; chọn video rồi mở **Chỉnh video…** để chỉnh phóng hình/logo. Bước thiết lập ưu tiên **Tỉ lệ xuất** và **Tên file đầu ra**. Chèn mã qua menu, chỉ hiện tùy chọn đánh số khi có `%N`; ẩn đi vẫn giữ giá trị đã chọn. Outro và hiệu năng mở khi cần. Tạo/xóa mẫu nằm trong **Mẫu khác**.

## 1.1.0 · Giao diện theo Clink

Luồng mới gồm **Nguồn video → Thiết lập xuất → Kiểm tra đầu ra**. Có xem trước chạy nền, tỉ lệ xem độc lập với tỉ lệ xuất, kéo thả video vào danh sách và xem chính xác tên/đường dẫn trước khi render.

Quy tắc đặt tên với `%F`, `%N`, `%S`, `%D`, `%%`. Tên trùng tự thêm `-2`, `-3`…; không ghi đè video nguồn hoặc file đã có. Render vào vùng tạm riêng, chỉ đưa file hoàn tất ra thư mục đích; GPU lỗi được thử lại bằng CPU. Tên và tỉ lệ được lưu trong mẫu. Bộ cài kèm font và icon để dùng offline.

## 1.0.0

Bản Windows đầu tiên: resize 3 tỉ lệ, nền mờ, ghép outro, chèn logo, profiles.
