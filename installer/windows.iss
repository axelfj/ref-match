; Inno Setup script for the Windows installer. CI passes the version:
;   iscc /DAppVersion=0.1.0 installer\windows.iss
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{A3C57F19-2E64-4B0D-8D93-51F0B7E4C803}
AppName=Ref Match
AppVersion={#AppVersion}
AppPublisher=ROMMUSER
AppPublisherURL=https://github.com/axelfj/ref-match
DefaultDirName={autopf}\Ref Match
DefaultGroupName=Ref Match
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
LicenseFile=..\LICENSE
OutputDir=Output
OutputBaseFilename=RefMatch-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\RefMatch.exe

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\RefMatch\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Ref Match"; Filename: "{app}\RefMatch.exe"
Name: "{group}\Uninstall Ref Match"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Ref Match"; Filename: "{app}\RefMatch.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\RefMatch.exe"; Description: "{cm:LaunchProgram,Ref Match}"; Flags: nowait postinstall skipifsilent
