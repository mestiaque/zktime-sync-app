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
    --icon app_icon.ico ^
    --hidden-import=zk ^
    --hidden-import=requests ^
    --hidden-import=babel.numbers ^
    --collect-data=babel ^
    --collect-data=tkcalendar ^
    app.py

REM ---------------------------
REM Build Installer
REM ---------------------------
iscc ZKTimeSync.iss

echo Done! Installer at Output\ZKTimeSyncInstaller.exe
pause
