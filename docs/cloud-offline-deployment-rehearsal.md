# Cloud Offline Deployment Rehearsal

## Purpose

This runbook defines the next deployment gate after the passing local offline
deployment rehearsal. It rehearses a cloud-hosted deployment posture while all
providers remain mock/offline and all external calls remain disabled.

This runbook does not approve local live deployment, staged internal live LLM
testing, public/beta live generation, production deployment, or any live
non-LLM provider.

## Scope

In scope:

- cloud runtime configuration review
- backend and frontend build artifact preparation
- database migration and seed rehearsal in a non-production cloud environment
- health/readiness validation
- one mock itinerary-generation validation
- log/redaction validation
- rollback/shutdown validation
- sanitized evidence capture

Out of scope:

- live LLM calls
- `/v1/chat/completions`
- live vector DB, POI verification, routing, ticketing, affiliate, TTS, or
  managed auth providers
- public/beta traffic
- production secrets
- production data
- staged internal approval

## Supported Target Placeholders

Replace these placeholders during an approved cloud-offline rehearsal:

- `<cloud-provider>`: hosting provider or platform
- `<cloud-project>`: project/account/subscription
- `<cloud-environment>`: non-production environment name
- `<backend-service>`: backend service/app identifier
- `<frontend-service>`: frontend static/runtime service identifier
- `<database-instance>`: non-production database instance
- `<log-sink>`: log sink or observability workspace
- `<operator>`: person running the rehearsal

Do not store real cloud credentials or secrets in tracked files.

Use `docs/cloud-target-decision.md` for target-selection context. Render has
been selected as the first concrete target for target-specific cloud offline
rehearsal assets. This selection does not approve deployment or cloud resource
creation.

Target-specific Render assets:

- `docs/cloud-offline-deployment-render.md`
- `docs/cloud-offline-env-render.template.md`
- `docs/cloud-offline-checklist-render.md`
- `docs/cloud-offline-rehearsal-record-render.md`

Placeholder assets remain available for future target comparison:

- `docs/cloud-offline-deployment-cloud-target-placeholder.md`
- `docs/cloud-offline-env-cloud-target-placeholder.template.md`
- `docs/cloud-offline-checklist-cloud-target-placeholder.md`
- `docs/cloud-offline-rehearsal-record-cloud-target-placeholder.md`

Do not execute the cloud offline rehearsal on Render until the user separately
approves the Render account/project, non-production environment, database,
access restrictions, rollback method, and operator.

## Prerequisites

- Batch 4 deployment-readiness harness has passed.
- Local offline deployment rehearsal has passed.
- A non-production cloud target is selected using
  `docs/cloud-target-decision.md`.
- Render-specific docs have been reviewed if Render remains the selected target.
- `docs/cloud-target-readiness-checklist.md` is completed for the selected
  target.
- `docs/cloud-offline-env-posture-template.md` is mapped into the selected
  platform's runtime configuration.
- Cloud target can be created or configured without public/beta traffic.
- Cloud database is non-production and disposable or explicitly approved for
  rehearsal.
- Rollback/shutdown path is known before deploying.
- Logs are available to the operator without exposing secrets.
- No real `LLM_API_KEY` is required.

Fail the rehearsal before deployment if the target cannot provide:

- reachable health and readiness endpoints
- durable logs for startup, health/readiness, seed/migration, mock generation,
  and rollback/shutdown
- rollback or shutdown evidence
- runtime config review without printing secret values

## Required Cloud Resources Checklist

- Backend runtime capable of serving the Litinerary API.
- Frontend static hosting or preview runtime.
- Non-production database.
- Network route to backend health/readiness endpoints.
- Log sink for backend startup, request logs, provider diagnostics, and errors.
- Rollback target: prior image/revision, stopped service state, or delete plan.
- Access controls limiting the rehearsal to approved operators.

## Required Environment Variables

Cloud offline rehearsal must use:

```text
APP_ENV=staging
ENABLE_REAL_LLM=false
ALLOW_EXTERNAL_CALLS=false
ENABLE_STAGED_INTERNAL_LLM_TESTING=false
ENABLE_INTERNAL_ACCESS_GATE=false
ENABLE_MOCK_SERVICES=true
LITINERARY_AI_PROVIDER=fake
LLM_PROVIDER=fake
LITINERARY_VECTOR_PROVIDER=fake
VECTOR_DB_PROVIDER=fake
LITINERARY_POI_VERIFICATION_PROVIDER=mock
POI_VERIFICATION_PROVIDER=mock
POI_PROVIDER=mock
ROUTING_PROVIDER=mock
TICKETING_PROVIDER=mock
AFFILIATE_PROVIDER=mock
TTS_PROVIDER=mock
PROVIDER_DAILY_COST_CEILING_USD=0
```

Auth posture:

```text
ENABLE_AUTH=false
AUTH_PROVIDER=dev
AUTH_ALLOW_DEV_USER_FALLBACK=false
```

Use a cloud database URL from secure cloud configuration only. Do not commit it.

## Mock/Offline Provider Posture

Required readiness posture:

- LLM provider: fake/mock/offline
- vector DB: fake/mock/offline
- POI verification: seed/mock/offline
- routing: mock/offline
- ticketing: disabled/mock
- affiliate: disabled/mock
- TTS: disabled/mock
- managed auth: disabled/mock unless separately approved
- external calls: disabled
- staged internal live LLM gate: disabled

Fail the rehearsal if readiness reports any provider with:

- `realEnabled=true`
- `externalCallsAllowed=true`
- mode other than `mock`
- `providerName=openai_compatible`
- any live non-LLM provider name

## Secret Management Expectations

- No `LLM_API_KEY` is required.
- Do not configure OpenAI-compatible, routing, POI, vector, ticketing,
  affiliate, TTS, or managed-auth secrets.
- Cloud database credentials must be stored only in the cloud platform's secret
  or configuration store.
- Logs must not include credentials, Authorization headers, raw provider
  payloads, or full request/response dumps.
- Evidence must report only file/path/category for any secret hygiene issue.

## Build Steps

From a clean repository checkout:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\deployment_readiness_check.ps1
```

Then build frontend artifacts:

```powershell
cd frontend
npm.cmd run build
```

Prepare backend artifact using the selected cloud target's approved packaging
method. Do not add live provider credentials to build artifacts.

## Database, Migration, And Seed Steps

Use a non-production cloud database.

Required sequence:

1. Confirm database target is not production.
2. Apply migrations.
3. Seed bundled data.
4. Validate seed data.
5. Confirm London/Sherlock Holmes/Baker Street seed data exists.
6. Confirm Baker Street has provenance and verification notes.

If migration or seed validation fails, stop and roll back the rehearsal.

## Health And Readiness Validation

After deploying backend in offline/mock posture:

```powershell
Invoke-RestMethod -Uri "https://<backend-service>/api/health"
Invoke-RestMethod -Uri "https://<backend-service>/api/readiness"
```

Expected:

- health returns `status=ok`
- readiness returns `status=ready`
- database status is `ok`
- external calls are disabled
- all providers are mock/offline
- no secret-like values or raw provider payload fields appear

## Mock Itinerary-Generation Validation

Send one mock generation request:

```json
{
  "destinationId": "london",
  "bookId": "sherlock-holmes",
  "durationDays": 1,
  "transportationMode": "walking"
}
```

Expected:

- provider is `mock_ai`
- provider is not `openai_compatible`
- routing provider is `mock_routing`
- Baker Street appears
- no `/v1/chat/completions` call occurs
- no secret-like values or raw provider payload fields appear

Do not paste the full raw response into evidence.

## Log And Redaction Validation

Check the cloud log sink for:

- startup logs
- health/readiness request logs
- seed/migration logs
- mock itinerary-generation request logs
- provider diagnostics and warnings
- shutdown or rollback logs

Pass criteria:

- no API keys
- no Authorization headers
- no raw provider payloads
- no full raw itinerary-generation response dumps
- request IDs are present where expected
- provider warnings are sanitized

If no durable cloud log sink exists, the rehearsal cannot pass this section.

## Rollback And Shutdown Validation

Before the rehearsal, document the rollback target.

After validation:

1. Stop the backend service or roll back to the previous non-production revision.
2. Stop or remove frontend preview if created for the rehearsal.
3. Confirm backend health endpoint is unavailable or points to the intended
   rollback revision.
4. Confirm no public/beta route was enabled.
5. Confirm no live provider configuration remains.
6. Preserve sanitized logs and evidence.

## Evidence Checklist

Use `docs/cloud-offline-deployment-rehearsal-record-template.md`.

Evidence must include:

- date/time
- operator
- cloud target/environment
- commit SHA
- harness result
- backend/frontend build result
- migration result
- seed result
- health result
- readiness result
- provider posture
- mock itinerary-generation result
- logs/redaction result
- rollback result
- secret hygiene result
- pass/fail verdict
- blockers
- next action

## Pass/Fail Criteria

Pass only if:

- deployment-readiness harness passed
- cloud runtime uses offline/mock posture
- health/readiness passed
- all providers remain mock/offline
- seed validation passed
- mock itinerary generation passed
- logs/redaction review passed
- rollback/shutdown validation passed
- evidence contains no secrets or raw provider payloads

Fail if any live provider is enabled, any external call is allowed, any required
log sink is missing, any secret-like value appears, rollback is unproven, or the
cloud target cannot be proven non-production.

## Explicit Non-Approval

Passing this rehearsal does not approve:

- local live deployment
- staged internal live LLM testing
- public/beta live generation
- production deployment
- live vector DB, POI verification, routing, ticketing, affiliate, TTS, or
  managed auth providers

## Current Status

- Selected target: Render.
- Target-specific docs created.
- Cloud offline rehearsal executed: no.
- Cloud deployment executed: no.
- Cloud resources created: no.
- Live providers enabled: no.
- Staged internal testing: `No-go`.
- Public/beta live generation: `No-go`.
