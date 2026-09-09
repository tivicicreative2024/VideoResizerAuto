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
echo "👉 BƯỚC A: Vào https://github.com/new để tạo repository mới trên GitHub."
echo "   (Đặt tên là VideoResizerTool_Mac, KHÔNG tích chọn Add README / .gitignore)"
echo ""
echo "👉 BƯỚC B: Copy link repository vừa tạo (VD: https://github.com/username/VideoResizerTool_Mac.git)"
echo "   và chạy 2 lệnh sau trong Terminal:"
echo ""
echo "   git remote add origin <LINK_GITHUB_CUA_BAN>"
echo "   git push -u origin main"
echo ""
echo "======================================================"
