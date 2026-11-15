@echo off
setlocal

rem Usage: organize.bat [folder] [--country AR]   (or drag a folder onto this file)
set "DEFAULT_TARGET=C:\Users\Mati\Desktop\comics"

rem Run from the project root so relative paths (cache\) resolve correctly
pushd "%~dp0"

rem Load KEY=VALUE pairs from .env (lines starting with # are ignored)
if exist ".env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do set "%%a=%%b"
)

rem The folder can appear anywhere in the arguments (a folder dropped on a shortcut
rem is appended after the shortcut's own arguments). Any argument that is an existing
rem directory is taken as the folder; everything else (e.g. --country AR) is passed through.
set "TARGET="
set "EXTRA="
:collect
if "%~1"=="" goto run
if not defined TARGET if exist "%~1\" (
    set "TARGET=%~1"
    shift
    goto collect
)
set EXTRA=%EXTRA% %1
shift
goto collect

:run
if not defined TARGET set "TARGET=%DEFAULT_TARGET%"
".venv\Scripts\python.exe" "src\main.py" --path "%TARGET%"%EXTRA%

popd
pause
