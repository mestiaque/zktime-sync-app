@echo off
REM Clean folders
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist Output rmdir /s /q Output

REM Build EXE
pyinstaller --noconsole --onefile --name ZKTimeSync ^
    --hidden-import=zk ^
    --hidden-import=requests ^
    app.py

REM Build Installer
iscc ZKTimeSync.iss

echo Done! Installer at Output\ZKTimeSyncInstaller.exe
pause
