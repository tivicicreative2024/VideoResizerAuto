@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Video Resizer Tool

echo ========================================================
echo       DANG KHOI DONG CONG CU VIDEO RESIZER (WINDOWS)
echo ========================================================

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Python tren he thong!
    echo Vui long cai dat Python 3.8+ tu https://www.python.org/
    echo LUU Y: Khi cai dat, nho tich vao o "Add Python to PATH".
    echo ========================================================
    pause
    exit /b 1
)

python -c "import PyQt5, imageio_ffmpeg" >nul 2>&1
if %errorlevel% neq 0 (
    echo [THONG BAO] Dang tu dong cai dat cac thu vien can thiet...
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [LOI] Cai dat thu vien that bai! Vui long kiem tra ket noi mang.
        pause
        exit /b 1
    )
)

echo Dang mo giao dien Video Resizer...
python video_resizer.py

if %errorlevel% neq 0 (
    echo.
    echo [CANH BAO] Ung dung da dong voi loi. Chi tiet loi xem ben tren.
    pause
)
