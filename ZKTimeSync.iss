[Setup]
AppName=ZKTime Sync
AppVersion=1.0.0
AppId=ZKTimeSync
AppPublisher=M. ESTIAQUE
DefaultDirName={localappdata}\ZKTimeSync
DefaultGroupName=ZKTime Sync
OutputDir=Output
OutputBaseFilename=ZKTimeSyncInstaller
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\ZKTimeSync.exe


[Files]
Source: "dist\ZKTimeSync.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{userprofile}\.zkteco_sync"; Flags: uninsneveruninstall


[Icons]
Name: "{group}\ZKTime Sync"; Filename: "{app}\ZKTimeSync.exe"; IconFilename: "{app}\app_icon.ico"
Name: "{commondesktop}\ZKTime Sync"; Filename: "{app}\ZKTimeSync.exe"; IconFilename: "{app}\app_icon.ico"


[Run]
Filename: "{app}\ZKTimeSync.exe"; Description: "Start ZKTime Sync"; Flags: nowait postinstall skipifsilent

; Ensure the user's .zkteco_sync directory exists and is writable so the app can save config without extra steps
Filename: "cmd.exe"; Parameters: "/C icacls \"{userprofile}\\.zkteco_sync\" /grant \"{user}\":F /T"; Flags: runhidden shellexec
