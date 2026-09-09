@echo off
title Dong goi Video Resizer thanh file EXE (Windows)
echo ===================================================
echo Dang chuan bi dong goi ung dung thanh file .exe...
echo ===================================================
pip install pyinstaller -q
pyinstaller VideoResizer_Windows.spec
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ===================================================
    echo [THANH CONG] File ung dung VideoResizer.exe da duoc tao tai:
    echo        dist\VideoResizer\VideoResizer.exe
    echo ===================================================
) else (
    echo.
    echo [LOI] Co loi xay ra trong qua trinh dong goi!
)
echo.
pause
