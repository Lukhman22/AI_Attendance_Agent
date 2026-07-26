[Setup]
AppName=AI Attendance Agent
AppVersion=1.0.0
DefaultDirName={pf}\AI Attendance Agent
DefaultGroupName=AI Attendance Agent
OutputDir=.\dist
OutputBaseFilename=AI Attendance Agent Setup
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile=.\frontend\public\favicon.ico
UninstallDisplayIcon={app}\AI Attendance Agent.exe
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\AI Attendance Agent\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\AI Attendance Agent"; Filename: "{app}\AI Attendance Agent.exe"
Name: "{commondesktop}\AI Attendance Agent"; Filename: "{app}\AI Attendance Agent.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AI Attendance Agent.exe"; Description: "{cm:LaunchProgram,AI Attendance Agent}"; Flags: nowait postinstall skipifsilent
