# Stage 1 S1-05 Database Fail-Fast and Migration Readiness Report

Date: 2026-08-15

## Executive Summary

S1-05 is complete. Deployed Litinerary environments now have an explicit database contract: `LITINERARY_DATABASE_URL` must be configured, valid, reachable, and migrated to the current Alembic head before the application accepts traffic. `/api/readiness` now reports safe database metadata and refuses to report ready for invalid configuration, failed connectivity, missing migration metadata, behind migrations, or unknown migration revisions.

No live providers, CI/CD, private itinerary CRUD/sharing, full observability platform, or usage-counter cleanup scheduler work was absorbed into S1-05. Those items were not ignored; they were deliberately left out because the prompt's scope boundary reserves them for separate production-readiness tasks.

## Starting State

The work began on branch `main...origin/main` at commit `86a40dc90ff7dcfd4497ef1da190dc2da35e73ca`. The working tree already contained prior S1-01 through S1-04 changes and untracked reports/migrations. No reset, clean, stash, revert, or overwrite of unrelated work was performed.

Required prior reports and progress documents were read first:

- `docs/stage-1-s1-04-durable-usage-controls-report.md`
- `docs/stage-1-s1-03-itinerary-ownership-report.md`
- `docs/stage-1-s1-02-managed-auth-report.md`
- `docs/production-development-progress.md`
- `docs/re-onboarding-production-readiness-review.md`

## Existing Database Architecture

Before S1-05, `backend/app/core/database.py` created the SQLAlchemy engine from `settings.database_url`, defaulting to `sqlite:///./litinerary.db`. `init_db()` called `Base.metadata.create_all`, which was useful locally but unsafe as a deployed schema contract. Alembic lived under `backend/migrations`, with a single current head, `20260815_0009`.

Repository selection was split between database-backed repositories and `mock_repository`. The previous `_use_database(db)` decision used seed-data availability and could return false on `OperationalError`, which meant deployed profiles could fall back to mock data if the database was empty or schema checks failed.

Readiness previously executed a lightweight DB query but did not inspect Alembic state. Startup validation already enforced S1-02 managed auth and S1-04 durable usage controls, but it did not fail on unreachable, unmigrated, behind, or unknown-revision deployed databases.

## Environment / Database Matrix

| Environment | Intended persistence | Current DB requirement | Current fallback | Migration requirement | Production-safe? |
| ----------- | -------------------- | ---------------------- | ---------------- | --------------------- | ---------------- |
| development | Local SQLite or explicit developer DB | DB URL optional; default SQLite allowed | Mock/local fallback remains deliberate | Alembic preferred; `create_all` allowed for local convenience | Yes for local only |
| test | Disposable SQLite/test DB | Explicit temp DB supported; default test/local behavior allowed | Mock/test fallback remains deliberate | Disposable DB migrations covered by tests; `create_all` allowed in test fixtures | Yes for tests only |
| internal | Explicit deployed DB | `LITINERARY_DATABASE_URL` required and valid | No mock/local fallback when DB session exists | Must be at Alembic head | Yes |
| beta | Explicit deployed DB | `LITINERARY_DATABASE_URL` required and valid | No mock/local fallback when DB session exists | Must be at Alembic head | Yes |
| staging | Explicit deployed DB | `LITINERARY_DATABASE_URL` required and valid | No mock/local fallback when DB session exists | Must be at Alembic head | Yes |
| production | Explicit deployed DB | `LITINERARY_DATABASE_URL` required and valid | No mock/local fallback when DB session exists | Must be at Alembic head | Yes |

No database vendor requirement was invented. The code validates explicit configuration and Alembic state without requiring PostgreSQL, because the repository does not yet establish a production vendor.

## Unsafe Fallbacks Found

| Fallback | Classification | S1-05 outcome |
| --- | --- | --- |
| Missing `LITINERARY_DATABASE_URL` fell back to `sqlite:///./litinerary.db` | Deployed-unsafe, local-intended | Deployed config validation now rejects missing/default fallback |
| `database_has_seed_data()` returning false on DB operational errors could make `mock_repository` use mock data | Deployed-unsafe | Deployed `_use_database(db)` now stays database-backed when a DB session exists |
| `/api/readiness` used DB connectivity only | Deployed-unsafe | Readiness now reports config, connectivity, and migration status |
| `init_db()` used `create_all()` | Local/test-intended but deployed-unsafe | `init_db()` now raises in deployed environments |
| Seed/import/export/validate scripts called `init_db()` | Local/test-intended but deployed-unsafe | Scripts skip schema creation in deployed profiles; `reset_dev_db` is blocked in deployed profiles |
| Alembic migration was not required before app startup | Deployed-unsafe | Deployed startup now validates Alembic head |

## Deployed Database Contract

For `internal`, `beta`, `staging`, and `production`:

- `LITINERARY_DATABASE_URL` must be explicitly set.
- The URL must parse as a supported SQLAlchemy URL.
- The default local SQLite fallback is forbidden.
- The database must accept a minimal SQLAlchemy connectivity query.
- The database must contain Alembic metadata.
- The database revision set must match the repository's Alembic head set.
- Unknown revisions are non-ready.
- Migrations remain an explicit deployment operation.
- Seed/reference data is not a startup requirement, because the app can legitimately operate with empty business data, but seed validation remains part of beta/deployment rehearsal.

## Configuration Validation

`backend/app/core/config.py` now tracks whether `LITINERARY_DATABASE_URL` was explicitly configured and exposes:

- `database_configuration_validation_errors()`
- `safe_database_dialect()`

Startup/config errors name `LITINERARY_DATABASE_URL` but do not print passwords, full URLs, or connection paths.

## Database Connectivity Model

`backend/app/core/database_readiness.py` executes a lightweight `SELECT 1` through SQLAlchemy. It distinguishes healthy connectivity from SQLAlchemy failures, rolls back failed sessions, and never performs destructive operations or migrations as part of the check.

## Migration-Head Validation

Runtime migration validation uses Alembic `ScriptDirectory` metadata to derive expected heads and known revisions. It detects:

- current head;
- no `alembic_version`;
- empty `alembic_version`;
- one migration behind;
- unknown revision;
- DB query errors while inspecting migration state.

The current graph has a single head: `20260815_0009`.

## Startup vs Readiness Semantics

| Condition | Startup | Health | Readiness |
| --- | --- | --- | --- |
| Valid config, migrated DB | Starts | `ok` | `ready` |
| DB URL missing | Fails config/startup | Not served if process cannot start | Non-ready if evaluated |
| DB unreachable | Fails startup in deployed envs | Not served if process cannot start | Non-ready if evaluated |
| Credentials invalid | Fails startup in deployed envs | Not served if process cannot start | Non-ready if evaluated |
| Empty/unmigrated DB | Fails startup in deployed envs | Not served if process cannot start | Non-ready if evaluated |
| DB one migration behind | Fails startup in deployed envs | Not served if process cannot start | Non-ready |
| Unknown migration revision | Fails startup in deployed envs | Not served if process cannot start | Non-ready |
| Local SQLite fallback in deployed env | Fails config/startup | Not served if process cannot start | Non-ready if evaluated |

## Health vs Readiness Semantics

`/api/health` remains a liveness endpoint and returns process health only. `/api/readiness` is the dependency and traffic-readiness endpoint. This keeps temporary dependency outages from being confused with process death, while preventing a deployed instance from advertising itself ready when persistence is invalid.

## Mock / SQLite Fallback Protection

Development and test can still use deliberate SQLite/mock paths. Deployed environments cannot silently fall back to the local SQLite default, mock repository state, or in-memory usage counters. When a DB session exists in deployed mode, repository behavior stays database-backed and fails through the database path instead of substituting bundled mock persistence.

## Durable Usage-Control Dependency

S1-04 durable usage controls remain required in deployed environments. Because deployed startup now validates the shared relational database before serving traffic, DB failure cannot cause usage enforcement to revert to unlimited or in-memory behavior. Readiness includes the database dependency and usage-control mode.

## Itinerary Persistence Dependency

S1-03 owner/admin and public/private itinerary semantics remain database-persistence-safe. Private/user functionality no longer silently shifts to mock state in deployed profiles when seed/schema probing fails. Unauthorized private itinerary behavior remains governed by the S1-03 database-backed access model.

## Migration Deployment Workflow

Production-like deployment order is now:

1. Configure `LITINERARY_DATABASE_URL` through deployment secrets/environment.
2. Back up the target database before migrations.
3. Run `alembic upgrade head` as an explicit deployment/pre-start operation.
4. Verify the database is at the current Alembic head.
5. Seed only approved non-production reference data where intended.
6. Start or restart the application.
7. Confirm `/api/health` returns `ok`.
8. Confirm `/api/readiness` returns `ready`, database connectivity `ok`, and migrations `current`.

Rollback should not be automated blindly. Migration files include downgrade hooks, but production rollback requires backup/restore planning and usually an app-version rollback paired with a database restore or reviewed downgrade.

## Environment Template Changes

Updated templates document the DB contract:

- `.env.example`: local SQLite remains a development default.
- `.env.test.example`: test SQLite remains deterministic.
- `.env.beta.example`: now uses a managed beta/staging DB placeholder and states Alembic must run before boot.
- `.env.production.example`: now uses a managed production DB placeholder and states Alembic must run before boot.

Only placeholders were added. No real credentials were added.

## Files Changed

Primary S1-05 files:

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
- `.env.example`
- `.env.test.example`
- `.env.beta.example`
- `.env.production.example`
- `.gitignore`
- `docs/api-contract.md`
- `docs/production-readiness.md`
- `docs/beta-deployment-runbook.md`
- `docs/deployment-readiness-harness.md`
- `docs/production-development-progress.md`

## Focused Test Results

| Command | Result |
| --- | --- |
| `venv\Scripts\python.exe -m pytest backend\tests\test_database_readiness.py backend\tests\test_observability.py::test_readiness_endpoint_reports_database_and_provider_modes backend\tests\test_offline_integration_readiness.py::test_offline_readiness_defaults_are_mock_only_and_secret_free backend\tests\test_offline_integration_readiness.py::test_deployed_profiles_do_not_enable_live_llm_without_explicit_gates -q` | 31 passed, 30 warnings |
| `venv\Scripts\python.exe -m py_compile backend\app\core\config.py backend\app\core\database.py backend\app\core\database_readiness.py backend\app\core\readiness.py backend\app\main.py backend\scripts\validate_beta_config.py backend\tests\test_database_readiness.py` | Passed |
| PowerShell parser tokenization for `scripts\deployment_readiness_check.ps1` and `scripts\beta_dry_run.ps1` | Passed |

## Complete Validation Results

| Command | Result |
| --- | --- |
| `venv\Scripts\python.exe -m pytest -q --basetemp=tests\.artifacts\tmp\pytest-s1-05-full-$PID` | 350 passed, 3 skipped, 114 warnings |
| `npm.cmd run typecheck` from `frontend/` | Passed |
| `npm.cmd test` from `frontend/` | 13 files passed, 66 tests passed |
| `npm.cmd run build` from `frontend/` | Passed |
| `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\beta_dry_run.ps1 -SkipTests -SkipFrontendBuild -Port 8776` | Passed; config validation, migration/seed, health/readiness/admin/debug smoke passed |
| `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\deployment_readiness_check.ps1 -SkipFrontendBuild -Port 8777` | Backend/profile/migration/server sections passed; frontend Vitest step hit the known Codex sandbox launch limitation. Direct frontend Vitest from `frontend/` passed. |
| `git diff --check` | Passed with line-ending warnings only |
| `git status --short --branch` | Reviewed; prior S1 work preserved and S1-05 changes present |

## Migration / Seed Results

Disposable previous-head rehearsal:

- Previous revision: `20260815_0008`.
- Resulting revision: `20260815_0009`.
- Seed before current-head upgrade: 5 destinations, 10 books, 13 POIs, 2 itineraries.
- Counts after current-head upgrade: 5 destinations, 10 books, 13 POIs, 2 itineraries, 0 usage counter rows.
- S1-03 ownership schema and S1-04 usage-control schema remained present through the current head.

## Runtime Valid-DB Results

`scripts\beta_dry_run.ps1 -SkipTests -SkipFrontendBuild -Port 8776` started the backend against a disposable migrated beta SQLite database. Results:

- startup succeeded;
- `/api/health` returned `ok`;
- `/api/readiness` returned `ready`;
- readiness reported database configured, connectivity `ok`, and migrations `current`;
- admin/dev routes remained disabled as expected;
- product providers remained mock/fake.

## Runtime Unmigrated-DB Results

A disposable unmigrated deployed-style SQLite database was evaluated through the readiness code without running migrations or schema creation.

Result:

```text
unmigrated_status=error migrations=missing connectivity=ok
```

No fallback repository was used and no schema was created or upgraded by readiness.

## Runtime Unavailable-DB Results

A deployed-style startup validation was run against an intentionally invalid SQLite path under a missing directory.

Result:

```text
unavailable_failed=True sanitized=True message=Database is not ready for APP_ENV=staging: connectivity=error migrations=not_checked.
```

The failure was closed and did not expose the database filename.

## Security Review

- No database URLs or credentials are exposed in readiness output.
- Startup errors name the relevant variable but avoid printing the full URL.
- Deployed `create_all()` is blocked.
- Readiness never runs migrations.
- Request paths do not run migrations.
- Product-provider live flags remain disabled in deployment harnesses.
- S1-02 auth, S1-03 ownership, and S1-04 durable usage guarantees were preserved.
- `git diff --check` passed with line-ending warnings only.
- No database files were staged or made intentionally trackable.

## Remaining Database / Deployment Gaps

- Provision the actual hosted database for beta/staging/production.
- Define backup cadence, restore drills, and migration rollback playbooks against provider snapshots.
- Add external readiness/DB alerting and dashboards.
- Add scheduled cleanup for expired `usage_limit_counters`.
- Decide whether production seed/reference data should be applied by release tooling or a separate controlled admin operation.

## Newly Discovered Production Risks

- Seed and seed-management scripts still assumed local `init_db()` semantics. S1-05 fixed deployed behavior by requiring Alembic-first data operations.
- Running Vitest from the long PowerShell deployment harness still hits the previously documented Codex sandbox process-initial-directory limitation, even though direct frontend commands from `frontend/` pass.
- Backend-local pytest runs can create `backend/tests/.artifacts`; `.gitignore` now excludes that generated path.

## Production Impact

A deployed Litinerary instance can no longer appear production-ready while its required persistence layer is missing, incorrect, unreachable, or behind the application schema. Local development remains ergonomic, but deployed environments now fail closed before traffic.

## Next Recommended Task

S1-06: establish the first safe live-provider rollout gate.

## Prompt Compliance Matrix

| # | Requirement | Status | Evidence |
| - | ----------- | ------ | -------- |
| 1 | Read current project state | DONE | Read required S1/progress/re-onboarding docs, inspected branch/status/commit/history and DB/deployment docs before edits. |
| 2 | Preserve S1-02/S1-03/S1-04 guarantees | DONE | Focused compatibility tests passed; auth, ownership, and durable usage semantics remain enforced. |
| 3 | Reconstruct database architecture | DONE | Inspected SQLAlchemy engine/session, config, models, repositories, startup, readiness, Alembic, seeds, scripts, templates, and tests. |
| 4 | Produce environment/database matrix | DONE | Matrix included in this report with repository-evidence-based deployed/local distinctions. |
| 5 | Identify silent fallback behavior | DONE | Unsafe fallback table documents default SQLite, mock repository fallback, readiness-only ping, and `create_all`. |
| 6 | Determine deployed DB contract | DONE | Contract requires explicit URL, connectivity, Alembic head, and safe migration workflow without vendor invention. |
| 7 | Separate configuration/runtime failure | DONE | Config errors fail immediately; DB health/migration failures fail startup/readiness without leaking URLs. |
| 8 | Eliminate deployed silent local fallback | DONE | Missing/default DB URL rejected; deployed mock fallback blocked; regression tests added. |
| 9 | Implement deployed DB config validation | DONE | `database_configuration_validation_errors()` identifies `LITINERARY_DATABASE_URL` and sanitizes values. |
| 10 | Verify DB connectivity | DONE | Readiness executes `SELECT 1`, reports connectivity state, rolls back on errors, and does not mutate DB. |
| 11 | Implement migration-head verification | DONE | Alembic `ScriptDirectory` heads and DB `alembic_version` are compared; missing/behind/unknown/current cases tested. |
| 12 | Handle multiple Alembic heads safely | DONE | Expected heads are treated as a set/list from Alembic; current graph verified as single head `20260815_0009`. |
| 13 | Distinguish migration readiness from schema creation | DONE | Deployed `init_db/create_all` blocked; create-all-without-Alembic test reports not ready. |
| 14 | Strengthen `/api/readiness` | DONE | Readiness now reports DB config/connectivity/migrations and is non-ready for deployed DB failures. |
| 15 | Preserve `/api/health` semantics | DONE | Health remains liveness; docs and runtime smoke confirm readiness carries dependency status. |
| 16 | Define deployed startup behavior | DONE | Startup/readiness behavior matrix included and implemented through `validate_database_startup()`. |
| 17 | Ensure durable usage controls cannot bypass DB failure | DONE | Deployed durable controls remain required and shared DB readiness/startup fail closed before traffic. |
| 18 | Verify itinerary ownership persistence dependency | DONE | Deployed repository selection no longer falls back to mock when DB session exists; S1-03 regression suite included in full backend run. |
| 19 | Review mock repository selection | DONE | `_use_database(db)` reviewed and changed to fail closed for deployed environments. |
| 20 | Review automatic DB creation behavior | DONE | `init_db` and seed/admin scripts reviewed; deployed schema auto-create blocked or skipped. |
| 21 | Implement safe DB readiness details | DONE | Readiness exposes configured/dialect/connectivity/migration labels only, not URLs or credentials. |
| 22 | Database URL sanitization | DONE | Startup/readiness failures avoid URL echoing; tests assert secret/path fragments are not leaked. |
| 23 | Environment template updates | DONE | `.env.example`, `.env.test.example`, `.env.beta.example`, and `.env.production.example` updated with placeholders and DB requirements. |
| 24 | Deployment script validation | DONE | `beta_dry_run.ps1`, `deployment_readiness_check.ps1`, and `validate_beta_config.py` now enforce the same DB/durable contract. |
| 25 | Migration deployment workflow | DONE | Workflow documented in this report and deployment/beta/production docs. |
| 26 | Do not auto-migrate production at request time | DONE | Readiness/startup do not upgrade DB; scripts run Alembic explicitly before startup smoke. |
| 27 | Migration rollback considerations | DONE | Backup, downgrade caution, and app-version rollback considerations documented. |
| 28 | Add DB configuration tests | DONE | Development/test/deployed missing/default/malformed/valid config cases covered in `test_database_readiness.py`. |
| 29 | Add migration-state tests | DONE | Current, behind, empty, no Alembic, unknown revision, and connection failure covered with disposable DBs. |
| 30 | Add fallback-regression tests | DONE | Tests cover deployed default SQLite rejection and deployed mock fallback prevention; local fallback remains allowed. |
| 31 | Migration upgrade test | DONE | Disposable DB upgraded from `20260815_0008` to `20260815_0009`; rows and S1-04 table verified. |
| 32 | Seed validation | DONE | Fresh migrated DB seeded with 5 destinations, 10 books, 13 POIs, 2 itineraries and 0 usage history. |
| 33 | Runtime valid-DB scenario | DONE | Beta dry-run smoke started backend with migrated DB; health ok and readiness ready. |
| 34 | Runtime unmigrated-DB scenario | DONE | Readiness evaluator returned `status=error`, `migrations=missing`, `connectivity=ok` without schema mutation. |
| 35 | Runtime unavailable-DB scenario | DONE | Startup validation failed closed with sanitized `connectivity=error migrations=not_checked`. |
| 36 | Run focused tests first | DONE | Focused DB/readiness suite ran before full suites: 31 passed, 30 warnings. |
| 37 | Run complete backend test suite | DONE | Full backend pytest passed: 350 passed, 3 skipped, 114 warnings. |
| 38 | Run complete frontend validation | DONE | `npm.cmd run typecheck`, `npm.cmd test`, and `npm.cmd run build` passed from `frontend/`. |
| 39 | Run migration/seed validation | DONE | Actual Alembic/seed workflow run on disposable DB, previous/current heads and counts recorded. |
| 40 | Verify runtime health/readiness | DONE | Valid DB runtime passed; unmigrated readiness and unavailable startup failed safely outside unit tests. |
| 41 | Git and diff validation | DONE | `git diff --check` and `git status --short --branch` run; diff reviewed for secrets/templates/migrations/S1 preservation. |
| 42 | Update API/readiness docs | DONE | `docs/api-contract.md` updated for health/readiness, DB metadata, migration-head validation, and safe output. |
| 43 | Update deployment docs | DONE | `docs/production-readiness.md`, `docs/beta-deployment-runbook.md`, and `docs/deployment-readiness-harness.md` updated. |
| 44 | Update production-development progress | DONE | `docs/production-development-progress.md` updated with S1-05 status, behavior, validation, risks, and next task. |
| 45 | Create S1-05 report | DONE | This file is `docs/stage-1-s1-05-database-fail-fast-readiness-report.md`. |
| 46 | Include prompt compliance matrix | DONE | This report includes exactly one row for every numbered requirement 1 through 46. |
