; Inno Setup script for CSV_Tools (per-user install, no admin rights needed).
; Build dist\CSV_Tools.exe first (build_windows.bat), then:
;   iscc installer.iss
; Output: dist\CSV_Tools_Setup.exe

#define AppName "CSV Tools"
#define AppVersion "1.0"
#define AppExe "CSV_Tools.exe"

[Setup]
AppId={{48D09546-DC4E-44E7-BCFA-170815C8A221}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=protolab.tech
AppPublisherURL=https://protolab.tech
DefaultDirName={localappdata}\Programs\CSV_Tools
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=CSV_Tools_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExe}
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; The app reads input\ and writes output\ next to its .exe.
Name: "{app}\input"
Name: "{app}\output"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{#AppName} input folder"; Filename: "{app}\input"
Name: "{group}\{#AppName} output folder"; Filename: "{app}\output"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
