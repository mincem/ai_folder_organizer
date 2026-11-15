@echo off
setlocal

rem Usage: organize.bat [folder]   (or drag a folder onto this file)
set "DEFAULT_TARGET=C:\Users\Mati\Desktop\comics"

rem Run from the project root so relative paths (cache\) resolve correctly
pushd "%~dp0"

rem Load KEY=VALUE pairs from .env (lines starting with # are ignored)
if exist ".env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do set "%%a=%%b"
)

set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=%DEFAULT_TARGET%"

".venv\Scripts\python.exe" "src\main.py" --path "%TARGET%"

popd
pause
