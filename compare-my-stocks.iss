#define MyAppName "Compare My Stocks"
#define MyAppVersion "1.0.6"
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
Source: "dist\combined2\data\*"; DestDir: "{code:GetDir|0}"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist uninsneveruninstall
;Source: "dist\combined\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
;Source: "install\*"; DestDir: "{app}\install"; Flags: ignoreversion recursesubdirs createallsubdirs
;Source: "data\*"; DestDir: "{app}\data"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files
[Types]
Name: "full"; Description: "Full installation. Installs voila support (also python 3.9.6 if needed)."
Name: "minimal"; Description: "Just compare-my-stocks"


[Components]
Name: "program"; Description: "Program's Files"; Types: full minimal; Flags: fixed
Name: "voila"; Description: "Voila and python for displaying notebooks. \
Notice that voila requires python 3.9.6 (using exes) "; Types: full; 


[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional tasks:"; 

[Code]
var
DirPage: TInputDirWizardPage;

function GetDir(Param: String): String;
begin
Result := DirPage.Values[StrToInt(Param)];
end;

procedure InitializeWizard;
begin
{ create a directory input page }
DirPage := CreateInputDirPage(
  wpSelectDir, 'Select Data Folder', 'Select folder to use for local data', '(keep it the default way unless you know what you are doing)', False, '');
{ add directory input page items }
DirPage.Add('Data Folder');
{ assign default directories for the items from the previously stored data; if }
{ there are no data stored from the previous installation, use default folders }
{ of your choice }
DirPage.Values[0] := GetPreviousData('Directory1', GetEnv('USERPROFILE')+'\.compare_my_stocks');
end;

procedure RegisterPreviousData(PreviousDataKey: Integer);
begin
{ store chosen directories for the next run of the setup }
SetPreviousData(PreviousDataKey, 'Directory1', DirPage.Values[0]);
end;
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
