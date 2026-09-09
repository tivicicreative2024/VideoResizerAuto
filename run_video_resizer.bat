@echo off
title Video Resizer Tool
echo ===================================================
echo Dang khoi dong Video Resizer Tool tren Windows...
echo ===================================================
python video_resizer.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [LOI] Khong the chay video_resizer.py!
    echo Vui long chay file 'install_requirements.bat' de cai dat thu vien.
    pause
)
