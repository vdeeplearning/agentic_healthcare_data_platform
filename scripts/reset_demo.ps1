$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
Push-Location $repo
try { & $python -m scripts.demo --reset } finally { Pop-Location }
