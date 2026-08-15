param(
  [string]$Profile = "beta",
  [switch]$SkipTests,
  [switch]$SkipFrontendBuild,
  [int]$Port = 8766
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$python = Join-Path $root "venv\Scripts\python.exe"
$artifactTmp = Join-Path $root "tests\.artifacts\tmp"
New-Item -ItemType Directory -Force $artifactTmp | Out-Null

function Invoke-NativeCommand {
  param(
    [Parameter(Mandatory = $true)]
    [scriptblock]$Command,
    [Parameter(Mandatory = $true)]
    [string]$Name
  )

  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "$Name failed with exit code $LASTEXITCODE."
  }
}

function Invoke-ProcessCommand {
  param(
    [Parameter(Mandatory = $true)]
    [string]$FilePath,
    [Parameter(Mandatory = $true)]
    [string[]]$ArgumentList,
    [Parameter(Mandatory = $true)]
    [string]$WorkingDirectory,
    [Parameter(Mandatory = $true)]
    [string]$Name
  )

  $process = Start-Process -FilePath $FilePath `
    -ArgumentList $ArgumentList `
    -WorkingDirectory $WorkingDirectory `
    -Wait `
    -PassThru `
    -NoNewWindow
  if ($process.ExitCode -ne 0) {
    throw "$Name failed with exit code $($process.ExitCode)."
  }
}

function Set-BetaEnvironment {
  $env:APP_ENV = $Profile
  $env:DEBUG = "false"
  $env:ENABLE_ADMIN_ROUTES = "false"
  $env:ENABLE_DEBUG_ROUTES = "false"
  $env:ENABLE_MOCK_SERVICES = "true"
  $env:ENABLE_REAL_LLM = "false"
  $env:ENABLE_REAL_VECTOR_DB = "false"
  $env:ENABLE_REAL_POI_PROVIDER = "false"
  $env:ENABLE_REAL_ROUTING = "false"
  $env:ENABLE_REAL_TICKETING = "false"
  $env:ENABLE_REAL_TTS = "false"
  $env:ENABLE_AFFILIATE_LINKS = "false"
  $env:ALLOW_EXTERNAL_CALLS = "true"
  $env:ENABLE_INTEGRATION_TESTS = "false"
  $env:EXTERNAL_CALL_ALLOWED_ENVIRONMENTS = "beta,staging"
  $env:ENABLE_AUTH = "true"
  $env:AUTH_PROVIDER = "oidc"
  $env:AUTH_REQUIRED_FOR_USER_FEATURES = "true"
  $env:AUTH_ALLOW_DEV_USER_FALLBACK = "false"
  $env:AUTH_JWT_ISSUER = "https://auth.example.test/"
  $env:AUTH_JWT_AUDIENCE = "litinerary-api"
  $env:AUTH_JWT_ALGORITHMS = "RS256"
  $env:AUTH_JWKS_URL = "https://auth.example.test/.well-known/jwks.json"
  $env:CORS_ALLOWED_ORIGINS = "http://127.0.0.1:5173"
  $env:LITINERARY_DATABASE_URL = "sqlite:///../tests/.artifacts/tmp/litinerary-beta-dry-run.db"
  $env:ENABLE_DURABLE_USAGE_CONTROLS = "true"
  $env:ANONYMOUS_ITINERARY_GENERATIONS_PER_MINUTE = "4"
  $env:ANONYMOUS_ITINERARY_GENERATIONS_PER_DAY = "20"
  $env:REGISTERED_USER_ITINERARY_GENERATIONS_PER_MINUTE = "10"
  $env:REGISTERED_USER_ITINERARY_GENERATIONS_PER_DAY = "100"
  $env:SUBSCRIBER_CHAT_MESSAGES_PER_MINUTE = "10"
  $env:SUBSCRIBER_CHAT_MESSAGES_PER_DAY = "100"
  $env:PROVIDER_DAILY_REQUEST_CEILING = "1000"
  $env:USAGE_COUNTER_RETENTION_DAYS = "90"
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

function Clear-ProviderEnvironment {
  $names = @(
    "LITINERARY_AI_PROVIDER",
    "LLM_PROVIDER",
    "LLM_API_KEY",
    "LLM_ALLOWED_ENVIRONMENTS",
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
    "TEXT_TO_SPEECH_API_KEY"
  )
  foreach ($name in $names) {
    Remove-Item -Path "Env:$name" -ErrorAction SilentlyContinue
  }
}

function Set-BackendTestEnvironment {
  Clear-ProviderEnvironment
  $names = @(
    "APP_ENV",
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
    "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS",
    "ENABLE_AUTH",
    "AUTH_PROVIDER",
    "AUTH_REQUIRED_FOR_USER_FEATURES",
    "AUTH_ALLOW_DEV_USER_FALLBACK",
    "AUTH_JWT_ISSUER",
    "AUTH_JWT_AUDIENCE",
    "AUTH_JWT_ALGORITHMS",
    "AUTH_JWKS_URL",
    "AUTH_PROVIDER_METADATA_URL",
    "CORS_ALLOWED_ORIGINS",
    "LITINERARY_DATABASE_URL",
    "ENABLE_DURABLE_USAGE_CONTROLS",
    "ANONYMOUS_ITINERARY_GENERATIONS_PER_MINUTE",
    "ANONYMOUS_ITINERARY_GENERATIONS_PER_DAY",
    "REGISTERED_USER_ITINERARY_GENERATIONS_PER_MINUTE",
    "REGISTERED_USER_ITINERARY_GENERATIONS_PER_DAY",
    "SUBSCRIBER_CHAT_MESSAGES_PER_MINUTE",
    "SUBSCRIBER_CHAT_MESSAGES_PER_DAY",
    "PROVIDER_DAILY_REQUEST_CEILING",
    "USAGE_COUNTER_RETENTION_DAYS",
    "PROVIDER_DAILY_COST_CEILING_USD"
  )
  foreach ($name in $names) {
    Remove-Item -Path "Env:$name" -ErrorAction SilentlyContinue
  }
}

function Set-FrontendEnvironment {
  Clear-ProviderEnvironment
  $names = @(
    "APP_ENV",
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
    "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS",
    "ENABLE_AUTH",
    "AUTH_PROVIDER",
    "AUTH_REQUIRED_FOR_USER_FEATURES",
    "AUTH_ALLOW_DEV_USER_FALLBACK",
    "AUTH_JWT_ISSUER",
    "AUTH_JWT_AUDIENCE",
    "AUTH_JWT_ALGORITHMS",
    "AUTH_JWKS_URL",
    "AUTH_PROVIDER_METADATA_URL",
    "CORS_ALLOWED_ORIGINS",
    "LITINERARY_DATABASE_URL",
    "ENABLE_DURABLE_USAGE_CONTROLS",
    "ANONYMOUS_ITINERARY_GENERATIONS_PER_MINUTE",
    "ANONYMOUS_ITINERARY_GENERATIONS_PER_DAY",
    "REGISTERED_USER_ITINERARY_GENERATIONS_PER_MINUTE",
    "REGISTERED_USER_ITINERARY_GENERATIONS_PER_DAY",
    "SUBSCRIBER_CHAT_MESSAGES_PER_MINUTE",
    "SUBSCRIBER_CHAT_MESSAGES_PER_DAY",
    "PROVIDER_DAILY_REQUEST_CEILING",
    "USAGE_COUNTER_RETENTION_DAYS",
    "PROVIDER_DAILY_COST_CEILING_USD"
  )
  foreach ($name in $names) {
    Remove-Item -Path "Env:$name" -ErrorAction SilentlyContinue
  }
  $env:PWD = $frontend
  $env:INIT_CWD = $frontend
}

Set-BetaEnvironment

Write-Host "== Litinerary beta dry run: config validation =="
Push-Location $backend
try {
  Invoke-NativeCommand { & $python -m scripts.validate_beta_config --profile $Profile } "Beta config validation"

  Write-Host "== Alembic migration status before upgrade =="
  Invoke-NativeCommand { & $python -m alembic heads } "Alembic heads"
  Invoke-NativeCommand { & $python -m alembic current } "Alembic current"

  Write-Host "== Beta database migration and seed =="
  Invoke-NativeCommand { & $python -m alembic upgrade head } "Alembic upgrade"
  Invoke-NativeCommand { & $python -m scripts.seed_database } "Beta seed data load"

  if (-not $SkipTests) {
    Write-Host "== Backend tests =="
    Set-BackendTestEnvironment
    $pytestTemp = "..\tests\.artifacts\tmp\pytest-beta-dry-run-$PID"
    Invoke-NativeCommand { & $python -m pytest --basetemp=$pytestTemp } "Backend tests"
    Set-BetaEnvironment
  }

  Write-Host "== Backend health/readiness smoke =="
  $server = Start-Process -FilePath $python -ArgumentList @(
    "-m", "uvicorn", "app.main:app",
    "--host", "127.0.0.1",
    "--port", "$Port"
  ) -PassThru -WindowStyle Hidden
  try {
    Start-Sleep -Seconds 3
    $baseUrl = "http://127.0.0.1:$Port"
    $health = Invoke-RestMethod -Uri "$baseUrl/api/health" -Headers @{ "X-Request-ID" = "req-beta-dry-run" }
    $readiness = Invoke-RestMethod -Uri "$baseUrl/api/readiness"
    try {
      $admin = Invoke-WebRequest -Uri "$baseUrl/api/admin/seed/validate"
    }
    catch {
      $admin = $_.Exception.Response
    }
    try {
      $debug = Invoke-WebRequest -Uri "$baseUrl/api/users/dev-reader/recommendations/mock"
    }
    catch {
      $debug = $_.Exception.Response
    }
    if ($health.status -ne "ok") { throw "Health check failed." }
    if ($readiness.status -ne "ready") { throw "Readiness check did not report ready." }
    if ($readiness.checks.database.configured -ne $true) { throw "Database URL should be explicit in beta dry run." }
    if ($readiness.checks.database.connectivity -ne "ok") { throw "Database connectivity should be ok in beta dry run." }
    if ($readiness.checks.database.migrations.status -ne "current") { throw "Database migration head should be current in beta dry run." }
    if ($readiness.checks.usageControls.durable -ne $true) { throw "Durable usage controls should be enabled in beta dry run." }
    if ($readiness.checks.externalCalls.allowed -ne $true) { throw "Managed auth external calls should be enabled in beta dry run." }
    foreach ($provider in $readiness.checks.providers) {
      if ($provider.providerType -eq "auth") {
        if ($provider.realEnabled -ne $true -or $provider.mode -ne "real") { throw "Auth provider should be real-enabled in beta dry run." }
        if ($provider.credentialsConfigured -ne $true -or $provider.externalCallsAllowed -ne $true) { throw "Auth provider should be configured in beta dry run." }
        continue
      }
      if ($provider.realEnabled -ne $false) { throw "Provider $($provider.providerType) should not be real-enabled in beta dry run." }
      if ($provider.externalCallsAllowed -ne $false) { throw "Provider $($provider.providerType) should not allow external calls in beta dry run." }
    }
    if ([int]$admin.StatusCode -ne 403) { throw "Admin route should be disabled in beta dry run." }
    if ([int]$debug.StatusCode -ne 403) { throw "Development-only route should be disabled in beta dry run." }
    Write-Host "Health/readiness/admin/debug checks passed."
  }
  finally {
    Stop-Process -Id $server.Id -Force
  }
}
finally {
  Pop-Location
}

if (-not $SkipTests -or -not $SkipFrontendBuild) {
  Set-FrontendEnvironment
  if (-not $SkipTests) {
    Write-Host "== Frontend tests =="
    Invoke-ProcessCommand -FilePath "cmd.exe" `
      -ArgumentList @("/c", "npm.cmd", "test") `
      -WorkingDirectory $frontend `
      -Name "Frontend tests"
  }
  if (-not $SkipFrontendBuild) {
    Write-Host "== Frontend build =="
    Invoke-ProcessCommand -FilePath "cmd.exe" `
      -ArgumentList @("/c", "npm.cmd", "run", "build") `
      -WorkingDirectory $frontend `
      -Name "Frontend build"
  }
}

Write-Host "Beta deployment dry run completed. No deployment was performed."
