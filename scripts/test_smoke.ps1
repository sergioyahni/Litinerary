Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

Push-Location (Join-Path $root "backend")
try {
  ..\venv\Scripts\python.exe -m pytest tests\test_smoke_happy_path.py
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
