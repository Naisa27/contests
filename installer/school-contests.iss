; AppVersion передаётся scripts/build.py из school_contests.__version__.
#ifndef AppVersion
  #error AppVersion must be provided by scripts/build.py
#endif
#define AppIdValue "{A6042B54-67A6-43D9-A13A-498F7B5A00E8}"

[Setup]
AppId={{A6042B54-67A6-43D9-A13A-498F7B5A00E8}
AppName=Школьные конкурсы
AppVersion={#AppVersion}
VersionInfoVersion={#AppVersion}
VersionInfoProductVersion={#AppVersion}
AppPublisher=SchoolContests
DefaultDirName={localappdata}\Programs\SchoolContests
DefaultGroupName=Школьные конкурсы
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=SchoolContests-{#AppVersion}-setup
SetupIconFile=..\src\school_contests\resources\images\app.ico
UninstallDisplayIcon={app}\SchoolContests.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableWelcomePage=no
CloseApplications=yes
RestartApplications=no

[Languages]
Name: russian; MessagesFile: compiler:Languages\Russian.isl

[Tasks]
Name: desktopicon; Description: Создать ярлык на рабочем столе; Flags: unchecked

[Files]
Source: ..\dist\SchoolContests\*; DestDir: {app}; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: {group}\Школьные конкурсы; Filename: {app}\SchoolContests.exe
Name: {autodesktop}\Школьные конкурсы; Filename: {app}\SchoolContests.exe; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: Software\SchoolContests; ValueType: string; ValueName: Version; ValueData: {#AppVersion}; Flags: uninsdeletekey
Root: HKCU; Subkey: Software\SchoolContests; ValueType: string; ValueName: InstallDir; ValueData: {app}

[Run]
Filename: {app}\SchoolContests.exe; Description: Запустить приложение; Flags: nowait postinstall skipifsilent

[Code]
var
  VersionPage: TOutputMsgWizardPage;
  PreviousVersion: String;
  PreviousDirectory: String;

function IsNewerVersion(const Candidate, Reference: String): Boolean;
var
  CandidatePacked, ReferencePacked: Int64;
begin
  Result := StrToVersion(Candidate, CandidatePacked) and StrToVersion(Reference, ReferencePacked);
  if Result then
    Result := ComparePackedVersion(CandidatePacked, ReferencePacked) > 0;
end;

function InitializeSetup(): Boolean;
begin
  if RegQueryStringValue(HKCU, 'Software\SchoolContests', 'InstallDir', PreviousDirectory)
      and FileExists(AddBackslash(PreviousDirectory) + 'SchoolContests.exe') then begin
    if not RegQueryStringValue(HKCU, 'Software\SchoolContests', 'Version', PreviousVersion) then
      GetVersionNumbersString(AddBackslash(PreviousDirectory) + 'SchoolContests.exe', PreviousVersion);
  end;
  Result := not IsNewerVersion(PreviousVersion, '{#AppVersion}');
  if not Result then
    MsgBox('Установлена более новая версия ' + PreviousVersion + '. Установка версии {#AppVersion} отменена.', mbError, MB_OK);
end;

procedure InitializeWizard();
var
  CaptionText, BodyText: String;
begin
  if PreviousVersion = '' then begin
    CaptionText := 'Установка версии {#AppVersion}';
    BodyText := 'Будет установлено приложение «Школьные конкурсы» версии {#AppVersion}.';
  end else if IsNewerVersion('{#AppVersion}', PreviousVersion) then begin
    CaptionText := 'Обновление с версии ' + PreviousVersion + ' до версии {#AppVersion}';
    BodyText := CaptionText + '.' + #13#10 + #13#10 + 'Мероприятия, участники и результаты сохранятся.';
  end else begin
    CaptionText := 'Повторная установка версии {#AppVersion}';
    BodyText := 'Версия {#AppVersion} уже установлена. Файлы приложения будут переустановлены, данные сохранятся.';
  end;
  VersionPage := CreateOutputMsgPage(wpWelcome, 'Версия приложения', CaptionText, BodyText);
end;
