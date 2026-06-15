Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

Push-Location (Join-Path $root "backend")
try {
  ..\venv\Scripts\python.exe -m pytest
}
finally {
  Pop-Location
}
