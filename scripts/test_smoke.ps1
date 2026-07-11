Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root "venv\Scripts\python.exe"

Push-Location $root
try {
  & $python -m pytest backend\tests\test_smoke_happy_path.py
}
finally {
  Pop-Location
}

Push-Location (Join-Path $root "frontend")
try {
  npm run test:smoke
}
finally {
  Pop-Location
}
