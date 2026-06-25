# Local Offline Deployment Rehearsal

## Purpose

This rehearsal verifies that Litinerary can start and exercise the core backend
deployment posture locally while every provider remains offline/mock. It uses
the Batch 4 deployment-readiness harness as the preflight gate before starting a
temporary backend.

This rehearsal does not approve staged internal live LLM testing, public/beta
live generation, cloud deployment, or any live non-LLM provider.

The recorded local offline rehearsal has passed. The next gate is the
cloud-specific offline deployment rehearsal in
`docs/cloud-offline-deployment-rehearsal.md`; local live deployment remains
blocked.

## Prerequisites

- Run from the repository root on Windows PowerShell.
- The project virtual environment exists at `venv\Scripts\python.exe`.
- Frontend dependencies are installed under `frontend\node_modules`.
- Port `8765` is free, or another port is supplied with `-Port`.
- No real API key is required or used.

## Environment Posture

The rehearsal script forces this posture for the backend process:

- `APP_ENV=development`
- `ENABLE_ADMIN_ROUTES=true`
- `ENABLE_REAL_LLM=false`
- `ALLOW_EXTERNAL_CALLS=false`
- `ENABLE_STAGED_INTERNAL_LLM_TESTING=false`
- `ENABLE_INTERNAL_ACCESS_GATE=false`
- AI/LLM provider: `fake`
- vector provider: `fake`
- POI verification provider: `mock`
- routing provider: `mock`
- ticketing, affiliate, and TTS providers: `mock`
- auth provider: local/dev mode
- daily provider cost ceiling: `0`

The script clears `LLM_API_KEY`, `OPENAI_API_KEY`, provider API key variables,
and live provider URLs before starting the backend.

## Preflight Harness

The rehearsal starts with the Batch 4 preflight harness:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\deployment_readiness_check.ps1
```

The rehearsal stops immediately if the harness fails.

## Backend Startup

The script creates a temporary SQLite database, applies Alembic migrations,
seeds bundled data, then starts:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

The process is hidden and is always stopped by the script cleanup block.

## Frontend Build Or Preview

The preflight harness validates frontend tests, typecheck, and build. A manual
preview can be run separately after a passing rehearsal:

```powershell
cd frontend
npm.cmd run preview -- --host 127.0.0.1
```

The preview must still point at the offline/mock backend. It does not approve
live providers.

## Health And Readiness Checks

The rehearsal checks:

- `GET /api/health` returns `{"status":"ok"}`
- `GET /api/readiness` returns `ready`
- external calls are disabled
- staged/internal live LLM testing is disabled
- every provider reports mock/offline mode
- readiness does not expose secrets or raw provider payload fields

## Seed Checks

The rehearsal calls:

- `POST /api/admin/seed/reset`
- `GET /api/admin/seed/validate`

Seed validation must pass and the reset response must include bundled
destination/book/POI/itinerary counts.

## Mock Itinerary Generation Check

The rehearsal calls `POST /api/itinerary/generate` with:

```json
{
  "destinationId": "london",
  "bookId": "sherlock-holmes",
  "durationDays": 1,
  "transportationMode": "walking"
}
```

The response must:

- use `mock_ai`, not `openai_compatible`
- include Baker Street
- use `mock_routing`
- contain no secret-like values
- contain no raw provider payload fields

## Shutdown And Rollback

The script stops the backend process and confirms no listener remains on the
rehearsal port. It also attempts to remove the temporary SQLite database.

If shutdown fails, the rehearsal fails and records the listener status.

## Pass/Fail Criteria

Pass requires:

- preflight harness passes
- migrations and seed setup pass
- health/readiness pass
- provider posture remains offline/mock
- seed reset and validation pass
- mock itinerary generation passes
- backend shutdown succeeds
- no listener remains on the rehearsal port
- no secret-like values or raw provider payloads are found in checked responses

Any failure is a blocker for local offline deployment rehearsal evidence.

## Evidence Checklist

The script writes sanitized evidence to:

- `docs/local-offline-deployment-rehearsal-record.md`

Evidence should include:

- execution timestamp
- harness result
- backend health result
- readiness provider posture
- seed reset/validation result
- mock itinerary-generation result
- shutdown/no-listener result
- no-live-provider confirmation
- no-secret/no-raw-payload confirmation
- limitations and next action

Do not paste raw full responses, secrets, Authorization headers, or raw provider
payloads into evidence.
