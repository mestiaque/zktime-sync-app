@echo off
REM ================================
REM ZKTimeSync Build & Installer
REM ================================

REM --- Clean previous builds ---
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist Output rmdir /s /q Output

echo Cleaning done.
echo.

REM --- Build EXE with PyInstaller ---
echo Building EXE...
pyinstaller --noconsole --onefile --name ZKTimeSync ^
    --hidden-import=zk ^
    --hidden-import=requests ^
    app.py

if errorlevel 1 (
    echo PyInstaller failed!
    pause
    exit /b 1
)

echo EXE built successfully!
echo.

REM --- Build Installer with Inno Setup ---
echo Building Installer...
REM Ensure Inno Setup CLI (iscc) is in PATH
if not exist ZKTimeSync.iss (
    echo ERROR: ZKTimeSync.iss not found!
    pause
    exit /b 1
)

iscc ZKTimeSync.iss

if errorlevel 1 (
    echo Inno Setup failed!
    pause
    exit /b 1
)

echo Installer built successfully!
echo.

echo All done! Installer is located at Output\ZKTimeSyncInstaller.exe
pause
