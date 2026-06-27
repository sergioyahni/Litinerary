# Live LLM Smoke-Test Runbook

## Purpose

This runbook verifies that Litinerary can make exactly one controlled, non-production call through the existing OpenAI-compatible LLM adapter while preserving deterministic mock/demo behavior by default.

The smoke test exercises the backend orchestration path for `POST /api/itinerary/generate`. It does not approve public, beta, or production user-facing live LLM itinerary generation.

## Scope

In scope:

- One local backend process.
- One readiness check in mock mode.
- One readiness check with live LLM gates enabled.
- One narrow itinerary-generation request using seeded MVP data.
- One reset back to mock/offline mode.

Out of scope:

- Public or beta traffic.
- New frontend product surface.
- Vector DB, POI, routing, ticketing, affiliate, TTS, or managed-auth live-provider testing.
- Storing, printing, or committing credentials.

## Non-Production Warning

Run this only in `APP_ENV=development` or another explicitly approved non-production environment. Do not use this runbook for public/beta user-facing traffic.

## Prerequisites

- Backend and frontend standard checks pass.
- A non-production `LLM_API_KEY` is already available from local environment or approved secret storage.
- `LLM_MODEL_NAME` is selected for the provider.
- The selected model supports OpenAI-compatible Chat Completions with JSON object
  response format. Models/providers that require a different endpoint shape, such
  as a Responses API endpoint, are out of scope for this smoke runbook.
- The selected `LLM_MODEL_NAME` is confirmed in the provider dashboard or provider
  documentation as an available Chat Completions-compatible model ID. Do not infer
  validity from a guessed model name.
- No real provider credentials are present for vector DB, POI, routing, ticketing, affiliate, TTS, or managed auth unless separately approved.
- The operator can start and stop a local FastAPI process.
- Optional: copy `.env.development.local.example` to `.env.development.local` as a local-only checklist. `.env.development.local` is ignored by Git. The preflight script and optional backend startup helper load this file when present. `.env.local` is still supported as a fallback.

Verify local secret files are ignored before adding any real value:

```powershell
git check-ignore -v .env.local
git check-ignore -v .env.development.local
```

Both commands should report a `.gitignore` rule. Do not proceed if a local secret file is not ignored.

## Required Live LLM Gates

Set these in the shell that starts the backend:

```powershell
$env:APP_ENV="development"
$env:ENABLE_REAL_LLM="true"
$env:ALLOW_EXTERNAL_CALLS="true"
$env:EXTERNAL_CALL_ALLOWED_ENVIRONMENTS="development"
$env:LITINERARY_AI_PROVIDER="openai_compatible"
$env:LLM_PROVIDER="openai_compatible"
$env:LLM_API_KEY="<from-approved-secret-storage>"
$env:LLM_MODEL_NAME="<model-name>"
$env:LLM_ALLOWED_ENVIRONMENTS="development"
```

To avoid printing secrets on Windows PowerShell, set `LLM_API_KEY` only in the current session from approved secret storage or by pasting directly into the assignment prompt provided by that storage workflow. Do not run `Write-Host $env:LLM_API_KEY`, do not place the key in command transcripts, and do not save it in tracked files. If you use an ignored local file such as `.env.local`, verify it is ignored first and remove it when the smoke window is finished.

Confirm only boolean secret presence:

```powershell
if ([string]::IsNullOrWhiteSpace($env:LLM_API_KEY)) { "LLM_API_KEY_PRESENT=false" } else { "LLM_API_KEY_PRESENT=true" }
if ([string]::IsNullOrWhiteSpace($env:LLM_MODEL_NAME)) { "LLM_MODEL_NAME_PRESENT=false" } else { "LLM_MODEL_NAME_PRESENT=true" }
```

Optional non-secret settings:

```powershell
$env:LLM_BASE_URL="https://api.openai.com/v1"
$env:LLM_TIMEOUT_SECONDS="20"
$env:LLM_MAX_TOKENS="1200"
$env:LLM_OUTPUT_TOKEN_PARAMETER="max_tokens"
$env:LLM_MAX_RETRIES="0"
$env:LLM_MAX_LIVE_CALLS_PER_REQUEST="4"
$env:LLM_DAILY_LIVE_REQUEST_CEILING="4"
$env:LLM_LATENCY_ALERT_THRESHOLD_MS="5000"
$env:LLM_ERROR_RATE_ALERT_THRESHOLD_PERCENT="10"
$env:ITINERARY_GENERATION_MAX_DAYS="7"
```

## Providers That Must Remain Disabled

```powershell
$env:ENABLE_REAL_VECTOR_DB="false"
$env:ENABLE_REAL_POI_PROVIDER="false"
$env:ENABLE_REAL_ROUTING="false"
$env:ENABLE_REAL_TICKETING="false"
$env:ENABLE_AFFILIATE_LINKS="false"
$env:ENABLE_REAL_TTS="false"
$env:ENABLE_AUTH="false"
$env:AUTH_PROVIDER="dev"
```

Mock/local providers should remain selected:

```powershell
$env:LITINERARY_VECTOR_PROVIDER="fake"
$env:VECTOR_DB_PROVIDER="fake"
$env:LITINERARY_POI_VERIFICATION_PROVIDER="mock"
$env:POI_PROVIDER="mock"
$env:ROUTING_PROVIDER="mock"
$env:TICKETING_PROVIDER="mock"
$env:AFFILIATE_PROVIDER="mock"
$env:TTS_PROVIDER="mock"
```

## Pre-Smoke Validation

From the repository root:

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest
cd ..\frontend
npm.cmd test
npm.cmd run typecheck
npm.cmd run build
cd ..
```

Start the backend in default mock mode:

```powershell
cd backend
$env:APP_ENV="development"
$env:ENABLE_REAL_LLM="false"
$env:ALLOW_EXTERNAL_CALLS="false"
$env:LITINERARY_AI_PROVIDER="fake"
$env:LLM_PROVIDER="fake"
..\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

In another shell, confirm health and readiness:

```powershell
$readiness = Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/readiness"
$readiness.status
$readiness.checks.externalCalls.allowed
$readiness.checks.providers | Select-Object providerType,providerName,mode,realEnabled,externalCallsAllowed,requiredConfigPresent,environmentAllowed
```

Expected mock readiness:

- `status` is `ready`.
- `externalCalls.allowed` is `False`.
- LLM provider mode is `mock`.
- All non-LLM live providers have `realEnabled=False`.
- No secret values appear.

Stop the mock backend before starting the live-gated backend.

Optional local preflight, with no network call and no secret output:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\live_llm_smoke_preflight.ps1
```

The preflight loads the first available source in this order:

1. An explicit `-EnvFile` argument.
2. `.env.development.local`.
3. `.env.local`.
4. Current process environment only.

It reports the loaded file name and boolean credential presence only; it never prints `LLM_API_KEY`.

To require every live smoke gate before continuing:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\live_llm_smoke_preflight.ps1 -RequireLiveReady
```

Network preflight, with no Chat Completions call and no API key sent:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\live_llm_network_preflight.ps1
```

The network preflight checks DNS, TCP 443, HTTPS reachability, and backend Python
HTTPS reachability for the configured provider host. It reports proxy and
certificate-related environment presence as booleans only; it must not print
proxy values, API keys, prompts, or provider payloads. Do not run a live smoke
request after `provider_reached=false` or `failure_category=url_error` until
this network preflight passes from the same local environment.

## Live-Gated Startup

Set the required live LLM gates and disabled-provider gates in the backend shell, then start. If using `.env.development.local`, prefer the helper so the backend process inherits the same local env source that preflight checked:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\live_llm_smoke_backend.ps1
```

Or start manually from a shell where the same environment variables are already set:

```powershell
cd backend
..\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Confirm readiness before making the request:

```powershell
$readiness = Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/readiness"
$llm = $readiness.checks.providers | Where-Object providerType -eq "llm"
$others = $readiness.checks.providers | Where-Object providerType -ne "llm"
$llm | Select-Object providerType,providerName,mode,realEnabled,credentialsConfigured,requiredConfigPresent,externalCallsAllowed,environmentAllowed
$others | Select-Object providerType,providerName,mode,realEnabled,externalCallsAllowed
```

Expected live-gated LLM readiness:

- LLM `providerName` is `openai_compatible`.
- LLM `realEnabled=True`.
- LLM `credentialsConfigured=True`.
- LLM `requiredConfigPresent=True`.
- LLM `externalCallsAllowed=True`.
- LLM `environmentAllowed=True`.
- Other provider rows remain `realEnabled=False`.

## One Narrow Itinerary Request

Use a seeded combination that does not already have a public repository match, so the generation path reaches the LLM adapter. The current MVP seed data does not include Rome, so this smoke test uses London and Sherlock Holmes.

The approved POI for this scenario is `baker-street`. It must have
`verificationNotes` or `provenanceMetadata` before any live LLM call. The bundled
seed data includes this grounding metadata; if a local development database was
seeded before that metadata existed, reset or reload the local development seed
data before retrying the smoke test.

```powershell
$body = @{
  destinationId = "london"
  bookId = "sherlock-holmes"
  durationDays = 1
  transportationMode = "walking"
} | ConvertTo-Json

$response = Invoke-RestMethod `
  -Uri "http://127.0.0.1:8765/api/itinerary/generate" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body

$response | Select-Object matchedExisting,message
$response.itinerary | Select-Object id,title,destinationId,bookId,durationDays,transportationMode,providerName,providerType,generatedByService
$response.itinerary.days | Select-Object dayNumber,title,estimatedDurationHours,estimatedDistanceKm
```

Make exactly one request. Do not include personal data or secret values in the request.

## Expected Successful Result Shape

Expected response fields:

- `matchedExisting=false`.
- `itinerary.destinationId="london"`.
- `itinerary.bookId="sherlock-holmes"`.
- `itinerary.durationDays=1`.
- `itinerary.transportationMode="walking"`.
- `itinerary.providerName="openai_compatible"`.
- `itinerary.providerType="llm"`.
- `itinerary.generatedByService="openai_compatible"`.
- At least one day and one stop.
- Mock routing metadata may be present because live routing remains disabled.

## Expected Logs Or Observations

Expected observations:

- API request start/end logs include request IDs and status codes.
- Provider failure logs, if any, use safe provider-neutral error codes.
- Logs do not contain `LLM_API_KEY`, bearer tokens, raw provider credentials, or full copyrighted text.
- Provider payloads are not printed by this runbook.

## Cleanup And Reset

Stop the live-gated backend. In the shell/session used for the smoke test:

```powershell
$env:ENABLE_REAL_LLM="false"
$env:ALLOW_EXTERNAL_CALLS="false"
$env:ENABLE_STAGED_INTERNAL_LLM_TESTING="false"
$env:ENABLE_INTERNAL_ACCESS_GATE="false"
$env:LITINERARY_AI_PROVIDER="fake"
$env:LLM_PROVIDER="fake"
Remove-Item Env:\LLM_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:\LLM_MODEL_NAME -ErrorAction SilentlyContinue
```

Start the backend again in mock mode and check readiness:

```powershell
cd backend
..\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Expected reset readiness:

- `externalCalls.allowed=False`.
- LLM mode is `mock`.
- LLM `realEnabled=False`.
- All other providers remain `realEnabled=False`.

## Failure Modes And Safe Responses

- Missing `LLM_API_KEY`: do not run live smoke; obtain credentials through approved secret storage only.
- Missing `LLM_MODEL_NAME`: fail closed with provider configuration error.
- HTTP 502 with `invalid_provider_response`: treat as an inconclusive provider-boundary
  failure. Inspect only sanitized diagnostics such as endpoint kind, HTTP status,
  provider error code/type, and safe request ID; do not print raw provider bodies
  or prompts. Confirm the selected model supports Chat Completions JSON mode before
  any retry. For GPT-5-family Chat Completions models, set
  `LLM_OUTPUT_TOKEN_PARAMETER=max_completion_tokens`; older compatible models may
  continue using the default `max_tokens`.
- In local development smoke mode, sanitized provider-boundary diagnostics are
  returned in `detail.diagnostics` and in the
  `X-Litinerary-Provider-Diagnostics` response header. Expected fields may include
  `provider_reached`, `provider_http_status`, `provider_error_type`,
  `provider_error_code`, `failure_category`, `endpoint_kind`, `endpoint_host`,
  `endpoint_path`, `url_error_reason_type`, `url_error_reason_category`,
  `timeout_seconds`, proxy-environment presence booleans, and certificate
  environment presence booleans. These fields must not contain secrets, prompts,
  raw request payloads, proxy values, or raw provider bodies.
- `provider_reached=false` with `failure_category=url_error`: the backend did not
  receive an HTTP response from the provider. Run the network preflight before
  another live attempt and check DNS, TCP 443, TLS/certificate trust, firewall or
  proxy requirements, IPv4/IPv6 behavior, local security software, backend Python
  environment inheritance, and timeout settings. Use
  `docs/live-llm-network-troubleshooting.md` for the focused Windows/proxy/TLS
  troubleshooting steps and retry criteria.
- `ALLOW_EXTERNAL_CALLS=false`: fail closed before transport.
- `APP_ENV` absent from either allow-list: fail closed before transport.
- `APP_ENV=test` without explicit integration gates: fail closed before transport.
- Provider HTTP error or invalid response: return safe provider-neutral error; do not print raw provider body.
- Grounding/provenance rejection: treat as a safety success; no live call should be made after unsafe input is detected.
- `POI 'baker-street' is missing provenance or candidate source notes`: the
  local database likely contains stale seed data for the London/Sherlock smoke
  scenario. Do not weaken the grounding gate. In a local development backend
  only, reset bundled seed data and validate it before retrying:

  ```powershell
  Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/admin/seed/reset" -Method Post
  Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/admin/seed/validate"
  ```

  The reset endpoint requires local admin/development routes and must not be used
  against beta or production data.
- Any non-LLM provider reports `realEnabled=True`: stop and reset before making the request.
- If any real API key ever appears in a tracked file, example template, docs,
  logs, terminal transcript, or shared evidence, revoke or rotate it outside the
  repository before any further live attempt.

## Evidence Checklist

Capture only sanitized evidence:

- Use `docs/live-llm-smoke-test-evidence-template.md` for each controlled smoke test.
- Date/time and operator.
- Git commit or working tree identifier.
- Backend test result summary.
- Frontend test/typecheck/build result summary.
- Mock readiness summary.
- Live-gated readiness summary with secrets redacted.
- One request summary: destination/book/duration/transport only.
- Sanitized result summary: itinerary ID/title/provider/day count/stop count.
- Reset readiness summary.
- Confirmation that no other live providers were enabled.
- Confirmation that no secrets were printed or committed.

Rollback and operational controls are documented in `docs/live-llm-operational-controls.md`.

## Go/No-Go Criteria

Go to repeat controlled live LLM smoke tests when:

- All standard checks pass.
- Readiness confirms only LLM is live-gated.
- Exactly one request succeeds or fails safely.
- Mock mode is restored afterward.

No-go to repeat smoke tests when:

- Any non-LLM live provider is enabled unexpectedly.
- Readiness exposes secret values.
- The adapter calls the provider without all gates.
- Reset to mock mode cannot be confirmed.

No-go for staged internal testing until:

- Multiple controlled smoke tests pass with sanitized evidence.
- Cost/rate limits are reviewed for the selected non-production environment.
- Runbooks for failure handling and provider outage are rehearsed.

No-go for public/beta user-facing live LLM generation until:

- Production auth and ownership checks are fully staged.
- Durable rate and cost controls are in place.
- Provider observability and alerting are operational.
- POI/routing quality validation is staged.
- A later readiness review explicitly approves the rollout.
