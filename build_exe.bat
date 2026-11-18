@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m PyInstaller VideoResizer_win.spec --noconfirm
if errorlevel 1 goto failed
echo Application: dist\VideoResizer\VideoResizer.exe
pause
exit /b 0
:failed
echo Build failed. See the error above.
pause
exit /b 1
