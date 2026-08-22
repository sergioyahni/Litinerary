# Stage 1 S1-04 Durable Usage, Rate, and Cost Controls Report

Date: 2026-08-15

Repository: `C:\Users\syahn\source\litinerary`

## Executive Summary

S1-04 is complete. Litinerary now has a centralized usage-control boundary that can use durable database counters for deployed environments and the existing in-memory behavior only for local development and ordinary tests.

The implementation adds UTC minute/day counters, authenticated and anonymous subject scoping, provider request budgets, estimated provider cost budgets, `Retry-After` responses, startup validation for deployed durability, readiness exposure, frontend API error handling for rate limits, an Alembic migration, and regression tests for concurrency, restart persistence, user isolation, provider budget exhaustion, durable-store failure, cleanup, and read-only endpoint availability.

## Starting State

The project already had S1-02 managed-auth startup enforcement and S1-03 itinerary ownership and visibility controls. The usage-control service existed at `backend/app/services/usage_policy.py`, but its source of truth was process-local memory. That meant limits reset on process restart, were split across workers, and could not be trusted for production cost control.

The worktree already contained substantial S1-01/S1-02/S1-03 changes. Those were preserved. I did not reset, clean, stash, or revert unrelated work.

## Existing Usage-Control Architecture

Before S1-04, `ProviderUsageGuard` used `InMemoryProviderUsageStore.records`. Guard methods checked configured limits and appended allowed/blocked records. The guard was already called by itinerary generation, subscriber chat, live LLM scoping, vector operations, POI verification, routing, ticketing, and narration/TTS paths.

The previous architecture was useful as local scaffolding, but it was not production-safe:

- state lived in Python process memory;
- process restart cleared usage;
- multiple backend workers had independent limits;
- concurrent requests were not protected by a shared atomic counter;
- API responses did not consistently expose `Retry-After`;
- frontend errors did not identify `429` or retry timing;
- no durable cleanup/retention model existed.

## Cost/Abuse Operation Inventory

| Operation | Public/Auth | Current limit | Durable? | External cost? | Abuse risk | Production-safe? |
|---|---|---:|---:|---:|---|---|
| Itinerary generation | Anonymous or authenticated | Per-minute and per-day by anonymous/global or verified user | Yes when enabled | Can trigger LLM/routing/POI-like work | High | Yes with durable controls |
| Itinerary adaptation | Anonymous public endpoint | Duration/input bounds plus downstream provider gates | Provider budgets apply to live downstream calls | Can trigger LLM/routing work | Medium | Yes for provider cost; no separate business quota invented |
| Subscriber chat message | Verified subscriber | Per-minute and per-day by verified user | Yes when enabled | Future LLM cost | Medium/high | Yes |
| Subscriber itinerary refinement | Verified subscriber | Subscriber chat quota plus downstream provider gates | Yes when enabled | Future LLM/routing cost | Medium/high | Yes |
| Narration/TTS | Public for accessible itinerary | Provider request budget if real TTS enabled | Yes when enabled | Future TTS cost | Medium | Yes |
| LLM completion | Internal provider path | Input/output bounds, live request ceiling, provider request budget, estimated cost budget | Yes when enabled | Yes if real LLM enabled | High | Yes |
| Vector search/upsert | Internal provider path | Result limit and provider request budget if real vector DB enabled | Yes when enabled | Yes if real vector DB enabled | Medium | Yes |
| POI verification | Admin/development routes and ingestion flow | Batch-size limit and provider request budget if real provider enabled | Yes when enabled | Yes if real provider enabled | Medium | Yes |
| Routing | Generation/adaptation/narration support path | Stop-count limit and provider request budget if real routing enabled | Yes when enabled | Yes if real routing enabled | Medium/high | Yes |
| Ticketing lookup | Provider service path | Per-itinerary request cap and provider request budget if real ticketing enabled | Yes when enabled | Yes if real ticketing enabled | Medium | Yes |
| Affiliate links/search | No current real reachable adapter path | Disabled by provider gates | Not needed for current mock path | Future only | Low current | Not applicable until a real path exists |
| Public reads: destinations, books, public itineraries, public detail | Anonymous/public | No cost quota | Not metered | No current external cost | Low | Safe to remain unmetered |

## Failure Modes of Previous Controls

The prior in-memory store reset on every app restart, was not shared across processes, and could not prevent a scaled deployment from multiplying limits by worker count. It also used event rows as counters, which made it unsuitable for precise reservations and impossible to persist safely.

Failed pre-provider validation could also be charged too early in some flows. S1-04 moved itinerary generation quota after destination/book validation and moved subscriber chat quota after chat/source ownership lookups.

## Durable Store Decision

The repository already has SQLAlchemy, SQLite for local/test, Alembic migrations, and a relational database as the central persistence mechanism. No Redis or other centralized counter service exists in the repository.

S1-04 therefore uses the existing relational database. This avoids adding new infrastructure while providing the needed durability and atomic counter behavior for the current expected scale.

## Usage Identity Model

Authenticated usage identity comes from verified backend `CurrentUser.id`, not from request body or path parameters.

Anonymous itinerary generation uses an application-level anonymous bucket, currently `anonymous-global`, because the app has no trusted proxy/IP/session identity contract. S1-04 deliberately does not trust arbitrary client headers and does not introduce persistent anonymous tracking.

## Rate-Limit Model

Rate limits use fixed UTC minute windows.

Configured rate limits:

- `ANONYMOUS_ITINERARY_GENERATIONS_PER_MINUTE`
- `REGISTERED_USER_ITINERARY_GENERATIONS_PER_MINUTE`
- `SUBSCRIBER_CHAT_MESSAGES_PER_MINUTE`

Rate-limit exhaustion returns `429` with `detail.code=rate_limited` and `Retry-After` when the window end is known.

## Quota Model

Usage quotas use fixed UTC day windows.

Configured quota limits:

- `ANONYMOUS_ITINERARY_GENERATIONS_PER_DAY`
- `REGISTERED_USER_ITINERARY_GENERATIONS_PER_DAY`
- `SUBSCRIBER_CHAT_MESSAGES_PER_DAY`
- `LLM_DAILY_LIVE_REQUEST_CEILING`

Quota exhaustion returns `429` with `detail.code=rate_limited` or `quota_exceeded`, following existing project provider-error conventions.

## Provider Budget Model

Provider budget protection is intentionally provider-neutral:

- `PROVIDER_DAILY_REQUEST_CEILING` limits aggregate daily request units per real provider type.
- `PROVIDER_DAILY_COST_CEILING_USD` limits estimated daily cost when a path has an estimated cost signal.

S1-04 does not fabricate pricing or commercial plans. A nonzero production spend ceiling still requires product/operations approval.

## Atomicity/Concurrency Design

The new `usage_limit_counters` table has one row per subject, action, and UTC window. `DatabaseUsageCounterStore.reserve_units()` inserts the counter row if missing and then runs a conditional atomic update:

`units_used + requested_units <= limit_units`

If the update affects one row, the reservation succeeds. If it affects zero rows, the request is denied. The concurrency test used 12 simultaneous attempts against a limit of 5 and observed exactly 5 successes.

Composite operations such as itinerary generation and subscriber chat reserve both minute and day windows. If a later window rejects, earlier reservations are refunded so retries do not permanently consume a different bucket.

## Retry/Idempotency Semantics

The current request architecture does not expose a stable idempotency key for itinerary generation, provider calls, or chat requests. S1-04 therefore uses pre-provider reservations and avoids charging failed validation where practical.

Residual risk: a client retry after a successful reservation and before receiving a response can count as another logical request. This is bounded by configured limits and should be revisited only if the product introduces request IDs, jobs, or long-running provider workflows.

## Failure/Fail-Closed Semantics

If durable counter storage is unavailable, cost-sensitive work fails closed with `ProviderErrorCode.UNAVAILABLE`, HTTP `503`, and safe metadata. The system does not silently fall back to unlimited local counters in deployed mode.

Startup validation rejects deployed environments when `ENABLE_DURABLE_USAGE_CONTROLS=true` is not set. Readiness exposes durable usage-control configuration and relies on the existing database check for the shared backing dependency.

## Implementation

Key implementation changes:

- Added `UsageLimitCounterModel`.
- Added Alembic migration `20260815_0009_durable_usage_counters`.
- Rebuilt `usage_policy.py` around `UsageCounterStore`, `InMemoryProviderUsageStore`, and `DatabaseUsageCounterStore`.
- Added atomic reservation, refund, cleanup, provider budgets, cost units, UTC windowing, and durable startup validation.
- Added `Retry-After` support to `ProviderError` and FastAPI error responses.
- Added readiness usage-control metadata.
- Moved itinerary generation quota after destination/book validation.
- Moved subscriber chat/refinement quota after session/source access checks.
- Added global test cache hygiene for usage guard state.
- Added frontend `ApiError.isRateLimited` and `retryAfterSeconds`.

## Routes/Providers Protected

Protected routes and paths:

- `POST /api/itinerary/generate`
- `POST /api/itineraries/adapt` through duration bounds and downstream provider gates
- subscriber chat message/refinement routes
- LLM live completion boundary
- vector search/upsert service
- POI verification service
- routing service and OpenRouteService adapter path
- ticketing service
- narration/TTS service

Provider bypass audit:

| Provider/action | Calling path | Usage gate | Budget gate | Can bypass? |
|---|---|---|---|---|
| LLM generation/adaptation | mock repository/live LLM scope/openai-compatible adapter | input/live-call/generation controls | LLM provider request and estimated cost where available | No known production bypass |
| Vector search/upsert | vector service | result/input operation event | real vector provider daily request budget | No known production bypass |
| POI verification | POI verification service/admin routes | batch-size guard | real POI provider daily request budget | No known production bypass |
| Routing | routing service/OpenRouteService adapter | stop-count guard | real routing daily request budget | No known production bypass |
| Ticketing lookup | ticketing service | per-itinerary request cap | real ticketing daily request budget | No known production bypass |
| TTS narration | narration service | operation guard | real TTS daily request budget | No known production bypass |
| Affiliate | mock-only/no real reachable adapter path | provider gates disabled | not applicable until real path exists | No current cost path found |

## Frontend Impact

The frontend API client now parses `Retry-After` into `ApiError.retryAfterSeconds`, marks `ApiError.isRateLimited`, and remains compatible with mocked fetch responses that omit headers. No pricing or upgrade UI was invented.

## Migration/Data Model

Migration `20260815_0009` creates:

- `usage_limit_counters`
- unique constraint on `subject_type`, `subject_key`, `action`, `window_start`
- `ix_usage_limit_counters_subject_action`
- `ix_usage_limit_counters_window_end`

Existing data is preserved. No historical usage is manufactured. Seed leaves usage counters empty.

## Configuration

New or newly enforced configuration:

- `ENABLE_DURABLE_USAGE_CONTROLS`
- `ANONYMOUS_ITINERARY_GENERATIONS_PER_MINUTE`
- `REGISTERED_USER_ITINERARY_GENERATIONS_PER_MINUTE`
- `SUBSCRIBER_CHAT_MESSAGES_PER_MINUTE`
- `PROVIDER_DAILY_REQUEST_CEILING`
- `USAGE_COUNTER_RETENTION_DAYS`

Existing daily quotas and provider cost ceilings remain configurable. Deployed environments require durable controls and positive finite limits. Development/test remain practical with local defaults.

## Security and Privacy Review

Findings and mitigations:

- Client-controlled quota identity: mitigated by using verified `CurrentUser.id` for authenticated users.
- Header spoofing: mitigated by not using arbitrary IP/proxy headers for anonymous identity.
- Cross-user charging: tested authenticated user isolation.
- Race conditions: tested durable atomic reservation under concurrency.
- Bypass paths: provider-call paths audited and gated or verified disabled.
- Information leakage: limit responses expose safe provider-neutral error data only.
- Persistent anonymous tracking: avoided; anonymous policy is a shared bucket.
- Unbounded data growth: retention cleanup method and window-end index added.
- Production fail-open: deployed startup requires durable controls; store failure returns `503`.

## Files Changed

S1-04 files include:

- `.env.example`
- `.env.test.example`
- `.env.beta.example`
- `.env.production.example`
- `README.md`
- `backend/README.md`
- `backend/app/api/routes/itineraries.py`
- `backend/app/core/config.py`
- `backend/app/core/observability.py`
- `backend/app/core/readiness.py`
- `backend/app/main.py`
- `backend/app/models/__init__.py`
- `backend/app/models/domain.py`
- `backend/app/services/chat_service.py`
- `backend/app/services/mock_repository.py`
- `backend/app/services/provider_contracts.py`
- `backend/app/services/usage_policy.py`
- `backend/migrations/versions/20260815_0009_durable_usage_counters.py`
- `backend/scripts/validate_beta_config.py`
- `backend/tests/conftest.py`
- `backend/tests/test_itinerary_ownership_migration.py`
- `backend/tests/test_provider_contracts.py`
- `backend/tests/test_usage_policy.py`
- `docs/api-contract.md`
- `docs/production-development-progress.md`
- `docs/production-readiness.md`
- `docs/provider-adapters.md`
- `frontend/src/services/apiClient.ts`
- `frontend/src/services/apiClient.test.ts`

The worktree also contains pre-existing S1-01/S1-02/S1-03 files and reports that were preserved.

## Focused Test Results

| Command | Result |
|---|---|
| `venv\Scripts\python.exe -m pytest backend\tests\test_usage_policy.py -q` | Passed: 24 passed, 2 warnings |
| `venv\Scripts\python.exe -m pytest backend\tests\test_itinerary_ownership_migration.py -q` | Passed: 2 passed, 3 warnings |
| `venv\Scripts\python.exe -m pytest backend\tests\test_provider_contracts.py::test_provider_error_normalizes_error_payload backend\tests\test_usage_policy.py backend\tests\test_itinerary_ownership_migration.py -q` | Passed: 27 passed, 4 warnings |
| `npm.cmd test -- src/services/apiClient.test.ts` from `frontend/` | Passed: 1 file, 5 tests |
| `npm.cmd test -- src/services/apiContract.integration.test.ts src/services/apiClient.test.ts` from `frontend/` | Passed: 2 files, 10 tests |

## Complete Validation Results

| Command | Result |
|---|---|
| `venv\Scripts\python.exe -m py_compile backend\app\services\usage_policy.py backend\app\core\config.py backend\app\core\readiness.py backend\app\main.py backend\scripts\validate_beta_config.py backend\tests\test_usage_policy.py` | Passed |
| `venv\Scripts\python.exe -m scripts.validate_beta_config --profile beta` with representative beta placeholders and durable controls enabled | Passed: `errors: []` |
| `venv\Scripts\python.exe -m pytest -q` | Passed: 324 passed, 3 skipped, 13 warnings |
| `npm.cmd run typecheck` from `frontend/` | Passed |
| `npm.cmd test` from `frontend/` | Passed: 13 files, 66 tests |
| `npm.cmd run build` from `frontend/` | Passed |
| `git diff --check` | Passed; line-ending warnings only |
| `git status --short --branch` | Passed; branch `main...origin/main`, dirty tree includes preserved S1 work and S1-04 changes |

## Runtime Results

Safe runtime validation used a disposable SQLite database:

- Alembic head: `20260815_0009`
- Seed: 5 destinations, 10 books, 13 POIs, 2 itineraries
- Usage counter rows after seed: 0
- `/api/health`: `ok`
- `/api/readiness`: `ready`
- readiness durable controls: `true`
- first generation under limit: `200`
- second generation over daily limit: `429`
- `Retry-After`: present, observed `26820`

## Remaining Gaps

- Anonymous limiting is intentionally coarse (`anonymous-global`) until Litinerary defines a trusted proxy/session identity model.
- Perfect request idempotency is not possible until the API introduces stable request or job IDs.
- Scheduled invocation of `cleanup_expired_counters()` is documented but not wired to an external scheduler.
- Alerting, metrics retention, and dashboarding remain S1-07/full observability work.
- Real provider rollout still requires separate staged provider validation.

## Newly Discovered Production Risks

- Running multiple pytest processes in parallel against the same configured basetemp can collide on Windows file locks. Sequential runs or unique basetemps avoid this.
- Global anonymous rate limits can affect unrelated tests if the cached usage guard is not cleared; `backend/tests/conftest.py` now clears it around each backend test.

## Production Impact

With durable controls enabled, restarting or scaling Litinerary no longer resets usage counters. Concurrent requests against the same subject/action/window cannot trivially exceed the configured counter. If the durable limiter fails, expensive traffic does not become unlimited; it fails closed.

## Next Recommended Task

S1-05: fail deployed readiness/startup on missing or unmigrated intended DB.

## Prompt Compliance Matrix

| # | Requirement | Status | Evidence |
| - | ----------- | ------ | -------- |
| 1 | Read current project state first | DONE | Read S1-02/S1-03/progress/re-onboarding docs, inspected git state/history/status, and preserved prior work. |
| 2 | Preserve established security boundaries | DONE | Auth/ownership code was not weakened; usage identity uses `CurrentUser`; full backend and ownership-adjacent tests pass. |
| 3 | Reconstruct all existing usage controls | DONE | Searched usage/rate/quota/provider/frontend/config/test paths and documented previous `InMemoryProviderUsageStore` architecture. |
| 4 | Produce cost/abuse operation inventory | DONE | Inventory table included in this report. |
| 5 | Separate rate, quota, and budget concepts | DONE | Separate rate, quota, and provider budget sections and config variables documented. |
| 6 | Identify current non-durable failure modes | DONE | Previous failure modes documented in this report before replacement. |
| 7 | Select durable storage architecture from evidence | DONE | Chose existing relational DB because repo has SQLAlchemy/Alembic and no Redis. |
| 8 | Define durable control model | DONE | Subject, action, window, atomicity, persistence, failure, and cleanup models documented. |
| 9 | Do not invent commercial policy | DONE | Limits are configurable; no pricing or subscriber tier UI was invented. |
| 10 | Implement durable persistence | DONE | Added `UsageLimitCounterModel` and migration `20260815_0009` with atomic DB store. |
| 11 | Implement centralized enforcement service | DONE | Strengthened `ProviderUsageGuard` and `UsageCounterStore` as the shared boundary. |
| 12 | Handle concurrency correctly | DONE | `test_durable_generation_rate_limit_is_concurrency_safe` proves 5 successes from 12 attempts at limit 5. |
| 13 | Handle process/restart durability | DONE | `test_durable_generation_limit_persists_across_guard_instances` proves enforcement with a new guard/store instance. |
| 14 | Define authenticated request identity | DONE | Generation route passes verified `CurrentUser.id`; user isolation test added. |
| 15 | Define anonymous limiting behavior | DONE | Anonymous generation uses documented shared anonymous bucket; no spoofable headers trusted. |
| 16 | Integrate itinerary generation | DONE | `POST /api/itinerary/generate` routes through durable generation guard after validation; API 429 tests added. |
| 17 | Integrate itinerary adaptation | DONE | Adaptation path inspected; duration bounds and downstream provider gates apply; no separate business quota invented. |
| 18 | Integrate subscriber chat/refinement | DONE | Chat/refinement guard uses verified user ID after session/source checks; isolation covered by usage tests and subscriber auth tests. |
| 19 | Integrate narration/TTS and provider-backed actions | DONE | TTS, routing, POI, vector, ticketing, and LLM guard methods now include durable provider budgets when real providers are enabled. |
| 20 | Provider-call bypass audit | DONE | Provider/action bypass audit table included; no current production cost bypass found. |
| 21 | Implement aggregate provider budget control | DONE | Added durable `PROVIDER_DAILY_REQUEST_CEILING` and estimated cost budget enforcement. |
| 22 | Reservation and failure accounting | DONE | Atomic pre-provider reservations, validation-before-charge moves, and composite refund semantics implemented/documented. |
| 23 | Idempotency/retry analysis | DONE | Current lack of stable request IDs documented with bounded residual retry risk. |
| 24 | Define 429 and limit response behavior | DONE | Provider errors map to `429`; `Retry-After` header and serialized retry seconds added. |
| 25 | Frontend handling | DONE | `ApiError` now exposes `isRateLimited` and `retryAfterSeconds`; frontend tests pass. |
| 26 | Deployed configuration validation | DONE | `usage_control_validation_errors()` and startup validation require durable controls and finite limits in deployed envs. |
| 27 | Backing-store failure behavior | DONE | Missing-table durable failure test expects fail-closed `UNAVAILABLE`; runtime/readiness dependencies documented. |
| 28 | Migration and backward compatibility | DONE | Forward migration preserves existing data; migration test reaches `20260815_0009`; seed verified. |
| 29 | Cleanup/retention mechanism | DONE | `cleanup_expired_counters()` and window-end index added; scheduler remains documented operations work. |
| 30 | Observability hooks | DONE | Usage allowed/blocked and limiter failure structured events added through existing observability helpers. |
| 31 | Security/privacy review | DONE | Review included in report; mitigations implemented for trusted identity, spoofing, races, leakage, and fail-open risk. |
| 32 | Dedicated durable-control tests | DONE | Added tests for below/exact/over, 429, retry-after, user isolation, anonymous, concurrency, restart, validation, failure, provider budget, read endpoints, and dev/test practicality. |
| 33 | Run focused tests first | DONE | Focused usage/migration/frontend tests run and recorded. |
| 34 | Run complete backend validation | DONE | `venv\Scripts\python.exe -m pytest -q`: 324 passed, 3 skipped, 13 warnings. |
| 35 | Run complete frontend validation | DONE | `npm.cmd run typecheck`, `npm.cmd test`, and `npm.cmd run build` passed from `frontend/`. |
| 36 | Migration and seed validation | DONE | Disposable DB upgraded to `20260815_0009`, seeded, and counts verified. |
| 37 | Runtime validation | DONE | Temporary backend returned health/readiness ready; under-limit generation 200; exhausted request 429 with `Retry-After`. |
| 38 | Git/diff validation | DONE | `git diff --check` and `git status --short --branch` run; diff reviewed for S1 preservation and no tracked generated DB/cache. |
| 39 | Update API/configuration documentation | DONE | Updated README, backend README, API contract, provider adapters, production readiness, env templates. |
| 40 | Update production-development progress | DONE | `docs/production-development-progress.md` updated with S1-04 status, architecture, validation, risks, and next task. |
| 41 | Create S1-04 session report | DONE | This file is `docs/stage-1-s1-04-durable-usage-controls-report.md`. |
| 42 | Prompt Compliance Matrix | DONE | This matrix contains one row for every numbered requirement 1 through 42. |
