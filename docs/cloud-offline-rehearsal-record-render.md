# Cloud Offline Rehearsal Record: Render

## Metadata

- Date/time:
- Operator:
- Selected target: Render
- Render project/environment name:
- Backend service name:
- Frontend static site name:
- Commit SHA:
- Backend URL:
- Frontend URL:
- Database target:
- Database engine/version:

## Environment Posture Result

- `APP_ENV`:
- `ENABLE_REAL_LLM=false`:
- `ALLOW_EXTERNAL_CALLS=false`:
- `ENABLE_STAGED_INTERNAL_LLM_TESTING=false`:
- `ENABLE_INTERNAL_ACCESS_GATE=false`:
- `ENABLE_MOCK_SERVICES=true`:
- LLM provider fake/mock:
- non-LLM providers mock/offline:
- Auth disabled/mock:
- No `LLM_API_KEY` configured:
- No real provider credentials configured:
- Result:

## Migration Result

- Command:
- Result:
- Notes:

## Seed Result

- Command:
- Validation command or endpoint:
- Result:
- Counts:
- London/Sherlock Holmes/Baker Street confirmed:
- Baker Street provenance/verification notes confirmed:

## Health Result

- Endpoint:
- Result:
- Observed status:

## Readiness Result

- Endpoint:
- Result:
- Observed status:
- Database status:
- External calls allowed:
- Secret-like values exposed:
- Raw provider payload fields exposed:

## Provider Posture Result

| Provider type | Observed provider | Observed mode | Real enabled | External calls allowed |
| --- | --- | --- | --- | --- |
| auth | | | | |
| llm | | | | |
| vector_db | | | | |
| poi_verification | | | | |
| routing | | | | |
| ticketing | | | | |
| affiliate | | | | |
| tts | | | | |

## Mock Itinerary Generation Result

- Scenario: `london / sherlock-holmes / 1 day / walking`
- Result:
- Generated title:
- LLM provider:
- Routing provider:
- Baker Street present:
- `/v1/chat/completions` called:
- Live provider request observed:
- Raw provider payload exposed:
- Secret-like values exposed:

## Logs And Redaction Result

- Render deploy logs reviewed:
- Backend startup logs reviewed:
- Health/readiness logs reviewed:
- Migration/seed logs reviewed:
- Mock generation logs reviewed:
- Rollback/redeploy or shutdown logs reviewed:
- Retention window:
- Authorization header present:
- Raw provider payload present:
- Secret-like value present:
- Database URL value present:
- Result:

## Rollback Result

- Backend rollback target:
- Frontend rollback target:
- Backend rollback/shutdown action:
- Frontend rollback/shutdown action:
- Database reset/delete action:
- Backend health after rollback:
- Frontend state after rollback:
- No public/beta route remains:
- No live provider config remains:
- Env posture reviewed after rollback:
- Result:

## Secret Hygiene Result

- Repository/template scan:
- Render runtime config review:
- Render log review:
- Evidence review:
- Result:

## Verdict

- Pass/fail verdict:
- Blockers:
- Limitations:
- Next action:

## Safety Confirmation

- Cloud deployment performed:
- Cloud resources created:
- Live LLM request made:
- `/v1/chat/completions` called:
- External providers enabled:
- Secrets/raw provider payloads added:
- Staged internal testing approved:
- Public/beta live generation approved:

## Database resource:
- Name: dpg-d8vnkrcm0tmc73d1m7ng-a
- Region: Ohio (US East)
- Plan: Free
- Production? No
- Connection type used by backend: Internal Database URL

### Backend pytest gate

Command:

```powershell
.\venv\Scripts\python.exe -m pytest backend\tests --basetemp=tests\.artifacts\tmp\pytest-render-rehearsal
```

Result:

- Status: Passed
- Tests: 292
- Failures: 0
- Errors: 0
- Skipped: 3
- Duration: 31.897s

Notes:

The skipped tests were live-provider integration tests and remained skipped by default:

- `test_live_google_places_integration_skipped_by_default`
- `test_live_llm_integration_skipped_by_default`
- `test_live_openrouteservice_integration_skipped_by_default`

No cloud provider was contacted by this backend pytest gate.

### Frontend build gate

Command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cloud_offline_render_preflight.ps1 -RunFrontendBuild
```

Result:

- Status: Passed
- Final output: `Render cloud-offline preflight passed. No deployment was performed.`

Notes:

The frontend build gate was run through the Render cloud-offline preflight script with `-RunFrontendBuild`.

No deployment was performed, and no cloud provider was contacted by this preflight gate.

### Full local Render preflight

Command:

```powershell
$env:PYTHONPATH = "C:\Users\syahn\source\litinerary\backend"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cloud_offline_render_preflight.ps1 -RunHarness -RunFrontendBuild
```

Result:

- Status: Passed
- Final output: `Render cloud-offline preflight passed. No deployment was performed.`

Notes:

The first full preflight attempt failed during offline profile validation because the temporary validation script could not import the backend `app` package:

```text
ModuleNotFoundError: No module named 'app'
```

The rerun passed after setting `PYTHONPATH` to the absolute backend path:

```powershell
$env:PYTHONPATH = "C:\Users\syahn\source\litinerary\backend"
```

The local deployment-readiness harness and frontend build completed successfully through the Render cloud-offline preflight script.

No deployment was performed, and no cloud provider was contacted by this preflight gate.

### Render backend deploy and smoke check

Service:

- Name: `litinerary-render-offline-backend`
- URL: `https://litinerary-render-offline-backend.onrender.com`
- Branch: `main`
- Commit: `2defe81`
- Auto Deploy: Off
- Environment posture: mock-only/offline, no live provider credentials

Deploy result:

- Status: Live
- Build result: Successful

Smoke checks:

- `/health`: Passed
  - Status: 200
  - Body: `{"status":"ok"}`
- `/api/readiness`: Passed
  - Status: 200
  - Body included:
    - `status: ready`
    - `appEnv: development`
    - `checks.database.status: ok`

Notes:

The root path `/` returned 404 and `/readiness` returned 404. These were not treated as failures because the backend health endpoint is `/health` and the readiness endpoint is `/api/readiness`.

No real provider credentials were added. No live LLM, POI, routing, vector DB, ticketing, affiliate, managed-auth, or TTS integrations were enabled.

### Render frontend deploy and smoke check

Site:

- Name: `litinerary-render-offline-frontend`
- URL: `https://litinerary-render-offline-frontend.onrender.com`
- Branch: `main`
- Root Directory: `frontend`
- Build Command: `npm ci && npm run build`
- Publish Directory: `dist`
- Auto Deploy: Off

Deploy result:

- Status: Live
- Build result: Successful
- Build output included:
  - `vue-tsc --noEmit && vite build`
  - `✓ built`
  - `Your site is live`

Smoke check:

- Frontend URL loaded: Passed
- Visible issue observed: No

Notes:

The frontend build reported npm audit findings:

- 6 vulnerabilities
- 3 moderate
- 2 high
- 1 critical

These audit findings were not treated as a blocker for this mock-only/offline Render rehearsal, but they should be tracked before any beta or production exposure.

### Render frontend-backend integration smoke check

Initial result:

- Status: Failed
- Action tested: Choose a Destination
- Observed result: Destinations could not load — Failed to fetch
- Browser console showed CORS failure:
  - Backend request: `https://litinerary-render-offline-backend.onrender.com/api/destinations`
  - Frontend origin: `https://litinerary-render-offline-frontend.onrender.com`
  - Error: No `Access-Control-Allow-Origin` header was present on the preflight response.

Fix applied:

- Backend environment updated:
  - `CORS_ALLOWED_ORIGINS=https://litinerary-render-offline-frontend.onrender.com`
  - `FRONTEND_URL=https://litinerary-render-offline-frontend.onrender.com`
- Backend redeployed manually.
- Backend redeploy status: Succeeded.

Final result:

- Status: Passed
- Action tested: Choose a Destination
- Observed result: Results loaded as expected.

Notes:

The frontend was already using the correct backend API base URL after setting `VITE_API_BASE_URL` on the frontend Static Site and redeploying it. The remaining blocker was backend CORS configuration.

No wildcard CORS origin was used. No secrets or live provider credentials were added.


### Render Postgres migration, seed, and mock itinerary smoke check

Initial database issue:

- Backend was initially falling back to SQLite because `LITINERARY_DATABASE_URL` was not set in the backend Render environment.
- Symptom during mock itinerary/account flow:
  - `sqlalchemy.exc.OperationalError`
  - `sqlite3.OperationalError: no such table: users`

Database environment fix:

- Backend environment updated with the Render Postgres Internal Database URL.
- The URL scheme was changed from `postgresql://` to `postgresql+psycopg://` so SQLAlchemy uses the installed `psycopg` driver.
- Secret value was not pasted into docs or chat.

Verification:

- `LITINERARY_DATABASE_URL set: True`
- `LITINERARY_DATABASE_URL scheme: postgresql+psycopg`

Postgres commands:

- `python -m alembic upgrade head`: Passed
- `python -m scripts.seed_database`: Passed
- `python -m scripts.validate_seed_data`: Passed

Final mock itinerary smoke check:

- Status: Passed
- Action tested: London / Sherlock Holmes / 1 day / walking
- Observed result: Output as expected
- Save/account error: No
- Provider/live-call concern visible: No

Notes:

The earlier provider log for narration showed `provider_name: local_usage_policy` and `provider_type: tts`, which is consistent with the mock/offline rehearsal posture. No live provider call was observed.

### Render log hygiene review

Scope reviewed:

- Backend deploy logs
- Backend runtime logs
- Frontend deploy logs
- Health/readiness logs
- Frontend-backend smoke-check logs
- Mock itinerary-generation logs
- Migration/seed/validation command output

Checked for:

- Database URL values
- Authorization headers
- API keys or tokens
- OpenAI, Google Places, OpenRouteService, vector DB, ticketing, affiliate, managed-auth, or TTS provider payloads
- Raw provider responses
- Passwords or connection strings

Result:

- Status: Passed
- Finding: None

Notes:

No visible secrets, database URL values, authorization headers, provider request payloads, raw provider responses, API keys, tokens, passwords, or connection strings were observed in the reviewed logs/evidence.