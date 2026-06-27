param(
  [Parameter(Position = 1)]
  [string]$EnvFile,
  [string]$HostAddress = "127.0.0.1",
  [int]$Port = 8765,
  [switch]$Background
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$preflight = Join-Path $PSScriptRoot "live_llm_smoke_preflight.ps1"
$logDir = Join-Path $repoRoot "tests\.artifacts\logs"
$tmpDir = Join-Path $repoRoot "tests\.artifacts\tmp"
New-Item -ItemType Directory -Force $logDir, $tmpDir | Out-Null

if (-not [string]::IsNullOrWhiteSpace($EnvFile)) {
  & $preflight -EnvFile $EnvFile -RequireLiveReady
} else {
  & $preflight -RequireLiveReady
}

Push-Location (Join-Path $repoRoot "backend")
try {
  $python = Resolve-Path -LiteralPath "..\venv\Scripts\python.exe"
  if ($Background) {
    $server = Start-Process `
      -FilePath $python.Path `
      -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", $HostAddress, "--port", "$Port") `
      -PassThru `
      -WindowStyle Hidden `
      -RedirectStandardOutput (Join-Path $logDir "live-llm-uvicorn-stdout-$Port.log") `
      -RedirectStandardError (Join-Path $logDir "live-llm-uvicorn-stderr-$Port.log")
    Set-Content -LiteralPath (Join-Path $tmpDir "live-llm-server.pid") -Value $server.Id
    Write-Output "serverPid=$($server.Id)"
    Write-Output "serverPort=$Port"
  } else {
    & $python.Path -m uvicorn app.main:app --host $HostAddress --port $Port
  }
} finally {
  Pop-Location
}
