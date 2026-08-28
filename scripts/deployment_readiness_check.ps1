param(
  [switch]$Full,
  [switch]$SkipFrontendBuild,
  [int]$Port = 8767
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$python = Join-Path $root "venv\Scripts\python.exe"
$runId = "$PID"
$artifactTmp = Join-Path $root "tests\.artifacts\tmp"
New-Item -ItemType Directory -Force $artifactTmp | Out-Null

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

  Write-Host "== $Name =="
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

function Clear-DeploymentProviderEnvironment {
  foreach ($name in $providerEnvNames) {
    Remove-Item -Path "Env:$name" -ErrorAction SilentlyContinue
  }
}

function Set-OfflineProfileEnvironment {
  param([Parameter(Mandatory = $true)][string]$Profile)

  Clear-DeploymentProviderEnvironment
  $env:APP_ENV = $Profile
  $env:DEBUG = if ($Profile -in @("development", "test")) { "true" } else { "false" }
  $env:ENABLE_ADMIN_ROUTES = if ($Profile -in @("development", "test")) { "true" } else { "false" }
  $env:ENABLE_DEBUG_ROUTES = if ($Profile -in @("development", "test")) { "true" } else { "false" }
  $env:ENABLE_MOCK_SERVICES = "true"
  $env:ENABLE_REAL_LLM = "false"
  $env:ENABLE_REAL_VECTOR_DB = "false"
  $env:ENABLE_REAL_POI_PROVIDER = "false"
  $env:ENABLE_REAL_ROUTING = "false"
  $env:ENABLE_REAL_TICKING = "false"
  $env:ENABLE_REAL_TICKETING = "false"
  $env:ENABLE_REAL_TTS = "false"
  $env:ENABLE_AFFILIATE_LINKS = "false"
  $isDeployedProfile = $Profile -in @("internal", "beta", "staging", "production")
  $env:ALLOW_EXTERNAL_CALLS = if ($isDeployedProfile) { "true" } else { "false" }
  $env:ENABLE_INTEGRATION_TESTS = "false"
  $env:ENABLE_STAGED_INTERNAL_LLM_TESTING = "false"
  $env:ENABLE_INTERNAL_ACCESS_GATE = "false"
  $env:EXTERNAL_CALL_ALLOWED_ENVIRONMENTS = if ($isDeployedProfile) { "internal,beta,staging,production" } else { "production" }
  $env:LLM_ALLOWED_ENVIRONMENTS = "development,production"
  $env:ENABLE_AUTH = if ($isDeployedProfile) { "true" } else { "false" }
  $env:AUTH_PROVIDER = if ($isDeployedProfile) { "oidc" } else { "dev" }
  $env:AUTH_REQUIRED_FOR_USER_FEATURES = if ($isDeployedProfile) { "true" } else { "false" }
  $env:AUTH_ALLOW_DEV_USER_FALLBACK = if ($Profile -in @("development", "test")) { "true" } else { "false" }
  if ($isDeployedProfile) {
    $env:AUTH_JWT_ISSUER = "https://auth.example.test/"
    $env:AUTH_JWT_AUDIENCE = "litinerary-api"
    $env:AUTH_JWT_ALGORITHMS = "RS256"
    $env:AUTH_JWKS_URL = "https://auth.example.test/.well-known/jwks.json"
  }
  $env:CORS_ALLOWED_ORIGINS = "http://127.0.0.1:5173"
  $env:LITINERARY_DATABASE_URL = "sqlite:///../tests/.artifacts/tmp/deployment-readiness-$Profile-$PID.db"
  $env:ENABLE_DURABLE_USAGE_CONTROLS = if ($isDeployedProfile) { "true" } else { "false" }
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

function Get-ScanFiles {
  Push-Location $root
  try {
    $tracked = @(& git ls-files)
    $changed = @(& git status --porcelain | ForEach-Object {
      if ($_.Length -ge 4) { $_.Substring(3).Trim() }
    })
  }
  finally {
    Pop-Location
  }

  $all = @($tracked + $changed) | Where-Object { $_ } | Sort-Object -Unique
  $allowedPrefixes = @("backend/", "frontend/src/", "docs/", "scripts/")
  $allowedRoots = @("README.md", "backend/README.md", ".env.example", ".env.beta.example", ".env.production.example", ".env.test.example", ".env.local.example", ".env.development.local.example")
  $allowedExtensions = @(".md", ".py", ".ps1", ".ts", ".vue", ".js", ".json", ".example", ".txt", ".html", ".css")

  foreach ($relative in $all) {
    $normalized = $relative.Replace("\", "/")
    $extension = [System.IO.Path]::GetExtension($normalized)
    $isAllowedRoot = $allowedRoots -contains $normalized
    $isAllowedPrefix = $false
    foreach ($prefix in $allowedPrefixes) {
      if ($normalized.StartsWith($prefix)) {
        $isAllowedPrefix = $true
        break
      }
    }
    if (($isAllowedRoot -or $isAllowedPrefix) -and ($allowedExtensions -contains $extension -or $isAllowedRoot)) {
      $path = Join-Path $root $relative
      if (Test-Path -LiteralPath $path -PathType Leaf) {
        $path
      }
    }
  }
}

function Test-SecretHygiene {
  Write-Host "== Secret hygiene scan =="
  $patterns = [ordered]@{
    openai_api_key_like = "sk-[A-Za-z0-9_-]{20,}"
    bearer_token = "Bearer\s+[A-Za-z0-9._-]{20,}"
    aws_access_key = "AKIA[A-Z0-9]{16}"
    github_token = "ghp_[A-Za-z0-9]{20,}"
    google_api_key = "AIza[A-Za-z0-9_-]{20,}"
    private_key_block = "-----BEGIN [A-Z ]+PRIVATE KEY-----"
  }
  $findings = @()
  foreach ($file in Get-ScanFiles) {
    foreach ($entry in $patterns.GetEnumerator()) {
      $matches = Select-String -LiteralPath $file -Pattern $entry.Value -AllMatches -ErrorAction SilentlyContinue
      if ($matches) {
        $relative = Resolve-Path -LiteralPath $file -Relative
        $findings += [PSCustomObject]@{ Path = $relative; Category = $entry.Key }
      }
    }
  }
  if ($findings.Count -gt 0) {
    $findings | Sort-Object Path,Category -Unique | Format-Table -AutoSize
    throw "Secret hygiene scan found high-confidence patterns. Values were not printed."
  }
  Write-Host "Secret hygiene scan passed; no high-confidence patterns found."
}

function Test-LocalEnvIgnored {
  Write-Host "== Local env ignore checks =="
  $localFiles = @(".env", ".env.local", ".env.development.local", "frontend/.env.local", "backend/.env")
  Push-Location $root
  try {
    foreach ($file in $localFiles) {
      $tracked = @(& git ls-files -- $file)
      if ($tracked.Count -gt 0) {
        throw "$file is tracked; local env files must remain untracked."
      }
      & git check-ignore -q -- $file
      if ($LASTEXITCODE -ne 0) {
        throw "$file is not ignored by .gitignore."
      }
    }
  }
  finally {
    Pop-Location
  }
  Write-Host "Local env files are ignored and untracked."
}

function Test-EnvironmentTemplates {
  Write-Host "== Environment template placeholder checks =="
  $templateFiles = @(
    ".env.example",
    ".env.beta.example",
    ".env.production.example",
    ".env.test.example",
    ".env.local.example",
    ".env.development.local.example"
  )
  foreach ($relative in $templateFiles) {
    $path = Join-Path $root $relative
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
      throw "Missing environment template: $relative"
    }
    $lineNumber = 0
    foreach ($line in Get-Content -LiteralPath $path) {
      $lineNumber += 1
      $trimmed = $line.Trim()
      if ($trimmed -eq "" -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
        continue
      }
      $name, $value = $trimmed.Split("=", 2)
      if ($name -match "(API_KEY|SECRET|TOKEN|PASSWORD)$" -and -not [string]::IsNullOrWhiteSpace($value)) {
        $clean = $value.Trim().Trim('"').Trim("'")
        $isPlaceholder = $clean.StartsWith("<") -and $clean.EndsWith(">")
        if (-not $isPlaceholder) {
          throw "$relative line $lineNumber contains a non-placeholder value for $name."
        }
      }
    }
  }
  Write-Host "Environment templates use placeholders for secret-bearing fields."
}

function Test-OfflineProfile {
  param([Parameter(Mandatory = $true)][string]$Profile)

  Set-OfflineProfileEnvironment $Profile
  $code = @'
import json
from app.core.config import get_settings
from app.core.readiness import provider_status

settings = get_settings()
providers = provider_status(settings)
deployed = settings.app_env in {"internal", "beta", "staging", "production"}
payload = {
    "app_env": settings.app_env,
    "allow_external_calls": settings.allow_external_calls,
    "enable_real_llm": settings.enable_real_llm,
    "enable_staged_internal_llm_testing": settings.enable_staged_internal_llm_testing,
    "enable_internal_access_gate": settings.enable_internal_access_gate,
    "providers": providers,
    "database": {
        "configured": settings.database_url_configured,
        "dialect": settings.safe_database_dialect(),
        "configurationErrors": settings.database_configuration_validation_errors(),
    },
    "usageControls": {
        "durable": settings.enable_durable_usage_controls,
        "providerDailyRequestCeiling": settings.provider_daily_request_ceiling,
        "retentionDays": settings.usage_counter_retention_days,
    },
}
if deployed and not settings.allow_external_calls:
    raise SystemExit("Managed auth requires external calls in deployed readiness profiles.")
if not deployed and settings.allow_external_calls:
    raise SystemExit("External calls must be disabled in local/test deployment-readiness profiles.")
if settings.enable_real_llm:
    raise SystemExit("Live LLM must be disabled in deployment-readiness default profiles.")
if settings.enable_staged_internal_llm_testing or settings.enable_internal_access_gate:
    raise SystemExit("Staged/internal live LLM gates must remain disabled.")
if deployed:
    if not settings.database_url_configured or settings.database_configuration_validation_errors():
        raise SystemExit("Deployed profile database URL must be explicitly configured.")
    if not settings.enable_durable_usage_controls:
        raise SystemExit("Durable usage controls must be enabled in deployed readiness profiles.")
else:
    if settings.enable_durable_usage_controls:
        raise SystemExit("Durable usage controls must remain disabled in local/test readiness profiles.")
for provider in providers:
    if deployed and provider["providerType"] == "auth":
        if not provider["realEnabled"] or provider["mode"] != "real":
            raise SystemExit("Managed auth provider is not enabled in deployed profile.")
        if not provider["credentialsConfigured"] or not provider["externalCallsAllowed"]:
            raise SystemExit("Managed auth provider is not configured for deployed profile.")
        continue
    if provider["realEnabled"] or provider["externalCallsAllowed"]:
        raise SystemExit(f"Provider {provider['providerType']} is not fail-closed.")
    if provider["mode"] != "mock":
        raise SystemExit(f"Provider {provider['providerType']} is not in mock mode.")
dumped = json.dumps(payload)
for forbidden in ("Authorization", "rawProviderPayload", "raw_provider_payload"):
    if forbidden in dumped:
        raise SystemExit(f"Readiness/provider output leaked {forbidden}.")
print(json.dumps(payload, sort_keys=True))
'@
  Push-Location $backend
  $profileCheckPath = Join-Path $artifactTmp "deployment-readiness-profile-$PID.py"
  try {
    Set-Content -LiteralPath $profileCheckPath -Value $code -Encoding UTF8
    $previousPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = $backend
    Invoke-NativeCommand { & $python $profileCheckPath } "Offline profile validation: $Profile"
  }
  finally {
    $env:PYTHONPATH = $previousPythonPath
    if (Test-Path -LiteralPath $profileCheckPath) {
      Remove-Item -LiteralPath $profileCheckPath -Force
    }
    Pop-Location
  }
}

function Test-PackageScripts {
  Write-Host "== Package script checks =="
  $packagePath = Join-Path $frontend "package.json"
  $package = Get-Content -LiteralPath $packagePath -Raw | ConvertFrom-Json
  foreach ($scriptName in @("test", "typecheck", "build")) {
    if (-not $package.scripts.$scriptName) {
      throw "frontend/package.json is missing script '$scriptName'."
    }
  }
  Write-Host "Frontend package scripts exist: test, typecheck, build."
}

function Set-FrontendCommandEnvironment {
  Clear-DeploymentProviderEnvironment
  Remove-Item -Path "Env:PWD" -ErrorAction SilentlyContinue
  Remove-Item -Path "Env:INIT_CWD" -ErrorAction SilentlyContinue
}

function Test-AlembicAndSeedReadiness {
  Write-Host "== Alembic migration and seed readiness =="
  $dbName = "deployment-readiness-migration-$PID.db"
  $dbPath = Join-Path $artifactTmp $dbName
  if (Test-Path -LiteralPath $dbPath) {
    Remove-Item -LiteralPath $dbPath -Force
  }
  Set-OfflineProfileEnvironment "test"
  $env:LITINERARY_DATABASE_URL = "sqlite:///../tests/.artifacts/tmp/$dbName"
  Push-Location $backend
  try {
    Invoke-NativeCommand { & $python -m alembic heads } "Alembic heads"
    Invoke-NativeCommand { & $python -m alembic upgrade head } "Alembic upgrade on temporary DB"
    Invoke-NativeCommand { & $python -m scripts.seed_database } "Seed temporary DB"
    Invoke-NativeCommand { & $python -m pytest tests\test_database_seed.py tests\test_seed_manager.py --basetemp="..\tests\.artifacts\tmp\pytest-deployment-readiness-seed-$runId" } "Seed validation tests"
  }
  finally {
    Pop-Location
    if (Test-Path -LiteralPath $dbPath) {
      Remove-Item -LiteralPath $dbPath -Force
    }
  }
}

function Test-HealthReadinessServer {
  Write-Host "== Temporary backend health/readiness check =="
  Set-OfflineProfileEnvironment "staging"
  $serverDbName = "deployment-readiness-server-$PID.db"
  $serverDbPath = Join-Path $artifactTmp $serverDbName
  $env:LITINERARY_DATABASE_URL = "sqlite:///../tests/.artifacts/tmp/$serverDbName"
  Push-Location $backend
  $server = $null
  try {
    Invoke-NativeCommand { & $python -m alembic upgrade head } "Temporary server DB Alembic upgrade"
    Invoke-NativeCommand { & $python -m scripts.seed_database } "Temporary server DB seed"
    $server = Start-Process -FilePath $python -ArgumentList @(
      "-m", "uvicorn", "app.main:app",
      "--host", "127.0.0.1",
      "--port", "$Port"
    ) -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 3
    $baseUrl = "http://127.0.0.1:$Port"
    $health = Invoke-RestMethod -Uri "$baseUrl/api/health" -Headers @{ "X-Request-ID" = "req-deployment-readiness" }
    $readiness = Invoke-RestMethod -Uri "$baseUrl/api/readiness"
    if ($health.status -ne "ok") {
      throw "Health endpoint did not return ok."
    }
    if ($readiness.status -ne "ready") {
      throw "Readiness endpoint did not return ready."
    }
    if ($readiness.checks.database.configured -ne $true) {
      throw "Readiness database check did not report explicit configuration."
    }
    if ($readiness.checks.database.connectivity -ne "ok") {
      throw "Readiness database connectivity did not report ok."
    }
    if ($readiness.checks.database.migrations.status -ne "current") {
      throw "Readiness database migrations did not report current."
    }
    if ($readiness.checks.externalCalls.allowed -ne $true) {
      throw "Readiness did not allow managed-auth external calls in staging."
    }
    foreach ($provider in $readiness.checks.providers) {
      if ($provider.providerType -eq "auth") {
        if ($provider.realEnabled -ne $true -or $provider.mode -ne "real") {
          throw "Auth provider is not enabled in staging readiness."
        }
        if ($provider.credentialsConfigured -ne $true -or $provider.externalCallsAllowed -ne $true) {
          throw "Auth provider is not configured for staging readiness."
        }
        continue
      }
      if ($provider.realEnabled -ne $false) {
        throw "Provider $($provider.providerType) is real-enabled in offline readiness."
      }
      if ($provider.externalCallsAllowed -ne $false) {
        throw "Provider $($provider.providerType) allows external calls in offline readiness."
      }
    }
    $readinessText = $readiness | ConvertTo-Json -Depth 20
    if ($readinessText -match "Authorization|rawProviderPayload|raw_provider_payload|sk-[A-Za-z0-9_-]{20,}") {
      throw "Readiness output contains a forbidden secret/raw-payload pattern."
    }
    Write-Host "Health/readiness endpoints passed in offline staging profile."
  }
  finally {
    if ($server -and -not $server.HasExited) {
      Stop-Process -Id $server.Id -Force
      Wait-Process -Id $server.Id -Timeout 10 -ErrorAction SilentlyContinue
    }
    Pop-Location
    if (Test-Path -LiteralPath $serverDbPath) {
      $removed = $false
      for ($attempt = 1; $attempt -le 5; $attempt += 1) {
        try {
          Remove-Item -LiteralPath $serverDbPath -Force
          $removed = $true
          break
        }
        catch {
          Start-Sleep -Milliseconds 500
        }
      }
      if (-not $removed -and (Test-Path -LiteralPath $serverDbPath)) {
        throw "Temporary server database could not be removed: $serverDbPath"
      }
    }
  }
}

Write-Host "Litinerary deployment-readiness check starting."
Write-Host "Mode: $(if ($Full) { 'full' } else { 'default focused' })"
Write-Host "No live providers are enabled by this harness."

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
  throw "Python executable not found at $python"
}

Test-SecretHygiene
Test-LocalEnvIgnored
Test-EnvironmentTemplates
foreach ($profile in @("development", "test", "internal", "staging", "production")) {
  Test-OfflineProfile -Profile $profile
}
Test-AlembicAndSeedReadiness
Test-HealthReadinessServer
Test-PackageScripts

Set-OfflineProfileEnvironment "test"
Push-Location $backend
try {
  if ($Full) {
    Invoke-NativeCommand { & $python -m pytest --basetemp="..\tests\.artifacts\tmp\pytest-deployment-readiness-full-$runId" } "Backend full pytest"
  } else {
    Invoke-NativeCommand {
      & $python -m pytest `
        tests\test_offline_integration_readiness.py `
        tests\test_provider_fail_closed_integration.py `
        tests\test_model_metadata_migrations.py `
        --basetemp="..\tests\.artifacts\tmp\pytest-deployment-readiness-$runId"
    } "Backend focused deployment tests"
  }
}
finally {
  Pop-Location
}

Set-FrontendCommandEnvironment
Push-Location $frontend
try {
  if ($Full) {
    Invoke-NativeCommand { & npm.cmd test } "Frontend full tests"
  } else {
    Invoke-NativeCommand {
      & npm.cmd test -- src/test/frontendApiIntegration.test.ts src/services/apiContract.integration.test.ts
    } "Frontend focused integration tests"
  }

  Invoke-NativeCommand { & npm.cmd run typecheck } "Frontend typecheck"

  if (-not $SkipFrontendBuild) {
    Invoke-NativeCommand { & npm.cmd run build } "Frontend build"
  } else {
    Write-Host "Frontend build skipped by -SkipFrontendBuild."
  }
}
finally {
  Pop-Location
}

Write-Host "Deployment-readiness check passed in offline/mock mode. No deployment was performed."
