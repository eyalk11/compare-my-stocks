#define MyAppName "Compare My Stocks"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "eyalk11"
#define MyAppURL "https://github.com/eyalk11/compare-my-stocks"
#define MyAppExeName "compare-my-stocks.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{0F67A6FE-C5A8-403D-80A0-DFE5E626232F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\compare-my-stocks
DisableProgramGroupPage=yes
LicenseFile=C:\Users\ekarni\compare-my-stocks\LICENSE
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
; Uncomment the following line to run in non-administrative install mode (install for the current user only.)
;PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\combined2\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\combined2\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\combined2\data\*"; DestDir: "{#GetEnv('USERPROFILE')}\.compare_my_stocks"; Flags: ignoreversion recursesubdirs createallsubdirs
;Source: "dist\combined\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
;Source: "install\*"; DestDir: "{app}\install"; Flags: ignoreversion recursesubdirs createallsubdirs
;Source: "data\*"; DestDir: "{app}\data"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files
[Types]
Name: "full"; Description: "Full installation. Installs compare-my-stocks and python+voila  "
Name: "minimal"; Description: "Just compare-my-stocks"


[Components]
Name: "program"; Description: "Program Files"; Types: full minimal; Flags: fixed
Name: "voila"; Description: "Voila"; Types: full; 


[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional tasks:"; 

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var 
ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    
    if WizardIsComponentSelected('voila') then
    begin
      // Run your PowerShell script here
      Exec('powershell.exe', '-ExecutionPolicy Bypass -File "' + ExpandConstant('{app}') + '\install\internal.ps1"', '', SW_SHOW, ewWaitUntilTerminated, ResultCode);

      if ResultCode <> 0 then
      begin
        MsgBox('PowerShell script execution failed. Aborting installation.', mbError, MB_OK);
        WizardForm.Close;
      end;
    end;
     
  end;
end;



[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
