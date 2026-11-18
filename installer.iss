#define AppVersion "1.1.2"

[Setup]
AppId={{739C07E7-2130-4E73-8830-60B9295E89CD}
AppName=Video Resizer Pro
AppVersion={#AppVersion}
AppPublisher=tivicicreative2024
DefaultDirName={localappdata}\Programs\VideoResizer
DefaultGroupName=Video Resizer Pro
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=dist
OutputBaseFilename=VideoResizer-Setup-{#AppVersion}-win64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\VideoResizer.exe
CloseApplications=yes
SetupLogging=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "dist\VideoResizer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "INSTALL-WINDOWS.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "THIRD-PARTY.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "licenses\*"; DestDir: "{app}\licenses"; Flags: ignoreversion
Source: "video_resizer.py"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "resizer_ui.py"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "output_naming.py"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "ui_theme.qss"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "assets\*"; DestDir: "{app}\source\assets"; Flags: ignoreversion
Source: "test_ui.py"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "test_output_naming.py"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "test_worker.py"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "requirements-build.txt"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "profiles.example.json"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "VideoResizer_win.spec"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "build_exe.bat"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "installer.iss"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "build_installer.bat"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "test_packaging.py"; DestDir: "{app}\source"; Flags: ignoreversion

[Icons]
Name: "{group}\Video Resizer Pro"; Filename: "{app}\VideoResizer.exe"
Name: "{autodesktop}\Video Resizer Pro"; Filename: "{app}\VideoResizer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\VideoResizer.exe"; Description: "Open Video Resizer Pro"; Flags: nowait postinstall skipifsilent
