$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw 'Python launcher (py) was not found. Install Python 3.11+ and enable the launcher.' }
py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe setup.py
Write-Host "Dobby Windows setup complete. Start with scripts\windows\start.ps1"
