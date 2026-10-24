; Version is passed by the build: iscc /DMyAppVersion=5.3.0 ZKTimeSync.iss
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

[Setup]
AppName=ZKTime Sync
AppVersion={#MyAppVersion}
AppVerName=ZKTime Sync {#MyAppVersion}
VersionInfoVersion={#MyAppVersion}
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
; Close the running app during install/update
CloseApplications=force
RestartApplications=no


[Tasks]
Name: "startup"; Description: "Start ZKTime Sync when Windows starts"; GroupDescription: "Startup:"


[Files]
Source: "dist\ZKTimeSync.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}"; Flags: uninsalwaysuninstall


[Icons]
Name: "{group}\ZKTime Sync"; Filename: "{app}\ZKTimeSync.exe"; IconFilename: "{app}\app_icon.ico"
Name: "{commondesktop}\ZKTime Sync"; Filename: "{app}\ZKTimeSync.exe"; IconFilename: "{app}\app_icon.ico"
Name: "{commonstartup}\ZKTime Sync"; Filename: "{app}\ZKTimeSync.exe"; IconFilename: "{app}\app_icon.ico"; Tasks: startup


[Run]
Filename: "{app}\ZKTimeSync.exe"; Description: "Launch ZKTimeSync"; Flags: nowait postinstall skipifsilent
; After an in-app (silent) update, start the new version again as the normal user
Filename: "{app}\ZKTimeSync.exe"; Flags: nowait runasoriginaluser skipifnotsilent
