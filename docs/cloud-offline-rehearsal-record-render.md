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
