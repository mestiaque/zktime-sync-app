[Setup]
AppName=ZKTime Sync
AppVersion=1.0.0
AppId=ZKTimeSync
AppPublisher=M. ESTIAQUE
DefaultDirName={pf}\ZKTimeSync
DefaultGroupName=ZKTime Sync
OutputDir=Output
OutputBaseFilename=ZKTimeSyncInstaller
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
UninstallDisplayIcon={app}\ZKTimeSync.exe


[Files]
Source: "dist\ZKTimeSync.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}"; Flags: uninsalwaysuninstall


[Icons]
Name: "{group}\ZKTime Sync"; Filename: "{app}\ZKTimeSync.exe"; IconFilename: "{app}\app_icon.ico"
Name: "{commondesktop}\ZKTime Sync"; Filename: "{app}\ZKTimeSync.exe"; IconFilename: "{app}\app_icon.ico"


[Run]
Filename: "{app}\ZKTimeSync.exe"; Description: "Launch ZKTimeSync"; Flags: nowait postinstall skipifsilent
