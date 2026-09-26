@echo off
rem ============================================================================
rem  load.bat: src -> infobase (configuration is REPLACED, DB structure updated)
rem  Configurator and 1C:Enterprise must be closed: the training version
rem  allows only one session at a time.
rem  If the infobase does not exist yet, it is created.
rem ============================================================================
setlocal
chcp 65001 >nul

set "V8=C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
set "ROOT=%~dp0"
set "BASE=%ROOT%base"
set "SRC=%ROOT%src"
set "LOG=%ROOT%load.log"

if not exist "%V8%" (
    echo [FAIL] 1C platform not found: "%V8%"
    echo        Fix the V8 path at the top of this file.
    pause
    exit /b 1
)

if not exist "%BASE%\1Cv8.1CD" (
    echo [..] Infobase not found, creating "%BASE%"
    "%V8%" CREATEINFOBASE File="%BASE%" /Out "%LOG%"
    if errorlevel 1 goto fail
)

echo Configuration in "%BASE%" will be replaced with "%SRC%".
choice /C YN /M "Continue"
if errorlevel 2 (
    pause
    exit /b 1
)

echo [..] Loading configuration and updating database structure
"%V8%" DESIGNER /F "%BASE%" /DisableStartupDialogs /DisableStartupMessages /LoadConfigFromFiles "%SRC%" -updateConfigDumpInfo /UpdateDBCfg /Out "%LOG%"
if errorlevel 1 goto fail

echo [OK] Configuration loaded
pause
exit /b 0

:fail
echo [FAIL] See "%LOG%"
if exist "%LOG%" type "%LOG%"
pause
exit /b 1
