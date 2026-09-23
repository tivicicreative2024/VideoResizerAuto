@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Đóng gói Video Resizer thành file .EXE

echo ========================================================
echo        DONG GOI VIDEO RESIZER CHO WINDOWS (.EXE)
echo ========================================================

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Python tren he thong!
    pause
    exit /b 1
)

python -c "import pyinstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo [THONG BAO] Dang cai dat pyinstaller...
    python -m pip install pyinstaller
)

echo Dang tien hanh dong goi bang PyInstaller...
python -m PyInstaller VideoResizer_win.spec --noconfirm

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo [THANH CONG] Ung dung da duoc dong goi tai:
    echo   dist\VideoResizer\VideoResizer.exe
    echo ========================================================
    if exist "profiles.json" (
        copy /y "profiles.json" "dist\VideoResizer\" >nul
    )
) else (
    echo.
    echo [LOI] Dong goi that bai. Vui long xem thong bao loi o tren.
)

pause
