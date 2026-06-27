param(
  [switch]$RunHarness,
  [switch]$RunFrontendBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$docs = Join-Path $root "docs"
$frontend = Join-Path $root "frontend"

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

function Test-RequiredFile {
  param([Parameter(Mandatory = $true)][string]$RelativePath)

  $path = Join-Path $root $RelativePath
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
    throw "Missing required file: $RelativePath"
  }
  Write-Host "Found $RelativePath"
}

function Test-TemplateContains {
  param(
    [Parameter(Mandatory = $true)][string]$TemplateText,
    [Parameter(Mandatory = $true)][string]$Expected
  )

  if ($TemplateText -notmatch [regex]::Escape($Expected)) {
    throw "Render env template is missing required value: $Expected"
  }
}

function Test-NoHighConfidenceSecrets {
  param([Parameter(Mandatory = $true)][string[]]$RelativePaths)

  Write-Host "== Render asset secret-pattern scan =="
  $patterns = [ordered]@{
    openai_api_key_like = "sk-[A-Za-z0-9_-]{20,}"
    bearer_token = "Bearer\s+[A-Za-z0-9._-]{20,}"
    aws_access_key = "AKIA[A-Z0-9]{16}"
    github_token = "ghp_[A-Za-z0-9]{20,}"
    google_api_key = "AIza[A-Za-z0-9_-]{20,}"
    private_key_block = "-----BEGIN [A-Z ]+PRIVATE KEY-----"
  }

  $findings = @()
  foreach ($relative in $RelativePaths) {
    $path = Join-Path $root $relative
    foreach ($entry in $patterns.GetEnumerator()) {
      $matches = Select-String -LiteralPath $path -Pattern $entry.Value -AllMatches -ErrorAction SilentlyContinue
      if ($matches) {
        $findings += [PSCustomObject]@{ Path = $relative; Category = $entry.Key }
      }
    }
  }

  if ($findings.Count -gt 0) {
    $findings | Sort-Object Path,Category -Unique | Format-Table -AutoSize
    throw "High-confidence secret patterns found. Values were not printed."
  }

  Write-Host "No high-confidence secret patterns found in Render assets."
}

function Test-ForbiddenLiveAssignments {
  param([Parameter(Mandatory = $true)][string]$TemplateText)

  Write-Host "== Render env live-posture guard scan =="
  $activeTemplateText = ($TemplateText -split "## Forbidden For This Rehearsal")[0]
  $forbiddenAssignments = @(
    "ENABLE_REAL_LLM=true",
    "ALLOW_EXTERNAL_CALLS=true",
    "ENABLE_STAGED_INTERNAL_LLM_TESTING=true",
    "ENABLE_INTERNAL_ACCESS_GATE=true",
    "LLM_PROVIDER=openai_compatible",
    "LITINERARY_AI_PROVIDER=openai_compatible",
    "POI_PROVIDER=google_places",
    "ROUTING_PROVIDER=openrouteservice",
    "AUTH_PROVIDER=oidc"
  )

  foreach ($assignment in $forbiddenAssignments) {
    if ($activeTemplateText -match "(?m)^\s*$([regex]::Escape($assignment))\s*$") {
      throw "Render env template contains forbidden live assignment: $assignment"
    }
  }

  $credentialAssignments = @(
    "LLM_API_KEY",
    "OPENAI_API_KEY",
    "VECTOR_DB_API_KEY",
    "QDRANT_API_KEY",
    "POI_PROVIDER_API_KEY",
    "GOOGLE_PLACES_API_KEY",
    "POI_VERIFICATION_API_KEY",
    "ROUTING_API_KEY",
    "OPENROUTESERVICE_API_KEY",
    "TICKETING_API_KEY",
    "AFFILIATE_API_KEY",
    "TTS_API_KEY",
    "TEXT_TO_SPEECH_API_KEY"
  )

  foreach ($name in $credentialAssignments) {
    $pattern = "(?m)^\s*$([regex]::Escape($name))\s*=\s*(?!<)[^\s#]+"
    if ($activeTemplateText -match $pattern) {
      throw "Render env template contains a non-placeholder credential assignment for $name."
    }
  }

  Write-Host "Render env template contains no active live-provider assignments."
}

Write-Host "Litinerary Render cloud-offline preflight starting."
Write-Host "This script does not contact Render or any cloud provider."

$requiredFiles = @(
  "docs/cloud-offline-deployment-render.md",
  "docs/cloud-offline-env-render.template.md",
  "docs/cloud-offline-checklist-render.md",
  "docs/cloud-offline-rehearsal-record-render.md"
)

foreach ($relative in $requiredFiles) {
  Test-RequiredFile -RelativePath $relative
}

$templatePath = Join-Path $docs "cloud-offline-env-render.template.md"
$templateText = Get-Content -LiteralPath $templatePath -Raw

foreach ($required in @(
  "APP_ENV=<non-production-offline-env>",
  "ENABLE_REAL_LLM=false",
  "ALLOW_EXTERNAL_CALLS=false",
  "ENABLE_STAGED_INTERNAL_LLM_TESTING=false",
  "LITINERARY_AI_PROVIDER=fake",
  "LLM_PROVIDER=fake",
  "LITINERARY_VECTOR_PROVIDER=fake",
  "VECTOR_DB_PROVIDER=fake",
  "POI_VERIFICATION_PROVIDER=mock",
  "ROUTING_PROVIDER=mock",
  "PROVIDER_DAILY_COST_CEILING_USD=0",
  "LITINERARY_DATABASE_URL=<render-postgres-internal-url-config-reference-only>",
  "VITE_API_BASE_URL=<render-backend-preview-url-placeholder>"
)) {
  Test-TemplateContains -TemplateText $templateText -Expected $required
}

Test-ForbiddenLiveAssignments -TemplateText $templateText
Test-NoHighConfidenceSecrets -RelativePaths $requiredFiles

if ($RunHarness) {
  $harnessPath = Join-Path $root "scripts\deployment_readiness_check.ps1"
  Invoke-NativeCommand {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $harnessPath -SkipFrontendBuild
  } "Local deployment-readiness harness"
} else {
  Write-Host "Local deployment-readiness harness skipped. Use -RunHarness to include it."
}

if ($RunFrontendBuild) {
  Push-Location $frontend
  try {
    Invoke-NativeCommand { & npm.cmd run build } "Frontend build"
  }
  finally {
    Pop-Location
  }
} else {
  Write-Host "Frontend build skipped. Use -RunFrontendBuild to include it."
}

Write-Host "Render cloud-offline preflight passed. No deployment was performed."
