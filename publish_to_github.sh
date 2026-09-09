#!/bin/bash
# Script hỗ trợ khởi tạo Git và đẩy mã nguồn lên GitHub nhanh chóng

set -e
cd "$(dirname "$0")"

echo "======================================================"
echo "🚀 Hướng dẫn / Tự động đẩy dự án lên GitHub"
echo "======================================================"

# 1. Khởi tạo Git nếu chưa có
if [ ! -d ".git" ]; then
    echo "1. Đang khởi tạo Git repository..."
    git init
    git branch -M main
else
    echo "1. Git repository đã tồn tại."
fi

# 2. Thêm file và commit
echo "2. Đang thêm các file mã nguồn..."
git add .gitignore README.md LICENSE requirements.txt video_resizer.py VideoResizer.spec run_video_resizer.command profiles.example.json

# Nếu có profiles.json của bạn và muốn commit (tùy chọn)
if [ -f "profiles.json" ]; then
    git add profiles.json
fi

echo "3. Đang tạo commit đầu tiên..."
git commit -m "feat: initial commit for Video Resizer Tool (macOS)" || echo "Không có thay đổi mới để commit."

echo ""
echo "======================================================"
echo "✅ ĐÃ CHUẨN BỊ XONG MÃ NGUỒN!"
echo "======================================================"
echo "Bây giờ bạn hãy làm theo 2 bước đơn giản sau:"
echo ""
echo "👉 BƯỚC A: Đảm bảo bạn đã tạo repository trên GitHub:"
echo "   https://github.com/new -> Đặt tên là: VideoResizerTool"
echo ""
echo "👉 BƯỚC B: Đẩy code lên bằng lệnh:"
echo "   git push -u origin main"

echo ""
echo "======================================================"
