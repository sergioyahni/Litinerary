Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root "venv\Scripts\python.exe"

Push-Location $root
try {
  & $python -m pytest backend\tests
}
finally {
  Pop-Location
}
