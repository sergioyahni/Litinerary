param(
  [Parameter(Position = 1)]
  [string]$EnvFile,
  [Parameter(Position = 0)]
  [switch]$RequireLiveReady
)

$ErrorActionPreference = "Stop"

function Is-PlaceholderValue {
  param([string]$Value)
  if ([string]::IsNullOrWhiteSpace($Value)) { return $true }
  $trimmed = $Value.Trim()
  return $trimmed.StartsWith("<") -and $trimmed.EndsWith(">")
}

function Set-EnvFromFile {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }

  Get-Content -LiteralPath $Path | ForEach-Object {
    $line = $_.Trim()
    if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith("#")) { return }
    $separatorIndex = $line.IndexOf("=")
    if ($separatorIndex -le 0) { return }

    $name = $line.Substring(0, $separatorIndex).Trim()
    if ($name -notmatch "^[A-Za-z_][A-Za-z0-9_]*$") { return }

    $value = $line.Substring($separatorIndex + 1).Trim()
    if (
      ($value.StartsWith('"') -and $value.EndsWith('"')) -or
      ($value.StartsWith("'") -and $value.EndsWith("'"))
    ) {
      $value = $value.Substring(1, $value.Length - 2)
    }

    $existing = [Environment]::GetEnvironmentVariable($name)
    if ([string]::IsNullOrWhiteSpace($existing)) {
      [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
  }

  return $true
}

function Read-BoolEnv {
  param(
    [string]$Name,
    [bool]$Default = $false
  )
  $value = [Environment]::GetEnvironmentVariable($Name)
  if ((Is-PlaceholderValue $value)) { return $Default }
  return $value.Trim().ToLowerInvariant() -in @("1", "true", "yes", "on")
}

function Read-ListEnv {
  param([string]$Name)
  $value = [Environment]::GetEnvironmentVariable($Name)
  if ((Is-PlaceholderValue $value)) { return @() }
  return @($value.Split(",") | ForEach-Object { $_.Trim().ToLowerInvariant() } | Where-Object { $_ })
}

function Present {
  param([string]$Name)
  $value = [Environment]::GetEnvironmentVariable($Name)
  return -not (Is-PlaceholderValue $value)
}

$repoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$developmentEnvPath = Join-Path $repoRoot ".env.development.local"
$localEnvPath = Join-Path $repoRoot ".env.local"
$developmentEnvExists = Test-Path -LiteralPath $developmentEnvPath -PathType Leaf
$localEnvExists = Test-Path -LiteralPath $localEnvPath -PathType Leaf
$loadedEnvSource = "<none>"

if (-not [string]::IsNullOrWhiteSpace($EnvFile)) {
  if ($EnvFile.Trim().StartsWith("-")) {
    throw "EnvFile must be a path. Did you mean to pass $EnvFile as a named switch?"
  }
  $resolvedEnvFile = Resolve-Path -LiteralPath $EnvFile -ErrorAction Stop
  if (Set-EnvFromFile $resolvedEnvFile.Path) {
    $loadedEnvSource = Split-Path -Leaf $resolvedEnvFile.Path
  }
} elseif ($developmentEnvExists) {
  if (Set-EnvFromFile $developmentEnvPath) {
    $loadedEnvSource = ".env.development.local"
  }
} elseif ($localEnvExists) {
  if (Set-EnvFromFile $localEnvPath) {
    $loadedEnvSource = ".env.local"
  }
}

$rawAppEnv = [Environment]::GetEnvironmentVariable("APP_ENV")
if ([string]::IsNullOrWhiteSpace($rawAppEnv)) { $rawAppEnv = "development" }
$appEnv = $rawAppEnv.Trim().ToLowerInvariant()
$blockedEnvironments = @("production", "beta", "staging")
$enableRealLlm = Read-BoolEnv "ENABLE_REAL_LLM"
$allowExternalCalls = Read-BoolEnv "ALLOW_EXTERNAL_CALLS"
$aiProvider = [Environment]::GetEnvironmentVariable("LITINERARY_AI_PROVIDER")
$llmProvider = [Environment]::GetEnvironmentVariable("LLM_PROVIDER")
$llmApiKeyPresent = Present "LLM_API_KEY"
$llmModelNamePresent = Present "LLM_MODEL_NAME"
$globalAllowed = Read-ListEnv "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS"
$llmAllowed = Read-ListEnv "LLM_ALLOWED_ENVIRONMENTS"

if ([string]::IsNullOrWhiteSpace($aiProvider)) { $aiProvider = $llmProvider }
if ([string]::IsNullOrWhiteSpace($llmProvider)) { $llmProvider = $aiProvider }

$otherLiveFlags = @(
  "ENABLE_REAL_VECTOR_DB",
  "ENABLE_REAL_POI_PROVIDER",
  "ENABLE_REAL_ROUTING",
  "ENABLE_REAL_TICKETING",
  "ENABLE_AFFILIATE_LINKS",
  "ENABLE_REAL_TTS"
)
$enabledOtherLiveFlags = @($otherLiveFlags | Where-Object { Read-BoolEnv $_ })

$isProductionLike = $blockedEnvironments -contains $appEnv
$providerSelected = ($aiProvider -eq "openai_compatible") -or ($llmProvider -eq "openai_compatible")
$globalEnvironmentAllowed = $globalAllowed -contains $appEnv
$llmEnvironmentAllowed = $llmAllowed -contains $appEnv
$otherProvidersDisabled = $enabledOtherLiveFlags.Count -eq 0
$rawAuthProvider = [Environment]::GetEnvironmentVariable("AUTH_PROVIDER")
if ([string]::IsNullOrWhiteSpace($rawAuthProvider)) { $rawAuthProvider = "dev" }
$managedAuthLiveDisabled = -not ((Read-BoolEnv "ENABLE_AUTH") -and ($rawAuthProvider.Trim().ToLowerInvariant() -ne "dev"))

$checks = [ordered]@{
  envDevelopmentLocalExists = $developmentEnvExists
  envLocalExists = $localEnvExists
  loadedEnvSource = $loadedEnvSource
  appEnv = $appEnv
  productionLikeEnvironment = $isProductionLike
  enableRealLlm = $enableRealLlm
  allowExternalCalls = $allowExternalCalls
  aiProvider = if ([string]::IsNullOrWhiteSpace($aiProvider)) { "<unset>" } else { $aiProvider }
  llmProvider = if ([string]::IsNullOrWhiteSpace($llmProvider)) { "<unset>" } else { $llmProvider }
  llmApiKeyPresent = $llmApiKeyPresent
  llmModelNamePresent = $llmModelNamePresent
  externalCallEnvironmentAllowed = $globalEnvironmentAllowed
  llmEnvironmentAllowed = $llmEnvironmentAllowed
  otherLiveProvidersDisabled = $otherProvidersDisabled
  managedAuthLiveDisabled = $managedAuthLiveDisabled
}

$checks.GetEnumerator() | ForEach-Object {
  Write-Output "$($_.Key)=$($_.Value)"
}

if ($enabledOtherLiveFlags.Count -gt 0) {
  Write-Output ("enabledOtherLiveFlags=" + ($enabledOtherLiveFlags -join ","))
}

$ready = (
  -not $isProductionLike -and
  $enableRealLlm -and
  $allowExternalCalls -and
  $providerSelected -and
  $llmApiKeyPresent -and
  $llmModelNamePresent -and
  $globalEnvironmentAllowed -and
  $llmEnvironmentAllowed -and
  $otherProvidersDisabled -and
  $managedAuthLiveDisabled
)

Write-Output "liveLlmSmokeReady=$ready"

if ($RequireLiveReady -and -not $ready) {
  exit 1
}
