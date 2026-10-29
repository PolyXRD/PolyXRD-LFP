; Inno Setup 6 script - PolyXRD LFP installer.
; APP_VER is passed by build_setup.bat as /DAPP_VER=vX.Y.Z (from lfp/version.py).
; Payload: the single-file exe produced by build_exe.bat (..\dist\PolyXRD-LFP-v*.exe).
; Keep comments ASCII-only to stay safe under any compiler codepage.

#define MyAppName "PolyXRD LFP"
#ifndef APP_VER
#define APP_VER "v0.0.0"
#endif

[Setup]
AppId=PolyXRD-LFP
AppName={#MyAppName}
AppVersion={#APP_VER}
AppPublisher=PolyXRD Team
AppPublisherURL=https://github.com/PolyXRD
AppUpdatesURL=https://github.com/PolyXRD
DefaultDirName={autopf}\PolyXRD-LFP
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE-CN
SetupIconFile=..\resources\app-icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
OutputDir=..\dist
OutputBaseFilename=PolyXRD-LFP-{#APP_VER}-Setup
Uninstallable=yes
CloseApplications=no

[Languages]
Name: "zh"; MessagesFile: "Languages\ChineseSimplified.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\PolyXRD-LFP-{#APP_VER}.exe"; DestDir: "{app}"; \
    DestName: "PolyXRD-LFP.exe"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\PolyXRD-LFP.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\PolyXRD-LFP.exe"; \
    Tasks: desktopicon

[Run]
Filename: "{app}\PolyXRD-LFP.exe"; \
    Description: "{cm:LaunchProgram,{#MyAppName}}"; \
    Flags: nowait postinstall skipifsilent
