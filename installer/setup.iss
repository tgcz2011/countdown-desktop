; Countdown Desktop installer (Inno Setup)
; build: "C:\Program Files\Inno Setup 7\ISCC.exe" /DVERSION=x.x.x.x installer\setup.iss

#ifndef VERSION
  #define VERSION "3.0.1.2"
#endif

#define APPNAME "Countdown Desktop"
#define EXENAME "CountdownDesktop.exe"

[Setup]
AppId={{7E0A4D2B-3C91-4F2E-9B55-COUNTDOWN01}
AppName={#APPNAME}
AppVersion={#VERSION}
VersionInfoVersion={#VERSION}
AppPublisher=tgcz2011
DefaultDirName={autopf}\CountdownDesktop
DefaultGroupName={#APPNAME}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible arm64
ArchitecturesInstallIn64BitMode=x64compatible arm64
OutputDir=..
OutputBaseFilename=CountdownDesktop_Setup_{#VERSION}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#EXENAME}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=force
RestartApplications=no

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Start automatically at login"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "..\dist\CountdownDesktop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: dontcopy noencryption

[Icons]
Name: "{group}\{#APPNAME}"; Filename: "{app}\{#EXENAME}"
Name: "{group}\Uninstall {#APPNAME}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#APPNAME}"; Filename: "{app}\{#EXENAME}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#EXENAME}"; Description: "{cm:LaunchProgram,{#APPNAME}}"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "CountdownDesktop"; ValueData: """{app}\{#EXENAME}"""; Flags: uninsdeletevalue; Tasks: autostart

[Code]
function WebView2Installed: Boolean;
var
  v: String;
begin
  Result :=
    RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', v) or
    RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', v) or
    RegQueryStringValue(HKCU, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', v);
  if Result then
    Result := (v <> '') and (v <> '0.0.0.0');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  rc: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    if not WebView2Installed then
    begin
      ExtractTemporaryFile('MicrosoftEdgeWebview2Setup.exe');
      Exec(ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe'), '/silent /install', '', SW_HIDE, ewWaitUntilTerminated, rc);
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  rc: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    { terminate running players/main so files can be removed }
    Exec('taskkill', '/F /IM CountdownDesktop.exe /T', '', SW_HIDE, ewWaitUntilTerminated, rc);
  end;
end;
