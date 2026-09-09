@echo off
title Cai dat thu vien cho Video Resizer Tool
echo ===================================================
echo Dang cai dat cac thu vien Python can thiet...
echo ===================================================
pip install -r requirements.txt
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [THANH CONG] Da cai dat xong thu vien!
    echo Bay gio ban co the nhap dup chuot vao 'run_video_resizer.bat' de mo ung dung.
) else (
    echo.
    echo [LOI] Khong the cai dat thu vien. Vui long kiem tra Python va pip tren may cua ban.
)
echo.
pause
