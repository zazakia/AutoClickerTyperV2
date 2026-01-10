; AutoClickerTyper Installer Script
; Requires Inno Setup 6.0 or later: https://jrsoftware.org/isinfo.php

#define MyAppName "AutoClicker Typer"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Your Name"
#define MyAppURL "https://github.com/yourusername/AutoClickerTyperV2"
#define MyAppExeName "AutoClickerTyper.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{A7B8C9D0-E1F2-4A5B-8C9D-0E1F2A3B4C5D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE.txt
OutputDir=installer_output
OutputBaseFilename=AutoClickerTyper_Setup_v{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main Application
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "quick_prompts.json"; DestDir: "{app}"; Flags: ignoreversion

; Tesseract OCR (bundled from system installation)
; NOTE: This assumes Tesseract is installed at the default location
; If Tesseract is not found, the installer will continue but the app won't work
Source: "C:\Program Files\Tesseract-OCR\*"; DestDir: "{app}\Tesseract-OCR"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: TesseractExists

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
; Set Tesseract path in config (optional - the app will use bundled version)
Root: HKCU; Subkey: "Software\{#MyAppName}"; ValueType: string; ValueName: "TesseractPath"; ValueData: "{app}\Tesseract-OCR\tesseract.exe"; Flags: uninsdeletekey

[Code]
function TesseractExists: Boolean;
begin
  Result := DirExists('C:\Program Files\Tesseract-OCR');
  if not Result then
  begin
    Log('Tesseract OCR not found at default location. Skipping bundling.');
    MsgBox('Warning: Tesseract OCR not found on this system.' + #13#10 + 
           'The installer will continue, but you will need to install Tesseract separately.' + #13#10 + #13#10 +
           'Download from: https://github.com/UB-Mannheim/tesseract/wiki', 
           mbInformation, MB_OK);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigFile: String;
  ConfigContent: TArrayOfString;
  I: Integer;
  Modified: Boolean;
begin
  if CurStep = ssPostInstall then
  begin
    // Update config.py to use bundled Tesseract if it exists
    if TesseractExists then
    begin
      Log('Tesseract bundled successfully. App will use bundled version.');
    end;
  end;
end;

[Messages]
WelcomeLabel2=This will install [name/ver] on your computer.%n%nThis application automates clicking and typing based on screen text detection using OCR.%n%nIMPORTANT: Tesseract OCR is required and will be bundled if found on this system.
