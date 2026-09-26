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

if not exist "%V8%" (
    echo [FAIL] 1C platform not found: "%V8%"
    echo        Fix the V8 path at the top of this file.
    pause
    exit /b 1
)
if not exist "%BASE%\1Cv8.1CD" (
    echo [FAIL] Infobase not found: "%BASE%". Run load.bat first.
    pause
    exit /b 1
)

set "MODE="
if exist "%SRC%\ConfigDumpInfo.xml" set "MODE=-update -force"

echo [..] Dumping configuration to "%SRC%" %MODE%
"%V8%" DESIGNER /F "%BASE%" /DisableStartupDialogs /DisableStartupMessages /DumpConfigToFiles "%SRC%" -Format Hierarchical %MODE% /Out "%LOG%"
if errorlevel 1 goto fail

echo [OK] Configuration dumped
pause
exit /b 0

:fail
echo [FAIL] See "%LOG%"
if exist "%LOG%" type "%LOG%"
pause
exit /b 1
