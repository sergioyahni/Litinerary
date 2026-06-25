param(
  [int]$Port = 8765,
  [switch]$SkipPreflightHarness
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$backend = Join-Path $root "backend"
$python = Join-Path $root "venv\Scripts\python.exe"
$harness = Join-Path $root "scripts\deployment_readiness_check.ps1"
$recordPath = Join-Path $root "docs\local-offline-deployment-rehearsal-record.md"
$runId = "$PID"
$dbName = "local-offline-rehearsal-$runId.db"
$dbPath = Join-Path $backend $dbName
$baseUrl = "http://127.0.0.1:$Port"

$providerEnvNames = @(
  "APP_ENV",
  "NODE_ENV",
  "DEBUG",
  "ENABLE_ADMIN_ROUTES",
  "ENABLE_DEBUG_ROUTES",
  "ENABLE_MOCK_SERVICES",
  "ENABLE_REAL_LLM",
  "ENABLE_REAL_VECTOR_DB",
  "ENABLE_REAL_POI_PROVIDER",
  "ENABLE_REAL_ROUTING",
  "ENABLE_REAL_TICKETING",
  "ENABLE_REAL_TTS",
  "ENABLE_AFFILIATE_LINKS",
  "ALLOW_EXTERNAL_CALLS",
  "ENABLE_INTEGRATION_TESTS",
  "ENABLE_STAGED_INTERNAL_LLM_TESTING",
  "ENABLE_INTERNAL_ACCESS_GATE",
  "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS",
  "LLM_ALLOWED_ENVIRONMENTS",
  "ENABLE_AUTH",
  "AUTH_PROVIDER",
  "AUTH_REQUIRED_FOR_USER_FEATURES",
  "AUTH_ALLOW_DEV_USER_FALLBACK",
  "AUTH_JWT_ISSUER",
  "AUTH_JWT_AUDIENCE",
  "AUTH_JWKS_URL",
  "AUTH_PROVIDER_METADATA_URL",
  "CORS_ALLOWED_ORIGINS",
  "LITINERARY_DATABASE_URL",
  "LITINERARY_AI_PROVIDER",
  "LLM_PROVIDER",
  "LLM_API_KEY",
  "OPENAI_API_KEY",
  "LLM_MODEL_NAME",
  "LITINERARY_VECTOR_PROVIDER",
  "VECTOR_DB_PROVIDER",
  "VECTOR_DB_URL",
  "VECTOR_DB_API_KEY",
  "QDRANT_URL",
  "QDRANT_API_KEY",
  "LITINERARY_POI_VERIFICATION_PROVIDER",
  "POI_VERIFICATION_PROVIDER",
  "POI_PROVIDER",
  "POI_PROVIDER_API_KEY",
  "GOOGLE_PLACES_API_KEY",
  "POI_VERIFICATION_API_KEY",
  "ROUTING_PROVIDER",
  "ROUTING_API_KEY",
  "OPENROUTESERVICE_API_KEY",
  "TICKETING_PROVIDER",
  "TICKETING_API_KEY",
  "AFFILIATE_PROVIDER",
  "AFFILIATE_API_KEY",
  "TTS_PROVIDER",
  "TTS_API_KEY",
  "TEXT_TO_SPEECH_API_KEY",
  "PROVIDER_DAILY_COST_CEILING_USD"
)

function Invoke-NativeCommand {
  param(
    [Parameter(Mandatory = $true)]
    [scriptblock]$Command,
    [Parameter(Mandatory = $true)]
    [string]$Name
  )

  Write-Host "== $Name =="
  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "$Name failed with exit code $LASTEXITCODE."
  }
}

function Clear-RehearsalProviderEnvironment {
  foreach ($name in $providerEnvNames) {
    Remove-Item -Path "Env:$name" -ErrorAction SilentlyContinue
  }
}

function Set-RehearsalEnvironment {
  Clear-RehearsalProviderEnvironment
  $env:APP_ENV = "development"
  $env:DEBUG = "false"
  $env:ENABLE_ADMIN_ROUTES = "true"
  $env:ENABLE_DEBUG_ROUTES = "false"
  $env:ENABLE_MOCK_SERVICES = "true"
  $env:ENABLE_REAL_LLM = "false"
  $env:ENABLE_REAL_VECTOR_DB = "false"
  $env:ENABLE_REAL_POI_PROVIDER = "false"
  $env:ENABLE_REAL_ROUTING = "false"
  $env:ENABLE_REAL_TICKETING = "false"
  $env:ENABLE_REAL_TTS = "false"
  $env:ENABLE_AFFILIATE_LINKS = "false"
  $env:ALLOW_EXTERNAL_CALLS = "false"
  $env:ENABLE_INTEGRATION_TESTS = "false"
  $env:ENABLE_STAGED_INTERNAL_LLM_TESTING = "false"
  $env:ENABLE_INTERNAL_ACCESS_GATE = "false"
  $env:EXTERNAL_CALL_ALLOWED_ENVIRONMENTS = "production"
  $env:LLM_ALLOWED_ENVIRONMENTS = "development,production"
  $env:ENABLE_AUTH = "false"
  $env:AUTH_PROVIDER = "dev"
  $env:AUTH_ALLOW_DEV_USER_FALLBACK = "true"
  $env:CORS_ALLOWED_ORIGINS = "http://127.0.0.1:5173,http://127.0.0.1:4173"
  $env:LITINERARY_DATABASE_URL = "sqlite:///./$dbName"
  $env:LITINERARY_AI_PROVIDER = "fake"
  $env:LLM_PROVIDER = "fake"
  $env:LITINERARY_VECTOR_PROVIDER = "fake"
  $env:VECTOR_DB_PROVIDER = "fake"
  $env:LITINERARY_POI_VERIFICATION_PROVIDER = "mock"
  $env:POI_VERIFICATION_PROVIDER = "mock"
  $env:POI_PROVIDER = "mock"
  $env:ROUTING_PROVIDER = "mock"
  $env:TICKETING_PROVIDER = "mock"
  $env:AFFILIATE_PROVIDER = "mock"
  $env:TTS_PROVIDER = "mock"
  $env:PROVIDER_DAILY_COST_CEILING_USD = "0"
}

function Test-PortOpen {
  param([Parameter(Mandatory = $true)][int]$TargetPort)

  $client = [System.Net.Sockets.TcpClient]::new()
  try {
    $task = $client.ConnectAsync("127.0.0.1", $TargetPort)
    if (-not $task.Wait(750)) {
      return $false
    }
    return $client.Connected
  }
  catch {
    return $false
  }
  finally {
    $client.Dispose()
  }
}

function Wait-ForHealth {
  for ($attempt = 1; $attempt -le 30; $attempt += 1) {
    try {
      $health = Invoke-RestMethod -Uri "$baseUrl/api/health" -Headers @{ "X-Request-ID" = "req-local-offline-rehearsal" }
      if ($health.status -eq "ok") {
        return $health
      }
    }
    catch {
      Start-Sleep -Seconds 1
    }
  }
  throw "Backend did not become healthy on $baseUrl."
}

function Assert-SafeJson {
  param(
    [Parameter(Mandatory = $true)]
    [object]$Payload,
    [Parameter(Mandatory = $true)]
    [string]$Label
  )

  $json = $Payload | ConvertTo-Json -Depth 40 -Compress
  $forbidden = @(
    "Authorization",
    "rawProviderPayload",
    "raw_provider_payload",
    "/v1/chat/completions",
    "sk-[A-Za-z0-9_-]{20,}",
    "Bearer\s+[A-Za-z0-9._-]{20,}",
    "AKIA[A-Z0-9]{16}",
    "ghp_[A-Za-z0-9]{20,}",
    "AIza[A-Za-z0-9_-]{20,}",
    "-----BEGIN [A-Z ]+PRIVATE KEY-----"
  )
  foreach ($pattern in $forbidden) {
    if ($json -match $pattern) {
      throw "$Label contains forbidden secret/raw-provider pattern: $pattern"
    }
  }
}

function Assert-OfflineReadiness {
  param([Parameter(Mandatory = $true)][object]$Readiness)

  if ($Readiness.status -ne "ready") {
    throw "Readiness status was not ready."
  }
  if ($Readiness.checks.externalCalls.allowed -ne $false) {
    throw "Readiness reports external calls allowed."
  }
  if ($Readiness.checks.externalCalls.stagedInternalLlmTestingEnabled -ne $false) {
    throw "Readiness reports staged internal LLM testing enabled."
  }
  foreach ($provider in $Readiness.checks.providers) {
    if ($provider.mode -ne "mock") {
      throw "Provider $($provider.providerType) is not mock/offline."
    }
    if ($provider.realEnabled -ne $false) {
      throw "Provider $($provider.providerType) is real-enabled."
    }
    if ($provider.externalCallsAllowed -ne $false) {
      throw "Provider $($provider.providerType) allows external calls."
    }
  }
}

function Write-RehearsalRecord {
  param(
    [Parameter(Mandatory = $true)][string]$Result,
    [Parameter(Mandatory = $true)][string]$HarnessResult,
    [Parameter(Mandatory = $true)][string]$HealthResult,
    [Parameter(Mandatory = $true)][string]$ReadinessSummary,
    [Parameter(Mandatory = $true)][string]$SeedSummary,
    [Parameter(Mandatory = $true)][string]$GenerationSummary,
    [Parameter(Mandatory = $true)][string]$ShutdownSummary,
    [Parameter(Mandatory = $true)][string]$Limitations
  )

  $timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
  $content = @"
# Local Offline Deployment Rehearsal Record

## Status

- Result: $Result
- Executed at: $timestamp
- Execution context: local Windows PowerShell from repository root
- Rehearsal port: $Port
- Environment posture: offline/mock only

## Preflight Harness

- Harness command: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\deployment_readiness_check.ps1`
- Harness result: $HarnessResult

## Backend Health

- Health result: $HealthResult

## Readiness Provider Posture

$ReadinessSummary

## Seed Reset And Validation

$SeedSummary

## Mock Itinerary Generation

$GenerationSummary

## Shutdown

$ShutdownSummary

## Safety Confirmations

- Live LLM request made: no
- `/v1/chat/completions` called: no
- External providers enabled: no
- Real API key required or read: no
- Secret-like values added to this evidence: no
- Raw provider payload added to this evidence: no

## Limitations

$Limitations

## Next Recommended Action

Use this record as local offline/mock rehearsal evidence only. Cloud-specific deployment rehearsal, staged log-sink review, production-grade internal access boundary, approved request/spend ceilings, owner approvals, and optional provider-gated tests remain separate blockers.
"@
  Set-Content -LiteralPath $recordPath -Value $content -Encoding UTF8
}

Write-Host "Litinerary local offline deployment rehearsal starting."
Write-Host "No live providers are enabled by this rehearsal."

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
  throw "Python executable not found at $python"
}
if (Test-PortOpen -TargetPort $Port) {
  throw "Port $Port is already in use. Stop the existing listener or choose another port with -Port."
}

$server = $null
$harnessResult = "not run"
$healthResult = "not run"
$readinessSummary = "- Not run."
$seedSummary = "- Not run."
$generationSummary = "- Not run."
$shutdownSummary = "- Not run."
$result = "failed"

try {
  if ($SkipPreflightHarness) {
    $harnessResult = "skipped by explicit -SkipPreflightHarness flag"
  } else {
    Invoke-NativeCommand {
      & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $harness
    } "Deployment-readiness preflight harness"
    $harnessResult = "passed"
  }

  Set-RehearsalEnvironment
  if (Test-Path -LiteralPath $dbPath) {
    Remove-Item -LiteralPath $dbPath -Force
  }

  Push-Location $backend
  try {
    Invoke-NativeCommand { & $python -m alembic upgrade head } "Apply migrations to rehearsal DB"
    Invoke-NativeCommand { & $python -m scripts.seed_database } "Seed rehearsal DB"
    $server = Start-Process -FilePath $python -ArgumentList @(
      "-m", "uvicorn", "app.main:app",
      "--host", "127.0.0.1",
      "--port", "$Port"
    ) -PassThru -WindowStyle Hidden
  }
  finally {
    Pop-Location
  }

  $health = Wait-ForHealth
  Assert-SafeJson -Payload $health -Label "Health response"
  $healthResult = "passed (`/api/health` returned ok)"

  $readiness = Invoke-RestMethod -Uri "$baseUrl/api/readiness"
  Assert-OfflineReadiness -Readiness $readiness
  Assert-SafeJson -Payload $readiness -Label "Readiness response"
  $providerNames = @($readiness.checks.providers | ForEach-Object { "$($_.providerType)=$($_.providerName)/$($_.mode)" })
  $readinessSummary = "- Status: $($readiness.status)`n- External calls allowed: $($readiness.checks.externalCalls.allowed)`n- Providers: $($providerNames -join ', ')"

  $reset = Invoke-RestMethod -Uri "$baseUrl/api/admin/seed/reset" -Method Post
  $validation = Invoke-RestMethod -Uri "$baseUrl/api/admin/seed/validate"
  Assert-SafeJson -Payload $reset -Label "Seed reset response"
  Assert-SafeJson -Payload $validation -Label "Seed validation response"
  if ($validation.valid -ne $true) {
    throw "Seed validation did not pass."
  }
  $seedSummary = "- Reset result: passed`n- Validation result: passed`n- Counts: destinations=$($reset.counts.destinations), books=$($reset.counts.books), pois=$($reset.counts.pois), itineraries=$($reset.counts.itineraries)"

  $requestBody = @{
    destinationId = "london"
    bookId = "sherlock-holmes"
    durationDays = 1
    transportationMode = "walking"
  } | ConvertTo-Json
  $generated = Invoke-RestMethod -Uri "$baseUrl/api/itinerary/generate" -Method Post -ContentType "application/json" -Body $requestBody
  Assert-SafeJson -Payload $generated -Label "Itinerary generation response"
  $generatedText = $generated | ConvertTo-Json -Depth 40 -Compress
  if ($generated.itinerary.providerName -eq "openai_compatible" -or $generatedText -match "openai_compatible") {
    throw "Mock rehearsal generation unexpectedly used openai_compatible."
  }
  if ($generated.itinerary.providerName -ne "mock_ai") {
    throw "Mock rehearsal generation did not use mock_ai."
  }
  if ($generatedText -notmatch "Baker Street") {
    throw "Mock rehearsal generation did not include Baker Street."
  }
  $routingProvider = $generated.itinerary.days[0].routingProviderMetadata.provider_name
  if ($routingProvider -ne "mock_routing") {
    throw "Mock rehearsal routing provider was not mock_routing."
  }
  $generationSummary = "- Result: passed`n- Title: $($generated.itinerary.title)`n- LLM provider: $($generated.itinerary.providerName)`n- Routing provider: $routingProvider`n- Baker Street present: yes"

  $result = "passed"
}
finally {
  if ($server -and -not $server.HasExited) {
    Stop-Process -Id $server.Id -Force
    Wait-Process -Id $server.Id -Timeout 10 -ErrorAction SilentlyContinue
  }
  $listenerClosed = $true
  for ($attempt = 1; $attempt -le 10; $attempt += 1) {
    if (-not (Test-PortOpen -TargetPort $Port)) {
      $listenerClosed = $true
      break
    }
    $listenerClosed = $false
    Start-Sleep -Milliseconds 500
  }
  if ($listenerClosed) {
    $shutdownSummary = "- Backend stopped: yes`n- Listener remains on port ${Port}: no"
  } else {
    $shutdownSummary = "- Backend stopped: attempted`n- Listener remains on port ${Port}: yes"
  }
  $limitations = "- Local loopback rehearsal only; no cloud infrastructure was exercised.`n- Frontend runtime preview is documented separately; the preflight harness validates frontend tests, typecheck, and build.`n- Staged internal and public/beta live modes remain no-go."
  Write-RehearsalRecord `
    -Result $result `
    -HarnessResult $harnessResult `
    -HealthResult $healthResult `
    -ReadinessSummary $readinessSummary `
    -SeedSummary $seedSummary `
    -GenerationSummary $generationSummary `
    -ShutdownSummary $shutdownSummary `
    -Limitations $limitations

  if (Test-Path -LiteralPath $dbPath) {
    $removed = $false
    for ($attempt = 1; $attempt -le 5; $attempt += 1) {
      try {
        Remove-Item -LiteralPath $dbPath -Force
        $removed = $true
        break
      }
      catch {
        Start-Sleep -Milliseconds 500
      }
    }
    if (-not $removed) {
      Write-Warning "Temporary rehearsal database could not be removed: $dbPath"
    }
  }
}

if ($result -ne "passed") {
  throw "Local offline deployment rehearsal failed. Sanitized record written to docs\local-offline-deployment-rehearsal-record.md."
}

Write-Host "Local offline deployment rehearsal passed."
Write-Host "Sanitized record written to docs\local-offline-deployment-rehearsal-record.md."
