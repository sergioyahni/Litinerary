# Integration Test Matrix

This matrix maps pre-deployment integration coverage while keeping default tests
offline/mock-only. It does not approve live providers, staged internal testing,
public/beta live LLM generation, or deployment.

| Test name | Purpose | Layer | Default mode | CI | Dependencies | Risk addressed | Current coverage status | Recommended next implementation task |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Readiness endpoint integration | Verify `/api/readiness` reports database status, provider modes, external-call gates, operational limits, and credential booleans without secret values. | Backend API | Offline/mock | Yes | FastAPI `TestClient`, SQLite test DB | Unsafe readiness output, wrong provider mode, hidden deployment drift | Implemented in `backend/tests/test_offline_integration_readiness.py`; also covered by `test_observability.py` and `scripts/deployment_readiness_check.ps1` temporary backend readiness checks | Remaining gap: add browser-level frontend/backend rehearsal if a later E2E harness is approved. |
| Health endpoint deployment check | Verify `/api/health` returns `ok` and request ID behavior remains stable. | Backend API/deployment | Offline/mock | Yes | FastAPI `TestClient`; temporary backend in dry run | Broken service startup or missing request tracing | Implemented in `scripts/deployment_readiness_check.ps1` and `scripts/local_offline_deployment_rehearsal.ps1`; also covered by `test_mvp_api.py`, `test_observability.py`, and beta dry-run runbook | Remaining gap: cloud-specific health check rehearsal after deployment target is selected. |
| Seed reset and validate | Verify development seed export/import/reset/validate works and production/beta destructive paths stay blocked. | Backend API/data | Offline/mock | Yes | SQLite test DB, admin routes in dev mode | Broken seed data, unsafe destructive routes | Implemented in `backend/tests/test_offline_integration_readiness.py`; also covered by `test_seed_manager.py`, `test_database_seed.py`, `test_environment_guards.py`, `scripts/deployment_readiness_check.ps1`, and `scripts/local_offline_deployment_rehearsal.ps1` endpoint seed reset/validate checks | Remaining gap: cloud deployment seed/migration rehearsal remains manual until deployment target exists. |
| Mocked itinerary generation | Verify exact match, partial adaptation, and new mock generation through `/api/itinerary/generate`. | Backend API/service | Offline/mock | Yes | Seed data, fake AI, mock routing/POI | MVP journey regression, bad repository matching | Implemented for London/Sherlock/Baker Street in `backend/tests/test_offline_integration_readiness.py` and exercised against a temporary local backend by `scripts/local_offline_deployment_rehearsal.ps1`; exact/adapt/new variants also covered by `test_mvp_api.py`, `test_persistent_repository.py`, `test_smoke_happy_path.py` | Remaining gap: endpoint-level provenance-failure fixture belongs in Batch 2. |
| Provider fail-closed behavior | Verify live providers cannot call out unless feature flags, credentials, external-call policy, and env allow-lists are explicit. | Backend provider boundary | Offline/mock | Yes | Provider guard code, mocked adapters | Accidental external calls, CI network leakage | Implemented at integration level in `backend/tests/test_provider_fail_closed_integration.py`; Batch 1 deployed defaults also covered by `test_offline_integration_readiness.py`; unit/adapter coverage remains in `test_external_call_policy.py`, provider adapter tests, and `test_provider_contracts.py` | Remaining gap: add endpoint-level user-facing copy checks for provider failures if product copy becomes specified. |
| Negative-path provider guard tests | Verify missing config, disabled flags, standard `APP_ENV=test`, and disallowed environments return safe errors. | Backend provider boundary | Offline/mock | Yes | Provider adapters, config cache reset | Unsafe live mode, unclear failures | Implemented in `backend/tests/test_provider_fail_closed_integration.py` for LLM missing/partial gates, bad allowlists, missing key/model, unsupported providers, conflicting provider env values, beta/internal gates, and non-LLM provider readiness states | Remaining gap: future provider-specific live-gated tests stay disabled until separate approvals exist. |
| Grounding/provenance failure tests | Verify unsafe full text, missing license/copyright context, missing POI provenance, and hallucination-prone output fail before or during judge checks. | Backend LLM safety | Offline/mock with mocked transport | Yes | LLM grounding service, seeded POIs | Hallucinated/unsupported live output, unsafe source use | Covered by `test_openai_compatible_llm_adapter.py`, `test_seed_manager.py`, `test_database_seed.py` | Add endpoint-level failure test proving generation fails safely when seed POI provenance is removed. |
| Frontend itinerary generation flow | Verify user can select destination/book, configure itinerary, generate, view stops/map text, bookmark, review, and browse repository. | Frontend app | Offline/mock | Yes | Vitest, Vue Test Utils, mocked API services, mocked Leaflet | Broken MVP UX, store/router drift | Implemented in `frontend/src/test/frontendApiIntegration.test.ts` for London/Sherlock/Baker Street generation, repository list/detail, loading, empty state, and controlled UI errors; broader MVP happy path remains covered by `frontend/src/test/happyPath.smoke.test.ts` and store tests | Remaining gap: browser-level app/backend harness belongs in Batch 4 or a later E2E pass. |
| Frontend/API service contract | Verify frontend service wrappers call the correct backend paths, methods, query params, payloads, and auth headers. | Frontend service | Offline/mock | Yes | Vitest, mocked `fetch` | API path drift, broken auth header behavior | Implemented in `frontend/src/services/apiContract.integration.test.ts` for generation, list/detail, readiness, validation error, provider-unavailable error, and rejected fetch shapes; existing service tests cover catalog, users, API client, auth store | Remaining gap: generated OpenAPI snapshot comparison if an API-contract artifact is introduced. |
| API contract stability | Verify backend response shapes for public, user, and admin endpoints remain stable. | Backend API contract | Offline/mock | Yes | FastAPI `TestClient`, seed data | Frontend/backend schema drift | Partially expanded by `backend/tests/test_offline_integration_readiness.py`; also covered by `test_api_contract.py` | Remaining gap: OpenAPI or fixture snapshot comparison for frontend/API contract drift. |
| Auth/ownership boundary checks | Verify anonymous public access, protected user features, dev token limits, managed JWT validation with mocked JWKS, owner/admin checks, and beta/prod dev-token rejection. | Backend auth/API | Offline/mock with mocked JWT/JWKS | Yes | Auth foundation, mocked JWK client | Unauthorized access, unsafe dev fallback | Covered by `test_auth_foundation.py`, subscriber chat tests, negative security tests | Add staged-internal access-boundary tests once a real internal boundary is designed. |
| Secret hygiene checks | Verify readiness, preflight, logs, provider diagnostics, and templates do not expose key-like values or raw provider payloads. | Security/ops | Offline/mock | Yes | Observability tests, preflight script tests, safe scan script | Secret leakage, unsafe artifacts | Covered by `test_observability.py`, `test_live_llm_preflight.py`, manual scans, and high-confidence repository scans in `scripts/deployment_readiness_check.ps1` | Remaining gap: extract the scan into a smaller reusable CI helper if separate jobs need it. |
| Migration and seed readiness | Verify Alembic head/current, schema metadata, seed loading, and seed validation are deployment-ready. | Backend data/deployment | Offline/mock | Yes | Alembic, SQLite non-production DB, seed script | Broken deployment DB or stale seed data | Implemented in `scripts/deployment_readiness_check.ps1`; covered by metadata migration tests, seed tests, and beta dry-run runbook | Remaining gap: cloud deployment migration rehearsal remains manual until deployment target exists. |
| Local offline deployment rehearsal | Run the preflight harness, start a temporary mock-only backend, verify health/readiness, seed reset/validate, one mock itinerary generation, shutdown, and no-listener cleanup. | Deployment rehearsal | Offline/mock | Yes locally; CI if loopback process startup is allowed | `scripts/local_offline_deployment_rehearsal.ps1`, `scripts/deployment_readiness_check.ps1`, local venv | Local deployment drift, failed startup/shutdown, accidental live providers | Implemented and documented in `docs/local-offline-deployment-rehearsal.md`; sanitized record written to `docs/local-offline-deployment-rehearsal-record.md` when run | Remaining gap: cloud-specific deployment rehearsal after deployment target is selected. |
| Cloud offline deployment rehearsal | Rehearse a non-production cloud deployment posture with mock-only providers, cloud runtime config review, health/readiness, seed validation, mock generation, log/redaction review, rollback, and sanitized evidence. | Deployment rehearsal | Offline/mock | Manual by target | `docs/cloud-offline-deployment-rehearsal.md`, selected cloud target, non-production DB, log sink | Cloud deployment drift, unsafe runtime config, missing rollback/log evidence | Planned in `docs/cloud-offline-deployment-rehearsal.md`; checklist in `docs/cloud-offline-deployment-checklist.md`; evidence template in `docs/cloud-offline-deployment-rehearsal-record-template.md` | Execute only after selecting a non-production cloud target and confirming no live providers or secrets are required. |
| Health/readiness deployment checks | Start a temporary mock-only backend, then verify `/api/health`, `/api/readiness`, admin/debug route protection, external calls disabled, and provider mock modes. | Deployment harness | Offline/mock | Yes | `scripts/deployment_readiness_check.ps1`, `scripts/local_offline_deployment_rehearsal.ps1`, local venv, npm | Deployment profile drift, accidental live providers | Implemented in `scripts/deployment_readiness_check.ps1` and rehearsed by `scripts/local_offline_deployment_rehearsal.ps1`; documented in `docs/deployment-readiness-harness.md` | Remaining gap: add hosted/cloud health checks only after deployment target and access boundary are approved. |
| Usage/cost guardrails | Verify in-memory request ceilings, input/output bounds, duration limits, live completion ceilings, and cost ceilings block locally. | Backend usage policy | Offline/mock | Yes | Usage guard, fake store | Runaway local/provider-like work | Covered by `test_usage_policy.py` | Add endpoint-level tests for user-facing safe errors on usage-policy blocks. |
| Rollback drill readiness | Verify no-live rollback can capture live-ready preflight, live-configured readiness, mock/offline reset, and post-reset readiness without provider calls. | Ops runbook | Live-gated local, no provider call | No by default | Ignored local env, backend start/stop, readiness endpoint | Inability to return to mock/offline mode | Attempted but incomplete in `docs/live-llm-rollback-drill-record.md` | Rerun manually from trusted PowerShell and record passing evidence. |
| Optional live LLM smoke test | Verify the OpenAI-compatible path with exactly one approved request and sanitized evidence. | Provider-gated smoke | Live-gated | No | Approved local env, runbook, rollback | Real provider integration regression | Three manual smoke tests completed; not part of default integration tests | Keep disabled; repeat only under controlled smoke runbook after blockers/approval. |
| Optional live POI/routing/vector tests | Verify future real non-LLM providers when separately approved. | Provider-gated adapter | Live-gated | No | Provider credentials, explicit flags, separate runbooks | Real provider adapter drift | Skipped placeholders for some adapters; live providers not approved | Do not implement until separate provider readiness review approves scope. |

## Coverage Summary

Already exists:

- Backend offline API and service integration coverage is broad.
- Provider fail-closed and adapter boundary tests exist for major provider types.
- Readiness, observability, redaction, auth, seed, usage, and grounding tests
  exist.
- Frontend service, store, component, and routed smoke tests exist.
- Batch 4 deployment-readiness harness exists for mock-only pre-deployment
  posture checks.
- Local offline deployment rehearsal exists for mock-only temporary backend
  startup, endpoint checks, mock generation, and shutdown evidence.
- Cloud offline deployment rehearsal is planned with a runbook, checklist, and
  evidence template.

Partially exists:

- Browser-level frontend/backend integration remains partially covered by
  component/API tests rather than a browser runner against a temporary backend.
- Frontend runtime preview remains manual; the rehearsal relies on the Batch 4
  harness for frontend tests, typecheck, and build.
- Secret hygiene exists as focused tests, manual scans, and the Batch 4 harness;
  a smaller standalone scanner may still be useful for separate CI jobs.
- Rollback drill evidence exists as an attempted/incomplete record.
- Staged log-sink review is planned but not executed.

Missing:

- Browser-level frontend/backend mock-only integration harness.
- Cloud-specific deployment rehearsal and hosted health/readiness checks.
- Completed cloud offline deployment evidence.
- Approved provider-gated test harnesses beyond controlled smoke runbooks.

Implemented in Batch 1:

- `backend/tests/test_offline_integration_readiness.py` groups offline backend
  integration coverage for health, readiness, deployed default gates, seed
  reset/validate, London/Sherlock/Baker Street mock generation, mock routing
  provenance, invalid generation requests, malformed JSON, and response
  secret/raw-payload hygiene.

Implemented in Batch 2:

- `backend/tests/test_provider_fail_closed_integration.py` groups offline
  provider gate integration coverage for real-LLM negative paths, partial live
  gate combinations, non-LLM provider disabled/mock readiness states, real-flag
  readiness visibility without external policy/config, and response
  secret/raw-payload hygiene.
- The Batch 2 no-network guard blocks OpenAI-compatible provider `urlopen` and
  non-loopback socket connects. Loopback socket connects are allowed because
  Starlette/FastAPI `TestClient` uses local event-loop socket plumbing on
  Windows; no external provider network is allowed by these tests.

Implemented in Batch 3:

- `frontend/src/test/frontendApiIntegration.test.ts` covers the offline/mock
  London/Sherlock/Baker Street generation UI flow, expected request shape,
  safe display of mock provider/provenance data, repository loading/list/detail,
  empty state, validation/provider errors, rejected repository/detail calls,
  and UI secret/raw-payload hygiene.
- `frontend/src/services/apiContract.integration.test.ts` covers frontend API
  handling for successful generation, itinerary list/detail, readiness, backend
  validation errors, provider-unavailable errors, and rejected `fetch` calls.
- All Batch 3 tests use Vitest mocks/fixtures only. They do not start a backend,
  make external calls, enable live providers, or approve staged/internal or
  public/beta live generation.

Implemented in Batch 4:

- `scripts/deployment_readiness_check.ps1` provides the offline/mock
  pre-deployment harness.
- `docs/deployment-readiness-harness.md` documents purpose, run modes, checks,
  pass/fail criteria, and remaining gaps.
- Default mode validates secret hygiene, ignored local env files, environment
  template placeholders, fail-closed provider posture for `development`, `test`,
  `internal`, `staging`, and `production`, temporary Alembic migration/seed
  readiness, temporary backend `/api/health` and `/api/readiness`, focused
  backend deployment tests, focused frontend/API integration tests, frontend
  typecheck, and frontend build.
- Full mode runs complete backend pytest and full frontend Vitest before
  typecheck/build.
- Batch 4 remains offline/mock only. It does not approve staged internal live
  LLM testing, public/beta live generation, cloud deployment, or Batch 5
  provider-gated tests.

Implemented after Batch 4:

- `scripts/local_offline_deployment_rehearsal.ps1` runs the Batch 4 harness as a
  preflight, starts a temporary offline/mock backend, verifies health/readiness,
  seed reset/validate, London/Sherlock/Baker Street mock generation, shutdown,
  and no-listener cleanup.
- `docs/local-offline-deployment-rehearsal.md` documents scope, commands,
  environment posture, pass/fail criteria, and evidence expectations.
- `docs/local-offline-deployment-rehearsal-record.md` stores sanitized local
  offline rehearsal evidence after script execution.
- `docs/cloud-offline-deployment-rehearsal.md`,
  `docs/cloud-offline-deployment-checklist.md`, and
  `docs/cloud-offline-deployment-rehearsal-record-template.md` define the next
  mock-only cloud deployment gate. No cloud deployment is performed by these
  documents.

## Recommended First Implementation Batch

Batch 1 backend offline integration tests are implemented in
`backend/tests/test_offline_integration_readiness.py` with:

- `/api/readiness` reports database `ok`, external calls disabled, LLM mock mode,
  all non-LLM providers mock/fake and `realEnabled=false`.
- `/api/health` returns `ok`.
- Production-like and internal readiness profiles do not enable live LLM without
  explicit gates.
- `/api/admin/seed/reset`, `/api/admin/seed/validate`, and seed export pass in a
  development test context and confirm London/Sherlock/Baker Street data.
- Seed admin endpoints remain blocked by default outside local/test contexts.
- `/api/itinerary/generate` creates a deterministic London/Sherlock mock
  itinerary using Baker Street, mock AI, and mock routing only.
- Invalid and malformed generation requests fail safely.
- No checked response body contains key-like values or raw provider payloads.

Next implementation batch: Batch 5 optional provider-gated tests, disabled by
default. Do not implement Batch 5 until staged/internal blockers are resolved
and a separate approval defines scope, ceilings, owners, monitoring, and
rollback requirements.
