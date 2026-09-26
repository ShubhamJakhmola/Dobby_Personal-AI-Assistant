@echo off
set ROOT=%~dp0\..\..
cd /d "%ROOT%"
if not exist ".venv\Scripts\python.exe" (
  echo Dobby is not installed. Run scripts\windows\setup.ps1 first.
  exit /b 1
)
".venv\Scripts\python.exe" -m dobby %*
