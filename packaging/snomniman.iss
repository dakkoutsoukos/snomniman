; Inno Setup script for SNOMNIMAN (deployment-strategy.md Phase 2).
;
; Build with (Inno Setup 6, after the PyInstaller onedir build exists at
; packaging\dist\SNOMNIMAN\):
;
;   "C:\Users\<you>\AppData\Local\Programs\Inno Setup 6\ISCC.exe" packaging\snomniman.iss
;
; Produces packaging\installer_dist\SNOMNIMAN_Setup_<version>.exe.
;
; Design choices (see docs/deployment-strategy.md Section 3 for the full
; justification): per-user install by default (no admin/UAC prompt, since
; lab machines often restrict admin rights) via PrivilegesRequired=lowest +
; the {autopf} directory constant, which resolves to
; %LOCALAPPDATA%\Programs\SNOMNIMAN for a per-user install or
; %ProgramFiles%\SNOMNIMAN if the researcher explicitly opts into an
; all-users install from the wizard's privilege dialog.

#include "version.iss"

#define MyAppName "SNOMNIMAN"
#define MyAppPublisher "SNOMNIMAN Project"
#define MyAppExeName "SNOMNIMAN.exe"

[Setup]
AppId={{4B6F6A2E-6C1A-4E9E-9C3D-2B7F3A9E1D40}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=SNOMNIMAN Setup
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
SetupIconFile=snomniman.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
OutputDir=installer_dist
OutputBaseFilename=SNOMNIMAN_Setup_{#MyAppVersion}
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\SNOMNIMAN\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
