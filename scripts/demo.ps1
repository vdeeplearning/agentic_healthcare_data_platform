$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $repo ".venv"
if (-not (Test-Path (Join-Path $venv "Scripts\python.exe"))) { python -m venv $venv }
$python = Join-Path $venv "Scripts\python.exe"
& $python -m pip install -e $repo
Push-Location $repo
try { & $python -m scripts.demo @args } finally { Pop-Location }
