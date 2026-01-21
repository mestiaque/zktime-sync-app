[Setup]
AppName=ZKTime Sync
AppVersion=1.0
DefaultDirName={pf}\ZKTimeSync
DefaultGroupName=ZKTime Sync
OutputBaseFilename=ZKTimeSyncInstaller
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\ZKTimeSync.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ZKTime Sync"; Filename: "{app}\ZKTimeSync.exe"
Name: "{commondesktop}\ZKTime Sync"; Filename: "{app}\ZKTimeSync.exe"

[Run]
Filename: "{app}\ZKTimeSync.exe"; Flags: nowait postinstall skipifsilent
