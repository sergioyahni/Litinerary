# Litinerary Production Development Progress

Last updated: 2026-08-21

## Current Stage

Production Gate B in progress; Gate C partially prepared locally.

Stage 0 is complete. S1-01, S1-02, S1-03, S1-04, and S1-05 are complete. PLU-01 is complete: owner-approved product/platform decisions are recorded in `docs/production-decisions.md`. PLU-02 local implementation is partially complete: Auth0 Vue SDK integration, frontend login/callback/session restoration/silent token acquisition/logout, `/api/me` hydration, protected-feature UX, deployed dev-token isolation, and placeholder-only staging/prod configuration are implemented. PLU-03 local repository work is partially complete: dependency-security preflight passed for production runtime, compatible npm transitive vulnerabilities were remediated, `render.yaml` now defines the intended Render backend/frontend/PostgreSQL staging and production structure, and provider-disablement regression coverage was added. The project is still not staging-ready or production-ready because real Auth0 staging resources, Render production infrastructure, managed PostgreSQL, CI/CD, observability/alerting, backup/restore evidence, and one persistence-integrity issue remain open. The remaining single-command deployment harness issue is documented as a Codex sandbox process-initial-directory limitation, with an equivalent split validation procedure.

The next recommended production unit is PLU-04 GitHub Actions CI/CD, dependency/security scanning, secret hygiene, release packaging, and post-deploy smoke gates. Live LLM/vector/POI/routing/ticketing/TTS/affiliate work is explicitly post-launch for v1.

## Litinerary v1 Scope

Owner-approved initial production scope: Auth0 managed authentication, Render production infrastructure, managed PostgreSQL persistence, durable usage controls, and mock/curated product providers.

Included for v1:

- Destination and book browsing.
- Deterministic seeded/mock itinerary generation.
- Public itinerary repository list/detail/narration/map behavior.
- Authenticated bookmarks, reviews, preferences, and account-backed profile features.
- Existing authenticated profile, preferences, bookmarks, and reviews functionality.
- Durable DB-backed usage limits and provider-budget controls.

Deferred unless the owner explicitly adds them to v1:

- Live LLM, vector, POI, routing, ticketing, TTS, affiliate, payment, or commerce providers. PLU-08 is post-launch and not required for initial Production GO.
- Subscriber chat/refinement as a public v1 journey.
- Private itinerary management UI, private itinerary list, save/edit/delete, publish/unpublish, sharing links, and true unlisted sharing.
- Product analytics, generated audio storage, self-service deletion, and mature disaster-recovery drills beyond the launch minimum.

## Stage 0 Final Status

Stage 0: COMPLETE.

Completed evidence:

| Area | Status | Evidence |
|---|---|---|
| Repository hygiene | Passed | `git status --short --branch --ignored` now completes without permission-denied warnings. |
| Backend import | Passed | Prior Stage 0 report recorded successful FastAPI/app import. |
| Backend tests | Passed | Full pytest now reports 291 passed, 3 skipped, 10 warnings. |
| Pytest cache/temp hygiene | Passed | Pytest cache moved out of the locked `tests/.artifacts/tmp` subtree to `tests/.artifacts/pytest-cache`; basetemp moved to `tests/.artifacts/pytest-tmp`. |
| Frontend focused integration tests | Passed | Direct `frontend/` execution reports 2 files, 9 tests passed. |
| Frontend typecheck/test/build | Passed | Prior Stage 0 report recorded typecheck, full Vitest, and production build success. |
| Migrations and seed | Passed | Prior Stage 0 report recorded Alembic head `20260614_0007` and successful seed. |
| Backend startup | Passed | Temporary backend returned `/api/health=ok` and `/api/readiness=ready`. |
| Deployment readiness harness | Codex-specific split procedure | Backend/profile portions pass; frontend step fails only when npm is launched from a process that initially started at repo root in the Codex sandbox. |

## Completed Tasks

### S0-01 - Capture current baseline checks

- Date: 2026-08-15
- Result: completed in `docs/stage-0-baseline-session-report.md`.
- Summary: baseline commands showed backend, frontend, migrations, seed, startup, health, and readiness were broadly healthy, with remaining artifact and Codex harness issues.

### S0-02 - Repair artifact/cache hygiene

- Date: 2026-08-15
- Result: complete.
- Changes:
  - `.gitignore` now ignores generated `tests/.artifacts` descendants recursively while preserving the tracked `.gitkeep`.
  - `pytest.ini` now uses `tests/.artifacts/pytest-cache` and `tests/.artifacts/pytest-tmp`, avoiding the previously locked `tests/.artifacts/tmp/.pytest_cache` and `tests/.artifacts/tmp/pytest` paths.
  - Old generated locked pytest artifact directories under `tests/.artifacts/tmp` were removed after approval.
- Validation:
  - `git status --short --branch --ignored` completed without permission-denied warnings.
  - `python -m pytest backend\tests\test_database_seed.py -q` passed without pytest cache warnings caused by repo configuration.
  - Full backend pytest passed.

### S0-03 - Resolve deployment-readiness harness question

- Date: 2026-08-15
- Result: complete with documented Codex sandbox limitation.
- Finding: `scripts/deployment_readiness_check.ps1` correctly uses `Push-Location frontend` before invoking npm. Earlier experiments showed `Push-Location`, `Start-Process -WorkingDirectory`, `cmd /c cd`, npm `--prefix`, and Node `process.chdir()` still fail in the Codex sandbox, while launching the same npm command with tool working directory `frontend/` succeeds.
- Decision: do not complicate the production harness for a Codex-only launch-context restriction.
- Codex-safe equivalent:
  - Run backend/profile/migration/startup portions with the harness as far as the frontend step.
  - Run frontend focused integration tests from `frontend/`:
    `npm.cmd test -- src/test/frontendApiIntegration.test.ts src/services/apiContract.integration.test.ts`
  - Run frontend typecheck/build from `frontend/` when frontend code changes.

### S1-01 - Fail closed for deployed user-owned routes

- Date: 2026-08-15
- Result: complete.
- Summary: user-owned backend routes now require authenticated owner/admin access in deployed environments even if `AUTH_REQUIRED_FOR_USER_FEATURES=false` is accidentally configured.
- Files:
  - `backend/app/core/auth.py`
  - `backend/app/api/routes/users.py`
  - `backend/tests/test_auth_foundation.py`
- Validation:
  - Focused auth pytest passed: 19 passed.
  - Full backend pytest passed: 291 passed, 3 skipped.

### S1-02 - Production authentication configuration and startup enforcement

- Date: 2026-08-15
- Result: complete.
- Summary: deployed environments now fail startup unless managed JWT/OIDC authentication is enabled, configured, and allowed to fetch JWKS/provider metadata. Local development and standard tests retain dev-token compatibility.
- Files:
  - `backend/app/core/config.py`
  - `backend/app/core/auth.py`
  - `backend/app/core/readiness.py`
  - `backend/scripts/validate_beta_config.py`
  - `scripts/deployment_readiness_check.ps1`
  - `scripts/beta_dry_run.ps1`
  - environment examples and production-readiness docs
  - `backend/tests/test_auth_foundation.py`
- Validation:
  - Representative startup validation pytest passed: 8 passed.
  - Focused backend auth/readiness/external-call suite passed: 80 passed.
  - Full backend pytest passed: 305 passed, 3 skipped.
  - Frontend typecheck, full Vitest, and production build passed.
  - Safe local backend startup returned `/api/health=ok` and `/api/readiness=ready`.

### S1-03 - Itinerary ownership, visibility, and access control

- Date: 2026-08-15
- Result: complete.
- Summary: itinerary ownership/public-private semantics are now explicit and enforced server-side. Public repository itineraries remain anonymous and ownerless. Subscriber chat refinements create private, subscriber-only, owner-bound itineraries. Private/unlisted itinerary detail and narration are owner/admin only, and unauthorized private IDs return `404` like missing IDs. User bookmark/review writes require the target itinerary to be public or accessible to the verified owner/admin, and bookmark lists filter inaccessible private rows.
- Files:
  - `backend/app/models/domain.py`
  - `backend/migrations/env.py`
  - `backend/migrations/versions/20260815_0008_itinerary_owner_constraints.py`
  - `backend/app/services/database_repository.py`
  - `backend/app/services/mock_repository.py`
  - `backend/app/services/user_repository.py`
  - `backend/app/api/routes/itineraries.py`
  - `backend/app/api/routes/users.py`
  - `backend/tests/test_itinerary_ownership.py`
  - `backend/tests/test_itinerary_ownership_migration.py`
  - `frontend/src/views/ItineraryDetailView.vue`
  - `docs/api-contract.md`
  - `docs/stage-1-s1-03-itinerary-ownership-report.md`
- Migration: `20260815_0008` normalizes legacy visibility, clears orphaned owner/creator IDs, adds the itinerary owner foreign key with `ON DELETE SET NULL`, and adds visibility/owner lookup indexes.
- Frontend state: no trusted ownership controls were added. The existing detail view remains compatible and its copy now says accessible route rather than public route because owners/admins can read private detail through the same endpoint when authenticated.
- Validation:
  - Focused ownership/migration pytest: 8 passed.
  - Focused regression suite: 71 passed.
  - Full backend pytest: 313 passed, 3 skipped, 12 warnings.
  - Frontend typecheck: passed.
  - Full frontend Vitest: 13 files and 65 tests passed.
  - Frontend production build: passed.
  - Migration/seed temp DB: head `20260815_0008`, seeded 5 destinations, 10 books, 13 POIs, 2 itineraries.
  - Runtime API validation: `/api/health=ok`, `/api/readiness=ready`, owner private detail `200`, other user `404`, anonymous `404`, public list count 2.
- Remaining ownership/sharing gaps: no dedicated private itinerary list, save/edit/delete, publish/unpublish, or sharing/unlisted workflow exists yet. `visibility=unlisted` is treated like private until that product contract is implemented.
- Newly discovered issue fixed: Alembic `fileConfig` disabled existing app loggers during migration tests; `backend/migrations/env.py` now preserves existing loggers so migrations do not mute structured logging in later tests.

### S1-04 - Durable usage, rate, and cost controls

- Date: 2026-08-15
- Result: complete.
- Summary: usage controls now support DB-backed durable UTC-window counters for anonymous itinerary generation, authenticated itinerary generation, subscriber chat, live-provider request budgets, and estimated provider cost budgets. Deployed environments fail startup unless `ENABLE_DURABLE_USAGE_CONTROLS=true`; local development and ordinary tests can still use the in-memory fallback.
- Files:
  - `backend/app/services/usage_policy.py`
  - `backend/app/core/config.py`
  - `backend/app/core/readiness.py`
  - `backend/app/main.py`
  - `backend/app/models/domain.py`
  - `backend/migrations/versions/20260815_0009_durable_usage_counters.py`
  - `backend/app/api/routes/itineraries.py`
  - `backend/app/services/mock_repository.py`
  - `backend/app/services/chat_service.py`
  - `frontend/src/services/apiClient.ts`
  - environment templates, README/API/provider/production docs, and usage/migration tests
- Migration: `20260815_0009` creates `usage_limit_counters` with subject/action/window uniqueness and lookup/retention indexes.
- Runtime semantics: reservations are atomic per counter row, keyed by subject/action/window, and use UTC minute/day windows. Composite generation/chat reservations refund earlier windows if a later window rejects. Durable limiter storage failures fail closed with `503`; rate/quota windows return `429` with `Retry-After` when known.
- Validation:
  - Focused usage-policy pytest: 24 passed.
  - Focused migration pytest: 2 passed.
  - Frontend API-client test: 5 passed.
  - Full backend pytest: 324 passed, 3 skipped.
  - Full frontend Vitest: 13 files and 66 tests passed.
  - Frontend typecheck and production build passed.
  - Migration/seed temp DB: head `20260815_0009`, seeded 5 destinations, 10 books, 13 POIs, 2 itineraries, and an empty `usage_limit_counters` table.
  - Runtime durable validation: `/api/health=ok`, `/api/readiness=ready`, durable usage controls `true`, first generation `200`, second generation `429` with `Retry-After`.

### S1-05 - Production database fail-fast and migration readiness

- Date: 2026-08-15
- Result: complete.
- Previous behavior: deployed profiles could inherit the default local SQLite URL, readiness only checked `SELECT 1`, deployed startup did not verify Alembic state, and mock repository selection could fall back to bundled data when DB seed/schema checks failed.
- Deployed DB contract: `internal`, `beta`, `staging`, and `production` require an explicit `LITINERARY_DATABASE_URL`, valid URL parsing, connectivity, and Alembic revision at the repository head. No database vendor is hard-coded by S1-05.
- Startup behavior: invalid deployed DB config fails immediately with `LITINERARY_DATABASE_URL` named; deployed unreachable, unmigrated, behind, or unknown-revision DBs fail startup before traffic. Local/test keep explicit SQLite and `create_all` convenience.
- Readiness behavior: `/api/health` remains liveness only. `/api/readiness` now reports safe DB metadata (`configured`, `dialect`, `connectivity`, migration status/current revisions/expected heads) and is non-ready for deployed invalid config, failed connectivity, missing migration metadata, behind revisions, or unknown revisions.
- Fallback protections: deployed repository selection no longer treats failed seed/schema checks as permission to use mock persistence, and deployed `init_db/create_all` is blocked. Seed/export/import/validate scripts skip schema auto-create in deployed profiles and assume Alembic has already run.
- Migration validation: disposable DB upgraded from `20260815_0008` to `20260815_0009`, retained 5 destinations, 10 books, 13 POIs, 2 itineraries, and kept `usage_limit_counters` empty.
- Files:
  - `backend/app/core/config.py`
  - `backend/app/core/database.py`
  - `backend/app/core/database_readiness.py`
  - `backend/app/core/readiness.py`
  - `backend/app/main.py`
  - `backend/app/services/mock_repository.py`
  - `backend/scripts/seed_database.py`
  - `backend/scripts/seed.py`
  - `backend/scripts/validate_seed_data.py`
  - `backend/scripts/reset_dev_db.py`
  - `backend/scripts/import_seed_data.py`
  - `backend/scripts/export_seed_data.py`
  - `backend/scripts/validate_beta_config.py`
  - `backend/tests/test_database_readiness.py`
  - `scripts/deployment_readiness_check.ps1`
  - `scripts/beta_dry_run.ps1`
  - environment templates and production/beta/API/deployment docs
  - `docs/stage-1-s1-05-database-fail-fast-readiness-report.md`
- Focused validation:
  - DB/readiness focused pytest: 31 passed, 30 warnings.
  - Python compile check: passed.
  - PowerShell script syntax tokenization: passed.
  - Beta dry run smoke with tests/build skipped: passed after aligning seed script and debug-route assertion.
- Complete validation:
  - Full backend pytest: 350 passed, 3 skipped, 114 warnings.
  - Frontend typecheck: passed.
  - Full frontend Vitest: 13 files and 66 tests passed.
  - Frontend production build: passed.
- Runtime results:
  - Valid beta disposable DB: startup succeeded, `/api/health=ok`, `/api/readiness=ready`, database configured/connectivity ok/migrations current.
  - Unmigrated disposable DB: readiness evaluator returned `status=error`, `connectivity=ok`, `migrations=missing`, with no schema creation or migration.
  - Unavailable disposable DB: startup validation failed closed with sanitized message `connectivity=error migrations=not_checked`.
- Remaining database/deployment risks: production still needs real hosted DB provisioning, backup/restore drills, migration rollback drills on provider snapshots, alerting for DB/readiness failures, and scheduled cleanup for expired usage counters.

## Stage 1 Production-Blocker Backlog

| ID | Priority | Area | Finding | Evidence | Production Risk | Dependencies | Definition of Done |
| -- | -------- | ---- | ------- | -------- | --------------- | ------------ | ------------------ |
| S1-01 | P1 | Auth/user authorization | Deployed user-owned routes must never accept path user IDs as identity. | `auth.py`, `users.py`; fixed this session. | Insecure direct object access if permissive flags reach deployed envs. | Existing JWT/dev auth foundation. | Deployed env user routes return 401 without current user and 403 for cross-user access; tests pass. |
| S1-02 | P1 | Production auth configuration | Complete: deployed startup now requires managed JWT/OIDC config and rejects dev auth/fallback. | `config.py`, `auth.py`, `.env.beta.example`, `.env.production.example`, tests. | Remaining operational work is to configure the real chosen provider and frontend SDK before public traffic. | Real provider tenant/client selection. | Staging/prod auth target documented, env templates aligned, startup fails for incomplete required auth config. |
| S1-03 | P1 | Data ownership | Complete: itinerary ownership/private/public semantics are explicit in schema, routes, repository, API docs, migration, and tests. | `docs/stage-1-s1-03-itinerary-ownership-report.md`; `20260815_0008`; ownership tests. | Remaining risk is future private CRUD/sharing work, not current cross-user private itinerary access through existing routes. | Auth identity model. | Done; keep future private CRUD/sharing behind the same owner/admin boundary. |
| S1-04 | P1 | Durable usage controls | Complete: DB-backed durable usage counters now protect rate, quota, request-budget, and estimated-cost windows. | `backend/app/services/usage_policy.py`; migration `20260815_0009`; usage-policy tests. | Remaining risk is operational alerting/retention scheduling, not in-process-only enforcement. | DB availability. | Done; keep `ENABLE_DURABLE_USAGE_CONTROLS=true` in deployed envs and add scheduled cleanup/alerts. |
| S1-05 | P1 | DB correctness | Complete: deployed DB config, connectivity, and Alembic head now fail closed. | `backend/app/core/database_readiness.py`; `backend/tests/test_database_readiness.py`; `docs/stage-1-s1-05-database-fail-fast-readiness-report.md`. | Remaining risk is operational DB provisioning/backup/rollback, not silent local/mock fallback. | Deployment profile decision. | Done; deployed readiness/startup fails for missing, unavailable, unmigrated, behind, or unknown-revision DB. |
| S1-06 | P1 | Live-provider gates | Real provider rollout remains no-go beyond guarded scaffolding. | Provider guards and templates disable live LLM/vector/POI/routing/ticketing/TTS. | Unexpected cost, unreliable output, or broken external dependencies. | Provider rollout decision, budgets, observability. | One provider has staged rollout plan, smoke tests, budget ceiling, rollback, and monitoring. |
| S1-07 | P2 | Observability | Logs/readiness exist, but no external retention, metrics, alerts, or tracing. | `observability.py`, `/api/readiness`; no monitoring config found. | Production incidents are hard to detect/debug. | Hosting/monitoring target. | Error reporting, metrics, request IDs, retention, and alert thresholds documented and wired. |
| S1-08 | P2 | Persistence integrity | Missing POI stops are silently dropped when saving itinerary models. | `database_repository.itinerary_to_model()`. | Itineraries can lose stops without explicit failure. | Desired validation behavior. | Missing POI references fail loudly or are handled explicitly with regression tests. |
| S1-09 | P2 | CI/CD | No checked-in CI workflow was found. | No `.github/workflows` in repo snapshot. | Quality gates remain manual. | Final command set and environment setup. | CI runs backend tests, frontend tests/typecheck/build, and secret-template checks. |
| S1-10 | P2 | Frontend auth/session | PLU-02 local implementation complete; staging proof blocked. | `frontend/src/services/authService.ts`, `frontend/src/main.ts`, `frontend/src/components/auth/AuthBootstrap.vue`, `frontend/src/views/AuthCallbackView.vue`, Auth0 tests. | Real Auth0 tenant/app values and staging E2E remain required before production users. | Auth0 staging/prod provisioning and deployed origins. | Real staging login/callback/token/session/logout and `/api/me` E2E pass. |

## Identity And Authorization Architecture

- Identity source: production identity should come from a managed OIDC/JWT provider. Local/test identity may use explicit `dev:` bearer tokens only outside deployed environments.
- Backend verification: managed JWTs are validated server-side by issuer, audience, algorithms, and JWKS/provider metadata. JWKS calls remain subject to the external-call gate.
- User mapping: `/api/me` syncs verified token claims into Litinerary user profiles through `sync_user_from_current_user()`.
- Authorization: user-owned profile, preference, bookmark, review, and recommendation routes must enforce owner/admin server-side. Public catalog and public itinerary browsing remain anonymous.
- Itinerary access: public repository itineraries are anonymous and ownerless. Subscriber/private itineraries are owned by the verified backend `CurrentUser`; private/unlisted detail and narration are owner/admin only. Client-supplied user IDs, owner IDs, or itinerary IDs are not sufficient to read, bookmark, or review another user's private itinerary.
- Development mode: unauthenticated dev fallback is allowed only in development/test-like environments and is ignored in deployed environments.
- Failure behavior: anonymous user-feature requests return 401; malformed/invalid/expired credentials return 401; cross-user access returns 403.
- Testing: keep negative tests for no credentials, invalid credentials, dev-token rejection in deployed envs, owner access, admin access, and cross-user denial.

## S1-02 Environment Authentication Matrix

| Environment | Auth behavior | Dev tokens allowed? | Managed JWT configuration required? | Startup behavior if incomplete |
| --- | --- | ---: | ---: | --- |
| `development` | Auth optional by default; dev provider supported for local work. | Yes, only for local/dev-provider paths. | No, unless a non-dev provider is selected. | Passes with local defaults. |
| `test` | Auth optional by default; deterministic mock/offline testing. | Yes, only for explicit test/dev-provider paths. | No, unless a managed-auth test config is selected. | Passes with test/dev defaults. |
| `internal` | Managed auth required. | No. | Yes. | Fails fast with missing variable names. |
| `beta` | Managed auth required. | No. | Yes. | Fails fast with missing variable names. |
| `staging` | Managed auth required. | No. | Yes. | Fails fast with missing variable names. |
| `production` | Managed auth required. | No. | Yes. | Fails fast with missing variable names. |

Frontend auth state after S1-02: backend ready, but frontend integration is
incomplete and provider decision is required. The frontend can attach bearer
tokens and hydrate `/api/me`; PLU-02 adds the Auth0 provider SDK/login/session
flow, still blocked on real Auth0 staging resources for E2E proof.

## Newly Discovered Issues

| ID | Priority | Issue | Evidence | Disposition |
|---|---|---|---|---|
| N1 | P2 | Fixed repo-wide pytest basetemp cannot be used by concurrent pytest processes. | Parallel focused pytest invocations collided on `tests/.artifacts/pytest-tmp`. | Documented validation commands should run backend pytest sequentially unless each command supplies a unique `--basetemp`. |
| N2 | P3 | The footer mojibake finding in the earlier re-onboarding report is stale. | Current footer source renders correct arrow/copyright characters despite terminal mojibake in docs. | Documentation drift only. |
| N3 | P2 | Alembic logging configuration can disable pre-existing app loggers if `disable_existing_loggers` is left at its default. | Full pytest initially failed three observability caplog tests after the new migration test ran. | Fixed in `backend/migrations/env.py`; full pytest now passes. |

## Architecture Decisions

- User-owned routes fail closed in deployed environments, independent of `AUTH_REQUIRED_FOR_USER_FEATURES`.
- Do not trust client-supplied path user IDs as authentication in beta/staging/production/internal profiles.
- Use a provider-neutral managed JWT/OIDC backend contract until the actual hosted auth vendor is selected. Deployed environments require `ENABLE_AUTH=true`, a non-`dev` provider label, issuer, audience, production algorithms, JWKS/provider metadata, user-feature auth, no dev fallback, and auth metadata external-call allowance.
- Readiness provider entries now report provider-scoped external-call allowance. Managed auth may show external calls allowed in deployed profiles, while disabled product providers remain `externalCallsAllowed=false`.
- Public repository generation/list/adaptation stays intentionally anonymous and public; private subscriber itineraries stay owner/admin-only and are excluded from public repository operations.
- Keep the deployment readiness harness production-shaped; use a Codex-specific split procedure for the sandbox launch-context limitation instead of overfitting script behavior to Codex.
- Keep pytest artifacts under `tests/.artifacts`, but avoid the historical locked `tests/.artifacts/tmp` cache/basetemp paths for normal pytest.
- Deployed database startup checks are intentionally stricter than local/test: deployed environments require explicit DB config, reachable DB, and Alembic head before serving traffic; local/test keep deliberate SQLite and schema-creation shortcuts.
- Readiness uses Alembic metadata for migration state and safe labels for DB diagnostics; it does not run migrations or expose connection URLs.

## Validation Log

| Command | Result |
|---|---|
| `git status --short --branch --ignored` | Passed; no permission-denied warnings after artifact cleanup. |
| `python -m pytest backend\tests\test_auth_foundation.py -q` | Passed; 19 passed, 1 warning. |
| `python -m pytest backend\tests\test_auth_foundation.py::test_deployed_auth_startup_validation_fails_when_config_incomplete backend\tests\test_auth_foundation.py::test_deployed_auth_startup_validation_fails_when_env_not_allowlisted backend\tests\test_auth_foundation.py::test_valid_deployed_auth_startup_validation_passes_without_network backend\tests\test_auth_foundation.py::test_development_auth_startup_allows_dev_provider backend\tests\test_auth_foundation.py::test_test_auth_startup_allows_dev_provider_without_external_services -q` | Passed; 8 passed, 1 warning. |
| `python -m pytest backend\tests\test_auth_foundation.py backend\tests\test_environment_guards.py backend\tests\test_external_call_policy.py backend\tests\test_observability.py backend\tests\test_offline_integration_readiness.py -q` | Passed; 80 passed, 3 warnings. |
| `python -m scripts.validate_beta_config --profile beta` with representative beta managed-auth placeholders | Passed; `errors: []`, auth provider configured, product external-call guard blocked. |
| `python -m pytest backend\tests\test_database_seed.py -q` | Passed; 3 passed, 1 warning. |
| `python -m pytest -q` | Passed; 305 passed, 3 skipped, 10 warnings. |
| `python -m pytest backend\tests\test_itinerary_ownership.py backend\tests\test_itinerary_ownership_migration.py -q` | Passed; 8 passed, 3 warnings. |
| `python -m pytest backend\tests\test_mvp_api.py backend\tests\test_model_metadata_migrations.py backend\tests\test_negative_security_paths.py backend\tests\test_subscriber_chat.py backend\tests\test_auth_foundation.py -q` | Passed; 71 passed, 1 warning. |
| `python -m pytest -q --basetemp=tests\.artifacts\tmp\pytest-s1-03-full-fixed` | Passed; 313 passed, 3 skipped, 12 warnings. |
| Temp DB migration/seed for S1-03 | Passed; Alembic head `20260815_0008`, seed loaded 5 destinations, 10 books, 13 POIs, 2 itineraries. |
| Temporary backend runtime S1-03 ownership validation | Passed; `/api/health=ok`, `/api/readiness=ready`, owner private detail `200`, other user `404`, anonymous `404`, public list count 2. |
| `npm.cmd test -- src/test/frontendApiIntegration.test.ts src/services/apiContract.integration.test.ts` from `frontend/` | Passed; 2 files, 9 tests. |
| `npm.cmd run typecheck` from `frontend/` | Passed. |
| `npm.cmd test` from `frontend/` | Passed; 13 files, 65 tests. |
| `npm.cmd run build` from `frontend/` | Passed; `vue-tsc --noEmit && vite build` completed. |
| Temporary backend startup on `127.0.0.1:8765` | Passed; `/api/health=ok`, `/api/readiness=ready`. |
| `venv\Scripts\python.exe -m pytest backend\tests\test_usage_policy.py -q` | Passed; 24 passed, 2 warnings. |
| `venv\Scripts\python.exe -m pytest backend\tests\test_itinerary_ownership_migration.py -q` | Passed; 2 passed, 3 warnings. |
| `venv\Scripts\python.exe -m pytest backend\tests\test_provider_contracts.py::test_provider_error_normalizes_error_payload backend\tests\test_usage_policy.py backend\tests\test_itinerary_ownership_migration.py -q` | Passed; 27 passed, 4 warnings. |
| `npm.cmd test -- src/services/apiClient.test.ts` from `frontend/` | Passed; 1 file, 5 tests. |
| `npm.cmd test -- src/services/apiContract.integration.test.ts src/services/apiClient.test.ts` from `frontend/` | Passed; 2 files, 10 tests. |
| `npm.cmd run typecheck` from `frontend/` | Passed after S1-04 changes. |
| `venv\Scripts\python.exe -m py_compile backend\app\services\usage_policy.py backend\app\core\config.py backend\app\core\readiness.py backend\app\main.py backend\scripts\validate_beta_config.py backend\tests\test_usage_policy.py` | Passed. |
| `venv\Scripts\python.exe -m scripts.validate_beta_config --profile beta` with representative beta managed-auth placeholders and `ENABLE_DURABLE_USAGE_CONTROLS=true` | Passed; `errors: []`, auth provider configured, product external-call guard blocked. |
| `venv\Scripts\python.exe -m pytest -q` | Passed; 324 passed, 3 skipped, 13 warnings. |
| `npm.cmd test` from `frontend/` | Passed after S1-04 changes; 13 files, 66 tests. |
| `npm.cmd run build` from `frontend/` | Passed after S1-04 changes; `vue-tsc --noEmit && vite build` completed. |
| S1-04 temp DB migration/seed | Passed; Alembic head `20260815_0009`, seed loaded 5 destinations, 10 books, 13 POIs, 2 itineraries, usage counter rows 0. |
| Temporary backend runtime S1-04 durable validation | Passed; `/api/health=ok`, `/api/readiness=ready`, durable controls `true`, first generation `200`, second generation `429`, `Retry-After=26820`. |
| `git diff --check` | Passed; only line-ending warnings reported. |
| `git status --short --branch` | Passed; branch `main...origin/main`, dirty tree includes S1-01/S1-02/S1-03/S1-04 tracked and untracked work. |
| `venv\Scripts\python.exe -m pytest backend\tests\test_database_readiness.py backend\tests\test_observability.py::test_readiness_endpoint_reports_database_and_provider_modes backend\tests\test_offline_integration_readiness.py::test_offline_readiness_defaults_are_mock_only_and_secret_free backend\tests\test_offline_integration_readiness.py::test_deployed_profiles_do_not_enable_live_llm_without_explicit_gates -q` | Passed; 31 passed, 30 warnings. |
| `venv\Scripts\python.exe -m py_compile backend\app\core\config.py backend\app\core\database.py backend\app\core\database_readiness.py backend\app\core\readiness.py backend\app\main.py backend\scripts\validate_beta_config.py backend\tests\test_database_readiness.py` | Passed. |
| PowerShell parser tokenization for `scripts\deployment_readiness_check.ps1` and `scripts\beta_dry_run.ps1` | Passed. |
| `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\beta_dry_run.ps1 -SkipTests -SkipFrontendBuild -Port 8776` | Passed; config validation `errors: []`, DB migrated/seeded, backend health/readiness/admin/debug smoke passed, no deployment performed. |
| Runtime unmigrated/unavailable DB validation command | Passed; unmigrated DB returned `status=error`, `migrations=missing`; unavailable DB startup failed closed with sanitized message. |
| S1-05 previous-head migration rehearsal | Passed; upgraded disposable DB from `20260815_0008` to `20260815_0009`, retained 5 destinations, 10 books, 13 POIs, 2 itineraries, usage counters 0. |
| `venv\Scripts\python.exe -m pytest -q --basetemp=tests\.artifacts\tmp\pytest-s1-05-full-$PID` | Passed; 350 passed, 3 skipped, 114 warnings. |
| `npm.cmd run typecheck` from `frontend/` | Passed after S1-05 changes. |
| `npm.cmd test` from `frontend/` | Passed after S1-05 changes; 13 files, 66 tests. |
| `npm.cmd run build` from `frontend/` | Passed after S1-05 changes; `vue-tsc --noEmit && vite build` completed. |
| `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\deployment_readiness_check.ps1 -SkipFrontendBuild -Port 8777` | Backend/profile/migration/server sections passed; frontend focused Vitest step hit the known Codex sandbox process-initial-directory limitation (`Cannot read directory "../../..": Access is denied`). Direct frontend Vitest command from `frontend/` passed. |
| `git diff --check` after S1-05 | Passed; only line-ending warnings reported. |
| `git status --short --branch` after S1-05 | Passed; branch `main...origin/main`, dirty tree includes prior S1 work plus S1-05 changes. Generated backend test artifacts are ignored. |

## Remaining P0/P1 Production Blockers

- P1: Create the owner-approved S1-01 through S1-05 Git checkpoint before PLU-02 begins. Do not commit/push without separate owner authorization.
- P1: Provision Auth0 staging/production tenants/apps and run real staging auth E2E against the existing backend managed-JWT contract and `/api/me` hydration.
- P1: Provision production-like Render infrastructure: frontend/backend hosting, managed PostgreSQL, Render secrets/environment groups, migration path, environment configuration, domain/DNS/TLS, and deployed startup/readiness checks.
- P1: Add GitHub Actions CI/CD quality gates for backend tests, frontend typecheck/tests/build, migration/seed checks, dependency/security scanning, secret hygiene, and post-deploy smoke validation.
- P1: Wire approved production observability and alerting: retained logs, frontend/backend error reporting, uptime checks, readiness/startup alerts, database/Auth0 failures, abnormal 5xx rates, rate/quota exhaustion, and usage-control failures.
- P1: Establish the approved backup, restore, migration rollback, and application rollback procedures with at least one restore rehearsal on a disposable database.
- P1: Fix persistence integrity for missing POI references in saved itinerary stops so core itinerary data cannot be silently truncated.
- P1: Complete a production-like staging rehearsal with Auth0, managed PostgreSQL, Render secrets, migrations, smoke tests, logs, alerts, backup/restore evidence, and rollback proof.
- Post-launch: Live LLM/vector/POI/routing/ticketing/TTS/affiliate rollout is PLU-08 and is not required for initial Production GO.

## PLU-02 Validation Update

- Focused frontend Auth0/auth/API/UX tests: `npm.cmd test -- src/services/authService.test.ts src/views/authUx.test.ts src/stores/authStore.test.ts src/services/apiClient.test.ts src/test/happyPath.smoke.test.ts` passed; 5 files, 18 tests.
- Frontend typecheck: `npm.cmd run typecheck` passed.
- Full frontend/backend/runtime validation for the current PLU-02 working tree is recorded in `docs/plu-02-auth0-frontend-session-integration-report.md`.
- Auth0 staging state: blocked; no real staging domain/issuer, SPA client ID, API audience, callback URL, logout URL, allowed web origin, backend JWKS/metadata values, or staging test user/session path is available in safe repo/environment sources.

## PLU-03 Validation Update

- Dependency-security preflight: initial `npm.cmd audit` reproduced 8 findings (`3 moderate`, `4 high`, `1 critical`). Non-forced `npm.cmd audit fix` remediated compatible transitive findings by updating `brace-expansion` to `2.1.4`, `nanoid` to `3.3.18`, and `postcss` to `8.5.26`.
- Remaining npm audit status: 5 findings (`3 moderate`, `1 high`, `1 critical`) in Vitest/Vite dev-test tooling. These are not production-runtime reachable in the approved Render static-site/backend topology. Removing them requires a semver-major Vitest upgrade and is recommended for PLU-04 CI/security hardening.
- Auth0 attribution: audit findings pre-existed PLU-02; the Auth0 lockfile delta did not introduce the vulnerable packages.
- Render configuration: root `render.yaml` added for separated staging/production backend, frontend static site, Render Postgres, provider-lock env group, Auth0 placeholders, SPA fallback, health check path, and no live product providers.
- Provider disablement: `backend/tests/test_environment_guards.py::test_plu03_staging_auth_allows_only_auth0_external_calls` passed and verifies Auth0 can be the only real/external-call provider in staging.
- Focused frontend Auth0/API/UX tests after dependency/config work: 5 files, 19 tests passed.
- Full frontend validation: typecheck passed; full Vitest passed with 15 files and 75 tests; production build passed.
- Focused backend auth/security/readiness validation: 93 passed, 23 warnings.
- Full backend validation: 351 passed, 3 skipped, 114 warnings.
- Migration/seed validation: Alembic head `20260815_0009`; disposable seed counts were 5 destinations, 10 books, 13 POIs, 2 itineraries, and 0 usage counters.
- Staging config validation: staging-shaped `scripts.validate_beta_config --profile staging` passed with `errors: []`; Auth0 configured as real auth provider and all product providers mock.
- Render preflight: `scripts/cloud_offline_render_preflight.ps1` passed without frontend build. The `-RunFrontendBuild` and full deployment-readiness script frontend subprocesses hit the known Codex sandbox `Cannot read directory "../../..": Access is denied` limitation; direct frontend validation from `frontend/` passed.
- External provisioning: Render services, Render Postgres, Render secrets/env groups, staging origins, and Auth0 resources remain owner-blocked and were not fabricated.

## Next Task

PLU-04: GitHub Actions CI/CD, dependency/security scanning, secret hygiene, release packaging, and post-deploy smoke gates.

Prerequisite: preserve the PLU-02/PLU-03 working tree or create an owner-authorized local checkpoint first. Do not commit or push without separate authorization.

Definition of done: checked-in CI gates run backend tests, frontend typecheck/tests/build, migration/seed checks, dependency/security checks, secret hygiene checks, and prepare post-deploy smoke validation without requiring live product providers.

## Production Launch Gates

| Gate | Name | Must Pass Before |
|---|---|---|
| PLG-01 | Product and platform decisions locked | COMPLETE: `docs/production-decisions.md`. |
| PLG-02 | Auth0 production auth completion | Any public traffic reaches user-specific features. |
| PLG-03 | Infrastructure, CI/CD, observability, and backup readiness | Staging is treated as production-like. |
| PLG-04 | Persistence integrity and security/privacy hardening | Launch qualification starts. |
| PLG-05 | Production-like staging rehearsal | Production GO decision. |
| PLG-06 | Post-launch live-provider gate | Not required for initial Production GO; required before any later live product-provider traffic. |

## Human Decisions Required

| Decision | Needed Before |
|---|---|
| Initial production product scope, including mock-only versus live-provider launch stance. | APPROVED: narrow v1, no live product providers. |
| Managed auth provider, tenant/project, client, issuer, audience, and claim mapping. | APPROVED: Auth0 with separate staging/prod tenants; concrete tenant/app values to provision in PLU-02. |
| Production hosting target, managed database target, secrets/config store, domain, DNS, and TLS ownership. | APPROVED: Render frontend/backend, managed PostgreSQL/Render Postgres preferred, Render secrets, Render TLS; literal domain/DNS values pending provisioning. |
| Observability/log/error-reporting/uptime-alerting target and incident notification owner. | APPROVED: minimal hosted observability; Project Owner role owns incidents until delegated. |
| Backup retention, RPO/RTO, restore-test expectations, and rollback approval owner. | APPROVED: paid managed PostgreSQL with PITR where available, daily logical backup/export, 30-day external retention, restore rehearsal, RPO 24h, RTO 4h. |
| Privacy/data handling posture for accounts, chat sessions, retention, deletion/export, analytics, external providers, and support. | APPROVED: manual deletion support process, logs 30 days, usage counters 90 days, no v1 chat policy, no product analytics. |
| Whether private itinerary CRUD, publish/unpublish, and unlisted sharing are v1 requirements or post-launch roadmap. | APPROVED: post-launch. |
| Launch quotas, abuse thresholds, provider budgets, and support/incident ownership. | APPROVED: production-template limits, live product-provider cost `$0`, Project Owner role ownership. |

## Required External Resources

| Resource | Required For | Status |
|---|---|---|
| Auth0 staging/production tenants/apps | Real login, token lifecycle, JWKS/metadata, callback/logout URLs. | Approved; provision in PLU-02. |
| Render frontend hosting | Public frontend deployment. | Approved; provision in PLU-03. |
| Render backend hosting | Public API deployment. | Approved; provision in PLU-03. |
| Managed PostgreSQL / Render Postgres preferred | Production persistence and migration readiness. | Approved; provision in PLU-03. |
| Render secret/config store | DB/auth/provider secrets, CORS, quotas, budgets, deploy profiles. | Approved; configure in PLU-03. |
| Domain/DNS/TLS | Public URL, HTTPS, auth callback origins. | Hostname pattern approved; literal domain/DNS values must be supplied before GO; Render TLS approved. |
| Monitoring/error reporting/uptime service | Logs, application errors, readiness/DB/Auth0/usage alerts. | Approved architecture; configure in PLU-05. |
| GitHub Actions | Automated test/build/migration/security/smoke gates. | Approved; repo lacks checked-in workflow and setup remains PLU-04. |
| Backup/restore facility | Managed DB backups, logical exports, snapshots, restore rehearsal. | Approved policy; implement/rehearse in PLU-06. |
| Live provider accounts | LLM/vector/POI/routing/ticketing/TTS/affiliate behavior. | Post-launch; not required for initial Production GO. |

## Remaining Implementation Units

| Unit | Scope | Status |
|---|---|---|
| PLU-01 | Product/platform decision record and launch-scope lock. | Complete. |
| PLU-02 | Managed Auth0 provider provisioning and frontend login/session integration. | Partially complete; local implementation/tests done, blocked on real Auth0 staging provisioning/E2E. |
| PLU-03 | Render infrastructure, Render secrets, managed PostgreSQL, migrations, and environment setup. | Recommended next. |
| PLU-04 | GitHub Actions CI/CD, dependency/security scanning, secret hygiene, release packaging, and post-deploy smoke. | Pending PLU-03. |
| PLU-05 | Observability, monitoring, alerts, incident ownership, and Render usage-counter cleanup scheduling/runbook. | Pending PLU-03. |
| PLU-06 | Backup/restore, migration rollback, app rollback, security headers/CSP, and privacy launch controls. | Pending PLU-03. |
| PLU-07 | Persistence-integrity fix and production-like staging rehearsal with GO/NO-GO evidence. | Pending PLU-02 through PLU-06. |
| PLU-08 | First live-provider rollout gate. | Post-launch; not required for initial Production GO. |

## Production GO Criteria

- Product owner has approved the initial public product scope and the mock-only versus live-provider stance.
- Managed auth works end to end in staging and production configuration rejects dev auth/fallback.
- Production infrastructure is provisioned with managed DB, secrets, domain/DNS/TLS, and deployment profiles.
- Alembic migrations are at head, seed data is intentional, startup fails closed, and readiness reports healthy DB/auth state.
- CI/CD passes backend tests, frontend tests/typecheck/build, migration/seed checks, dependency/security checks, and secret hygiene checks.
- Observability has retained logs, error reporting, uptime checks, readiness alerts, DB/auth alerts, and usage-budget/provider alerts where applicable.
- Backup, restore, migration rollback, and app rollback have documented procedures and at least one successful restore rehearsal.
- Persistence-integrity regression for missing POI stops is fixed and tested.
- Production-like staging rehearsal passes smoke tests, auth tests, migration checks, alert checks, backup/restore proof, and rollback proof.
- Human GO approval is recorded.

## Production NO-GO Criteria

- Auth provider, hosting, database, secrets, monitoring, domain, backup, or product-scope decisions are unresolved.
- Frontend auth still depends on dev/manual token injection or lacks session persistence/refresh/logout.
- Production uses SQLite, an unmigrated database, mock persistence fallback, or unknown Alembic revision.
- CI/CD is absent or required backend/frontend/migration/security gates are manual-only.
- Logs, error reporting, uptime/readiness alerts, database/auth alerts, or incident ownership are missing.
- Backup/restore or rollback has not been rehearsed.
- Saved itineraries can silently lose stops because missing POI references are ignored.
- A live cost-bearing provider is enabled without staged proof, budgets, monitoring, rollback, and owner approval.
- Security/privacy launch decisions are missing for user data, external providers, retention, deletion, CSP/security headers, or support ownership.
