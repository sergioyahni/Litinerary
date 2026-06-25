# Cloud Offline Deployment Rehearsal: `{{CLOUD_TARGET}}`

## Status

- Selected target: `{{CLOUD_TARGET}}`
- Target slug: `cloud-target-placeholder`
- Target specificity: unresolved placeholder
- Cloud deployment executed: no
- Provider posture: mock/offline only
- Local live deployment: blocked
- Staged internal testing: `No-go`
- Public/beta live generation: `No-go`

Replace `{{CLOUD_TARGET}}` with the approved non-production platform before
executing this runbook. Do not deploy while the target remains a placeholder.

## Target Assumptions

This runbook assumes the target is a simple non-production PaaS/app platform or
static frontend plus managed backend/API platform with:

- secure runtime configuration
- built-in logs
- revision rollback or service shutdown
- non-production database support
- private or restricted preview access
- reachable backend health/readiness endpoints

If the selected target cannot provide health/readiness evidence, durable log
evidence, and rollback evidence, the cloud offline rehearsal fails before any
deployment.

## Service Layout Recommendation

- Backend: one API service running `app.main:app`.
- Frontend: static build artifact served by target static hosting, CDN preview,
  or app platform static service.
- Database: disposable or resettable non-production managed database.
- Logs: target-provided service logs plus database/migration logs.

Keep backend and frontend preview routes restricted to approved operators.

## Backend Deployment Shape

Recommended backend runtime:

- Python app service or container runtime.
- Working directory: `backend`.
- Start command:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port <platform-port>
```

Adapt the Python executable path to the platform image. Do not add live provider
credentials to the backend image, artifact, or runtime config.

## Frontend Deployment Shape

Build:

```powershell
cd frontend
npm.cmd run build
```

Serve the generated `frontend/dist` artifact with the selected target's static
hosting or preview runtime. Configure the frontend backend API base URL only to
the approved non-production backend URL.

## Database Choice For Non-Production

Use a non-production managed database or safe disposable test database. The
database must support:

- applying Alembic migrations
- bundled seed loading
- seed validation
- reset/rollback or deletion after rehearsal

Never point the cloud offline rehearsal at production data.

## Required Runtime Versions

Record the approved target versions before execution:

- Python: `<python-version>`
- Node.js: `<node-version>`
- Database: `<database-engine-version>`
- Runtime image: `<runtime-image-or-stack>`

## Build Commands

Preflight from repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\deployment_readiness_check.ps1
```

Frontend build:

```powershell
cd frontend
npm.cmd run build
```

Backend artifact preparation depends on the selected target and must remain
mock-only.

## Start Commands

Backend:

```text
python -m uvicorn app.main:app --host 0.0.0.0 --port <platform-port>
```

Frontend:

```text
serve frontend/dist using <target-static-hosting-method>
```

## Health And Readiness URLs

Replace placeholders after target approval:

- Backend health: `https://<backend-service>/api/health`
- Backend readiness: `https://<backend-service>/api/readiness`
- Frontend preview: `https://<frontend-service>/`

## Migration And Seed Approach

Required sequence:

1. Confirm database target is non-production.
2. Apply migrations:

```text
python -m alembic upgrade head
```

3. Seed bundled data:

```text
python -m scripts.seed_database
```

4. Validate seed data via:

```text
GET /api/admin/seed/validate
```

Expected seed content includes London, Sherlock Holmes, and Baker Street with
provenance and verification notes.

## Required Environment Variables

Use `docs/cloud-offline-env-cloud-target-placeholder.template.md` as the target
posture template. Required values include:

```text
ENABLE_REAL_LLM=false
ALLOW_EXTERNAL_CALLS=false
ENABLE_STAGED_INTERNAL_LLM_TESTING=false
LITINERARY_AI_PROVIDER=fake
LLM_PROVIDER=fake
ROUTING_PROVIDER=mock
PROVIDER_DAILY_COST_CEILING_USD=0
```

## Forbidden Env Vars And Values

Forbidden for cloud offline rehearsal:

- `ENABLE_REAL_LLM=true`
- `ALLOW_EXTERNAL_CALLS=true`
- `ENABLE_STAGED_INTERNAL_LLM_TESTING=true`
- `LLM_PROVIDER=openai_compatible`
- `LITINERARY_AI_PROVIDER=openai_compatible`
- any `LLM_API_KEY`
- any real vector, POI, routing, ticketing, affiliate, TTS, or managed auth
  credential

If any live provider credential is present, the rehearsal fails.

## Provider Posture Checks

Readiness must show:

- all providers `mode=mock`
- all providers `realEnabled=false`
- all providers `externalCallsAllowed=false`
- LLM provider is fake/mock, not `openai_compatible`
- routing provider is mock

## Log And Redaction Checks

Review target logs for:

- startup
- health/readiness
- migrations/seed
- mock itinerary generation
- rollback/shutdown

Fail if logs contain:

- API keys
- Authorization headers
- raw provider payloads
- full raw response dumps
- live provider endpoint URLs such as `/v1/chat/completions`

## Rollback And Revision Restore Checks

Before execution, document:

- previous revision/image
- rollback command
- shutdown command
- database reset/delete method
- expected post-rollback health behavior

After execution, verify no public/beta route or live provider config remains.

## Evidence Capture Checklist

Complete `docs/cloud-offline-rehearsal-record-cloud-target-placeholder.md` after
execution with:

- target and environment
- commit SHA
- preflight result
- build result
- migration/seed result
- health/readiness result
- provider posture
- mock itinerary result
- logs/redaction result
- rollback result
- pass/fail verdict

Do not include secrets, raw provider payloads, Authorization headers, or full
raw response dumps.

## Explicit Mock-Only Statement

This runbook is mock-only/offline. It does not approve local live deployment,
staged internal live LLM testing, public/beta live generation, or any live
external provider.

