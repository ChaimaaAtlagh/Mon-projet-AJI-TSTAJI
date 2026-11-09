#define AppName "AJI TSTAJI FINAL"
#define AppVersion GetEnv("AJI_INSTALLER_VERSION")
#define AppSourceDir GetEnv("AJI_INSTALLER_SOURCE")
#define OutputDir GetEnv("AJI_INSTALLER_OUTPUT")
#define AppIcon GetEnv("AJI_INSTALLER_ICON")

[Setup]
AppId={{4D8C148E-2E8A-4AA4-8E9B-FC7D7C72D2A9}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=AJI TSTAJI
DefaultDirName={localappdata}\Programs\AJI TSTAJI FINAL
DefaultGroupName=AJI TSTAJI FINAL
UninstallDisplayIcon={app}\AJI_TSTAJI_FINAL.exe
PrivilegesRequired=lowest
UsePreviousAppDir=yes
DisableProgramGroupPage=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
OutputDir={#OutputDir}
OutputBaseFilename=AJI_TSTAJI_Setup
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile={#AppIcon}
CloseApplications=yes
RestartApplications=yes
VersionInfoVersion={#AppVersion}.0
VersionInfoProductName=AJI TSTAJI
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"

[Files]
Source: "{#AppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\AJI TSTAJI FINAL"; Filename: "{app}\AJI_TSTAJI_FINAL.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\AJI TSTAJI FINAL"; Filename: "{app}\AJI_TSTAJI_FINAL.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\AJI_TSTAJI_FINAL.exe"; Description: "Lancer AJI TSTAJI FINAL"; Flags: postinstall nowait skipifsilent
