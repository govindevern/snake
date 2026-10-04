#define SnakeVersion "1.1.0"
#define ProjectRoot AddBackslash(SourcePath) + ".."
#define ReleaseDir AddBackslash(ProjectRoot) + "release\v1.1.0"

[Setup]
AppId={{C5D36DF0-9B89-47F6-9D2F-DBFB5EF8399C}
AppName=Snake Programming Language
AppVersion={#SnakeVersion}
AppVerName=Snake {#SnakeVersion}
AppPublisher=Snake Language Contributors
DefaultDirName={code:GetDefaultInstallDir}
DefaultGroupName=Snake
DisableProgramGroupPage=yes
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog commandline
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
ChangesEnvironment=yes
UsePreviousAppDir=yes
OutputDir=..\release\v1.1.0
OutputBaseFilename=Snake-Setup-{#SnakeVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=Snake Programming Language {#SnakeVersion}
UninstallDisplayIcon={app}\snake.exe
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "startmenu"; Description: "Create a Start Menu shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "{#ReleaseDir}\standalone\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\RELEASE_NOTES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Snake"; Filename: "{app}\snake.exe"; Parameters: "--help"; Tasks: startmenu
Name: "{group}\Uninstall Snake"; Filename: "{uninstallexe}"

[Code]
const
  EnvironmentKey = 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment';
  SnakeWMSettingChange = $001A;
  SnakeHWNDBroadcast = $FFFF;
  SnakeSMTOAbortIfHung = $0002;

function SendMessageTimeout(hWnd: LongWord; Msg: LongWord; wParam: LongWord;
  lParam: String; fuFlags: LongWord; uTimeout: LongWord;
  var lpdwResult: Int64): Int64;
  external 'SendMessageTimeoutW@user32.dll stdcall';

function GetDefaultInstallDir(Param: String): String;
begin
  if IsAdminInstallMode then
    Result := ExpandConstant('{autopf}\Snake')
  else
    Result := ExpandConstant('{localappdata}\Programs\Snake');
end;

function NormalizePathEntry(Value: String): String;
begin
  Result := Lowercase(Trim(Value));
  while (Length(Result) > 3) and (Result[Length(Result)] = '\') do
    Delete(Result, Length(Result), 1);
end;

function PathContainsEntry(PathValue, Entry: String): Boolean;
var
  Remaining, Part: String;
  Separator: Integer;
begin
  Remaining := PathValue;
  Result := False;
  while Remaining <> '' do
  begin
    Separator := Pos(';', Remaining);
    if Separator = 0 then
    begin
      Part := Remaining;
      Remaining := '';
    end
    else
    begin
      Part := Copy(Remaining, 1, Separator - 1);
      Delete(Remaining, 1, Separator);
    end;
    if NormalizePathEntry(Part) = NormalizePathEntry(Entry) then
    begin
      Result := True;
      Exit;
    end;
  end;
end;

function AddPathEntry(PathValue, Entry: String): String;
begin
  if PathValue = '' then
    Result := Entry
  else if PathValue[Length(PathValue)] = ';' then
    Result := PathValue + Entry
  else
    Result := PathValue + ';' + Entry;
end;

function RemovePathEntry(PathValue, Entry: String): String;
var
  Part: String;
  StartAt, Separator: Integer;
  KeepPart: Boolean;
begin
  Result := '';
  StartAt := 1;
  KeepPart := False;
  while StartAt <= Length(PathValue) + 1 do
  begin
    Separator := Pos(';', Copy(PathValue, StartAt, Length(PathValue)));
    if Separator = 0 then
    begin
      Part := Copy(PathValue, StartAt, Length(PathValue));
      StartAt := Length(PathValue) + 2;
    end
    else
    begin
      Part := Copy(PathValue, StartAt, Separator - 1);
      StartAt := StartAt + Separator;
    end;
    if NormalizePathEntry(Part) <> NormalizePathEntry(Entry) then
    begin
      if KeepPart then
        Result := Result + ';';
      Result := AddPathEntry(Result, Part);
      KeepPart := True;
    end;
  end;
end;

function EnvironmentRootKey: Integer;
begin
  if IsAdminInstallMode then
    Result := HKEY_LOCAL_MACHINE
  else
    Result := HKEY_CURRENT_USER;
end;

procedure UpdateInstallPath(AddEntry: Boolean);
var
  CurrentPath, InstallPath, UpdatedPath: String;
  KeyRoot: Integer;
  BroadcastResult: Int64;
begin
  KeyRoot := EnvironmentRootKey;
  InstallPath := ExpandConstant('{app}');
  if Pos(';', InstallPath) > 0 then
    RaiseException('The installation folder cannot contain a semicolon because it must be added to PATH.');
  if not RegQueryStringValue(KeyRoot, EnvironmentKey, 'Path', CurrentPath) then
  begin
    if RegValueExists(KeyRoot, EnvironmentKey, 'Path') then
      RaiseException('Could not safely read the existing PATH value; it was not changed.');
    CurrentPath := '';
  end;

  if AddEntry then
  begin
    if not PathContainsEntry(CurrentPath, InstallPath) then
    begin
      UpdatedPath := AddPathEntry(CurrentPath, InstallPath);
      if not RegWriteExpandStringValue(KeyRoot, EnvironmentKey, 'Path', UpdatedPath) then
        RaiseException('Could not add Snake to PATH. Add this folder manually: ' + InstallPath);
    end;
  end
  else if PathContainsEntry(CurrentPath, InstallPath) then
  begin
    UpdatedPath := RemovePathEntry(CurrentPath, InstallPath);
    if UpdatedPath = '' then
    begin
      if not RegDeleteValue(KeyRoot, EnvironmentKey, 'Path') then
        RaiseException('Could not remove Snake from PATH during uninstall.');
    end
    else if not RegWriteExpandStringValue(KeyRoot, EnvironmentKey, 'Path', UpdatedPath) then
      RaiseException('Could not remove Snake from PATH during uninstall.');
  end;

  SendMessageTimeout(SnakeHWNDBroadcast, SnakeWMSettingChange, 0, 'Environment',
    SnakeSMTOAbortIfHung, 5000, BroadcastResult);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    UpdateInstallPath(True);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    UpdateInstallPath(False);
end;
