Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

Push-Location (Join-Path $root "frontend")
try {
  npm test
  npm run build
}
finally {
  Pop-Location
}
