@echo off
rem ============================================================================
rem  dump.bat: infobase -> src (Hierarchical format)
rem  The first run is a full dump, next runs are incremental (ConfigDumpInfo.xml).
rem  Configurator and 1C:Enterprise must be closed.
rem ============================================================================
setlocal
chcp 65001 >nul

set "V8=C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
set "ROOT=%~dp0"
set "BASE=%ROOT%base"
set "SRC=%ROOT%src"
set "LOG=%ROOT%dump.log"

set "MODE="
if exist "%SRC%\ConfigDumpInfo.xml" set "MODE=-update -force"

echo [..] Dumping configuration to "%SRC%" %MODE%
"%V8%" DESIGNER /F "%BASE%" /DisableStartupDialogs /DisableStartupMessages /DumpConfigToFiles "%SRC%" -Format Hierarchical %MODE% /Out "%LOG%"
if errorlevel 1 goto fail

echo [OK] Configuration dumped
exit /b 0

:fail
echo [FAIL] See "%LOG%"
type "%LOG%"
exit /b 1
