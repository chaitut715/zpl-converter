; installer.iss — Inno Setup 6 script for ZPL Converter
; Compile with: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

#define MyAppName        "ZPL Converter"
#define MyAppVersion     "1.0.0"
#define MyAppPublisher   "ZPL Converter"
#define MyAppExeName     "zpl_converter.exe"
#define MyAppSourceDir   "dist\zpl_converter"

[Setup]
; Unique GUID — regenerate with Tools > Generate GUID in the Inno Setup IDE
AppId={{F3A8B2C1-D4E5-4F60-9A1B-C2D3E4F50678}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Let the user escalate to admin or stay per-user
PrivilegesRequiredOverridesAllowed=dialog
PrivilegesRequired=lowest
; Output
OutputDir=Output
OutputBaseFilename=zpl-converter-setup-{#MyAppVersion}
; Appearance
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
; Windows 10+ x64 only
MinVersion=10.0
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; \
  Description: "{cm:CreateDesktopIcon}"; \
  GroupDescription: "{cm:AdditionalIcons}"; \
  Flags: unchecked

[Files]
; Recursively install the entire onedir PyInstaller output
Source: "{#MyAppSourceDir}\*"; \
  DestDir: "{app}"; \
  Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; \
  Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; \
  Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; \
  Filename: "{app}\{#MyAppExeName}"; \
  Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; \
  Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove any files the app created in its own install folder
Type: filesandordirs; Name: "{app}"
