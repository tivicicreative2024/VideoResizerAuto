@echo off
setlocal
cd /d "%~dp0"
call build_exe.bat
if errorlevel 1 exit /b 1
set "ISCC=.build-tools\inno-6.4.3\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo Install Inno Setup 6 first: https://jrsoftware.org/isdl.php
    pause
    exit /b 1
)
"%ISCC%" installer.iss
if errorlevel 1 exit /b 1
echo Installer: dist\VideoResizer-Setup-1.1.2-win64.exe
pause
