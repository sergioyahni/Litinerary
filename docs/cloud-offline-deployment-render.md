# Cloud Offline Deployment Rehearsal: Render

## Status

- Selected target: Render
- Target specificity: target-specific rehearsal assets prepared
- Cloud deployment executed: no
- Cloud resources created: no
- Provider posture: mock/offline only
- Local live deployment: blocked
- Staged internal testing: `No-go`
- Public/beta live generation: `No-go`

This runbook is for planning and manually executing a future Render cloud
offline rehearsal only. It is mock-only/offline and does not approve live LLM
requests, staged internal testing, public/beta generation, production
deployment, or any live external provider.

## Target Assumptions

Render is used only as a non-production app platform for this rehearsal.

Assumptions:

- One Render Web Service runs the FastAPI backend.
- One Render Static Site serves the Vue/Vite frontend from `frontend/dist`.
- One Render Postgres instance or other explicitly approved safe test database
  is used for non-production data only.
- Render service logs, deploy logs, and rollback/redeploy history are available
  to the operator.
- Runtime config is stored in Render environment variables or secret files, not
  tracked files.
- Preview URLs remain restricted to approved operators and are not promoted as
  public/beta routes.

Fail before deployment if Render project access, logs, rollback, or a
non-production database cannot be confirmed.

## Service Layout Recommendation

- Backend: Render Web Service named `<render-backend-service-name>`.
- Frontend: Render Static Site named `<render-frontend-service-name>`.
- Database: Render Postgres named `<render-postgres-name>` or an approved safe
  disposable test database.
- Runtime config: Render service environment variables.
- Logs: Render deploy logs and service logs, with sanitized evidence only.
- Rollback: Render deploy rollback/redeploy to a previous successful deploy, or
  service shutdown if this is the first rehearsal deploy.

Keep backend, frontend, and database in the same non-production Render project
or team boundary when possible.

## Backend Deployment Shape

Render shape:

- Service type: Web Service.
- Runtime: Python.
- Root directory: `backend`.
- Build command:

```text
pip install -r requirements.txt
```

- Start command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Render expects web services to bind to `0.0.0.0` and use the `PORT`
environment variable assigned by the platform. Do not hard-code a port in the
Render start command.

Do not add `LLM_API_KEY`, OpenAI-compatible provider config, live vector DB,
live POI, live routing, ticketing, affiliate, TTS, or managed-auth credentials
to the service.

## Frontend Deployment Shape

Render shape:

- Service type: Static Site.
- Root directory: `frontend`.
- Build command:

```text
npm ci && npm run build
```

- Publish directory:

```text
dist
```

Frontend runtime config must point only to the approved non-production backend:

```text
VITE_API_BASE_URL=<render-backend-preview-url>
```

The frontend URL must be added to backend CORS as an exact allowed origin.

## Database Choice For Non-Production

Preferred: a disposable Render Postgres database dedicated to the rehearsal.

Acceptable alternative: an explicitly approved safe test database that is
non-production, isolated from public/beta users, and resettable.

Requirements:

- Never point at production data.
- Store the database URL only in Render service config.
- Prefer Render's internal database URL for backend connections from the same
  Render region/project boundary.
- Record database name, region, engine/version, and reset/delete plan before
  migration.
- Confirm backup/snapshot behavior if rollback evidence depends on it.

## Required Runtime Versions

Record exact Render versions before execution:

- Python: `<render-python-runtime-version>`; local workspace observed
  `Python 3.14.0`.
- Node.js: `<render-node-runtime-version>`; local workspace observed
  `Node v24.11.0`.
- npm: `<render-npm-version>`; local workspace observed `npm 11.6.2`.
- Database: `<render-postgres-engine-version-or-test-db-version>`.

Use versions supported by Render and compatible with the dependency files in
`backend/requirements.txt` and `frontend/package-lock.json`. If Render's
default versions differ from local, record the difference in the evidence
record.

## Build Commands

Local preflight from repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cloud_offline_render_preflight.ps1
```

Optional local harness:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cloud_offline_render_preflight.ps1 -RunHarness
```

Render backend build command:

```text
pip install -r requirements.txt
```

Render frontend build command:

```text
npm ci && npm run build
```

No build step may configure live provider credentials.

## Start Commands

Backend:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Frontend:

```text
Render Static Site serving frontend/dist
```

## Health And Readiness URLs

Replace placeholders during manual rehearsal:

- Backend health: `https://<render-backend-service>.onrender.com/api/health`
- Backend readiness:
  `https://<render-backend-service>.onrender.com/api/readiness`
- Frontend preview: `https://<render-frontend-static-site>.onrender.com/`

Expected:

- `/api/health` returns `status=ok`.
- `/api/readiness` returns `status=ready`.
- Readiness shows database `ok`.
- Readiness shows external calls disabled and all providers mock/offline.

## Migration And Seed Approach

Use the backend service environment and non-production database URL.

Recommended sequence:

1. Confirm the Render database is non-production and resettable.
2. Open a one-off shell/job only if it does not enable live providers.
3. Run migrations from the `backend` directory:

```text
python -m alembic upgrade head
```

4. Seed bundled mock data:

```text
python -m scripts.seed_database
```

5. Validate seed data with one of:

```text
python -m scripts.validate_seed_data
GET /api/admin/seed/validate
```

6. Confirm London, Sherlock Holmes, and Baker Street exist, and Baker Street
   has provenance and verification notes.

Stop and roll back if migration or seed validation fails.

## Required Environment Variables

Use `docs/cloud-offline-env-render.template.md` as the source posture.

Required offline values:

```text
APP_ENV=<non-production-offline-env>
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
ENABLE_AUTH=false
AUTH_PROVIDER=dev
AUTH_ALLOW_DEV_USER_FALLBACK=false
```

Database and URL values must be placeholders in docs and real values only in
Render config:

```text
LITINERARY_DATABASE_URL=<render-postgres-internal-url-from-render-config>
BACKEND_URL=<render-backend-preview-url>
FRONTEND_URL=<render-frontend-preview-url>
CORS_ALLOWED_ORIGINS=<render-frontend-preview-origin>
LOG_LEVEL=<render-log-level>
PORT=<render-provided-port>
VITE_API_BASE_URL=<render-backend-preview-url>
```

## Forbidden Env Vars And Values

Forbidden:

- `ENABLE_REAL_LLM=true`
- `ALLOW_EXTERNAL_CALLS=true`
- `ENABLE_STAGED_INTERNAL_LLM_TESTING=true`
- `ENABLE_INTERNAL_ACCESS_GATE=true`
- `LLM_PROVIDER=openai_compatible`
- `LITINERARY_AI_PROVIDER=openai_compatible`
- any `LLM_API_KEY`
- any `OPENAI_API_KEY`
- any real vector DB key or URL
- any Google Places, POI, routing, ticketing, affiliate, TTS, or managed auth
  credential
- any auth JWKS/provider metadata URL

No `LLM_API_KEY` is required. If any live provider credential is present, the
rehearsal fails.

## Provider Posture Checks

Readiness must show:

- `ALLOW_EXTERNAL_CALLS=false`.
- all providers `mode=mock`.
- all providers `realEnabled=false`.
- all providers `externalCallsAllowed=false`.
- LLM provider fake/mock, not `openai_compatible`.
- routing provider mock.
- no live managed auth lookup.

Fail if any provider reports live/real mode or external calls allowed.

## Log And Redaction Checks

Review Render logs for:

- backend startup
- build output
- health/readiness requests
- migration and seed output
- mock itinerary generation
- rollback/redeploy or shutdown

Fail if logs contain:

- API keys or key-like values
- Authorization headers
- raw provider payloads
- full raw itinerary responses
- `/v1/chat/completions`
- live provider endpoint URLs
- database URL values

Evidence must summarize categories and outcomes only. Do not paste secret
values, full env dumps, Authorization headers, or raw responses.

## Rollback And Revision Restore Checks

Before execution, record:

- previous successful backend deploy
- previous successful frontend deploy
- rollback/redeploy method
- shutdown method
- database reset/delete method

After validation:

1. Roll back to the previous non-production deploy, or shut down/remove the
   rehearsal services if no previous deploy exists.
2. Confirm frontend static site no longer points at an unintended backend.
3. Confirm backend health is unavailable or points to the intended rollback
   revision.
4. Confirm Render env vars still have no live provider credentials.
5. Confirm no public/beta route remains.

Render deploy rollback does not prove environment variable rollback. Review
runtime env posture after rollback as a separate check.

## Evidence Capture Checklist

Complete `docs/cloud-offline-rehearsal-record-render.md` with:

- date/time
- operator
- Render project/environment name
- commit SHA
- backend/frontend URLs
- database target
- env posture result
- migration/seed result
- health/readiness result
- provider posture result
- mock itinerary-generation result
- log/redaction result
- rollback result
- secret hygiene result
- pass/fail verdict
- blockers
- next action

Do not include secrets, raw provider payloads, Authorization headers, database
URL values, or full raw responses.

## Explicit Mock-Only Statement

This Render runbook is mock-only/offline. It does not deploy by itself, does not
create cloud resources, does not require `LLM_API_KEY`, does not permit live
provider credentials, and does not approve local live deployment, staged
internal live LLM testing, public/beta live generation, or any live external
provider.

## References

- Render web services: https://render.com/docs/web-services
- Render static sites: https://render.com/docs/static-sites
- Render PostgreSQL connections: https://render.com/docs/postgresql-creating-connecting
- Render deploy rollbacks: https://render.com/docs/deploy-rollbacks
