# Beta Deployment Dry Run

This runbook prepares Litinerary for a mock-only beta/staging environment. It does not deploy, push, add secrets, or connect live providers.

## Environment Profiles

Use the checked-in examples as templates only:

- Local development: `.env.example`, `frontend/.env.example`
- Standard tests: `.env.test.example`
- Beta/staging dry run: `.env.beta.example`, `frontend/.env.beta.example`
- Production template: `.env.production.example`, `frontend/.env.production.example`

Do not commit `.env`, `.env.local`, copied provider secrets, database files, build outputs, or generated caches.

## Beta Defaults

The beta dry-run profile is intentionally mock-only:

- `APP_ENV=beta`
- `DEBUG=false`
- `ENABLE_ADMIN_ROUTES=false`
- `ENABLE_DEBUG_ROUTES=false`
- `ENABLE_MOCK_SERVICES=true`
- all `ENABLE_REAL_*` flags are `false`
- `ENABLE_AFFILIATE_LINKS=false`
- `ALLOW_EXTERNAL_CALLS=false`
- `ENABLE_INTEGRATION_TESTS=false`
- `AUTH_ALLOW_DEV_USER_FALLBACK=false`
- exact `CORS_ALLOWED_ORIGINS`

Provider keys remain empty in beta examples. Readiness exposes only whether credentials are configured, never secret values.

## Dry-Run Command

From the repository root:

```powershell
.\scripts\beta_dry_run.ps1
```

The script validates configuration, checks Alembic heads/current revision, runs backend tests, starts a temporary backend server, checks `/api/health`, checks `/api/readiness`, confirms admin routes are disabled, runs frontend tests, and builds the frontend.

On machines where PowerShell script execution is disabled, run the same script with a process-scoped execution-policy bypass:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\scripts\beta_dry_run.ps1
```

This does not change machine policy, does not deploy, and does not enable external providers.

Faster local syntax checks:

```powershell
.\scripts\beta_dry_run.ps1 -SkipTests
```

## Verified Dry Run - 2026-06-15

Command attempted from the repository root:

```powershell
.\scripts\beta_dry_run.ps1
```

Result on this machine: blocked before execution by PowerShell execution policy:

```text
running scripts is disabled on this system
```

Verified command used:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\scripts\beta_dry_run.ps1
```

Final result: passed end to end. No deployment was performed. No real providers were connected. No secrets were added.

Verified output summary:

- Config validation: `errors: []`.
- Profile: `APP_ENV=beta`, `DEBUG=false`, admin/debug routes disabled, mock services enabled.
- External-call policy: `externalCallsAllowed=false`, dry-run guard confirmed external calls blocked.
- Providers: LLM, Vector DB, POI verification, routing, ticketing, affiliate, and TTS all reported `realEnabled=false`, `externalCallsAllowed=false`, and mock/fake mode.
- Alembic head/current: `20260614_0007 (head)`.
- Beta database migration: `alembic upgrade head` completed.
- Seed loading: completed through `python -m scripts.seed_database`. This run reported `0 destinations, 0 books, 0 POIs, 0 itineraries` because the dry-run SQLite database was already seeded from earlier attempts. A fresh beta dry-run database is expected to report `5 destinations, 10 books, 13 POIs, 2 itineraries`.
- Backend tests: `191 passed, 3 skipped, 1 warning`.
- Backend smoke: `/api/health` returned `ok`; `/api/readiness` returned `ready`; admin seed route returned `403`; debug recommendations route returned `403`.
- Frontend tests: `11 passed` test files, `55 passed` tests.
- Frontend build: `vue-tsc --noEmit && vite build` completed, Vite built successfully.
- Final line: `Beta deployment dry run completed. No deployment was performed.`

Fixes made during verification:

- The dry-run script now fails when native commands fail instead of continuing after a nonzero exit code.
- Backend tests now run with a clean local test environment instead of inheriting beta settings that intentionally disable admin/debug routes.
- Backend tests now use a per-process workspace pytest temp directory, such as `.pytest_tmp_beta_dry_run_<pid>`, to avoid Windows locked-directory collisions.
- The beta database is explicitly migrated and seeded before backend health/readiness checks.
- Readiness smoke now verifies external calls are disabled and all provider `realEnabled` flags are false.
- Debug route protection is checked in addition to admin route protection.
- Frontend commands are launched through `cmd.exe /c npm.cmd ...` with the frontend directory as the explicit working directory.

Machine-specific notes:

- This Windows machine blocks direct `.ps1` execution by policy. Use the process-scoped bypass command above, or enable script execution according to local policy.
- In the Codex sandbox, frontend Vite/Vitest child processes can fail with `Cannot read directory "../../..": Access is denied` when launched from inside a longer PowerShell script. Running the full dry run outside the sandbox, or from a normal VS Code terminal, avoids that sandbox path restriction.
- Stale pytest temp directories can be locked on Windows. The dry-run script now avoids this by using a unique `--basetemp` path per process.

## Manual Checklist

- Install backend dependencies: `..\venv\Scripts\python.exe -m pip install -r backend\requirements.txt`
- Install frontend dependencies: `npm install` from `frontend`
- Confirm `.env*example` files contain placeholders only.
- Confirm no `.env`, local DB, cache, build output, or secret file is staged.
- Run Alembic migrations: `..\venv\Scripts\python.exe -m alembic upgrade head` from `backend`.
- Seed only safe non-production data: `..\venv\Scripts\python.exe -m scripts.seed_database` from `backend`.
- Run backend tests: `..\venv\Scripts\python.exe -m pytest --basetemp=.pytest_tmp_beta_dry_run` from `backend`.
- Run frontend tests: `npm test` from `frontend`.
- Run smoke tests: `.\scripts\test_smoke.ps1`.
- Build frontend: `npm run build` from `frontend`.
- Start backend with beta env and confirm `/api/health`.
- Confirm `/api/readiness` reports database `ok` and mock provider modes.
- Confirm admin routes return `403`.
- Confirm debug routes return `403`.
- Confirm `ALLOW_EXTERNAL_CALLS=false`.
- Confirm all real provider feature flags are `false`.
- Confirm CORS origins are exact beta frontend origins.
- Confirm no real secrets are committed or printed in logs.

## Private Staging Preflight Checklist

Complete this checklist before any private staging beta deployment attempt. This is still a mock-only staging profile; do not enable real providers, external calls, admin/debug routes, or real secrets.

- Confirm the private beta frontend URL, for example `https://beta.litinerary.example`.
- Confirm the private beta backend API URL, for example `https://api.beta.litinerary.example`.
- Confirm backend `CORS_ALLOWED_ORIGINS` exactly matches the frontend origin. Do not use `*`.
- Confirm frontend `VITE_API_BASE_URL` exactly matches the backend API origin.
- Confirm backend profile is `APP_ENV=beta`, `DEBUG=false`, `ENABLE_ADMIN_ROUTES=false`, and `ENABLE_DEBUG_ROUTES=false`.
- Confirm `ENABLE_MOCK_SERVICES=true`.
- Confirm all real-provider flags are disabled: `ENABLE_REAL_LLM=false`, `ENABLE_REAL_VECTOR_DB=false`, `ENABLE_REAL_POI_PROVIDER=false`, `ENABLE_REAL_ROUTING=false`, `ENABLE_REAL_TICKETING=false`, and `ENABLE_REAL_TTS=false`.
- Confirm `ENABLE_AFFILIATE_LINKS=false`, `ALLOW_EXTERNAL_CALLS=false`, and `ENABLE_INTEGRATION_TESTS=false`.
- Confirm `AUTH_ALLOW_DEV_USER_FALLBACK=false`.
- Confirm all provider API key values are empty or supplied only as non-secret placeholders in example files.
- Confirm `LITINERARY_DATABASE_URL` points to an explicitly non-production beta/staging database.
- Confirm seed data is approved for beta and contains no private, secret, or production-only data.
- Run `alembic upgrade head` against the beta database before seeding.
- Run the seed command against the beta database and confirm expected counts for a fresh database.
- Confirm `/api/health` is reachable and returns `{"status":"ok"}`.
- Confirm `/api/readiness` is reachable, returns `ready`, reports database `ok`, reports provider mock/fake modes, and exposes only credential booleans.
- Confirm `/api/admin/seed/validate` returns `403`.
- Confirm `/api/users/dev-reader/recommendations/mock` returns `403`.
- Confirm logs include `X-Request-ID`/request IDs and do not include secrets, bearer tokens, raw prompts, raw provider payloads, or copyrighted text.
- Confirm a rollback/restart procedure exists for the chosen host.
- Confirm the private staging URL is not publicly announced until the dry run and preflight checks pass.

## Deployment Gate

Do not deploy beta until:

- `.\scripts\beta_dry_run.ps1` passes.
- Product owner confirms beta URL and CORS origin.
- Database target is explicitly non-production.
- Seed data is approved for beta.
- Health and readiness checks are reachable from the intended environment.
- Logs contain request IDs and no sensitive payloads.
- Rollback/restart procedure is documented for the chosen host.
