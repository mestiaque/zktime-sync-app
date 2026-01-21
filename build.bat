@echo off
REM ---------------------------
REM Clean previous builds
REM ---------------------------
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
mkdir build

REM ---------------------------
REM Build EXE
REM ---------------------------
pyinstaller --noconsole --onefile --name ZKTimeSync ^
    --hidden-import=zk ^
    --hidden-import=requests ^
    app.py

REM ---------------------------
REM Build Installer
REM ---------------------------
iscc ZKTimeSync.iss

echo Done! Installer at Output\ZKTimeSyncInstaller.exe
pause
