# Litinerary Beta Go/No-Go Report

Audit date: 2026-06-15

Scope: beta release hardening audit against `docs/App_Design_Document_v2.md`, current repository files, configuration examples, tests, provider-adapter boundaries, safety gates, frontend flows, backend services, and migrations. No real providers were connected and no deployment was performed.

## 1. Executive Summary

Litinerary is ready for a local beta demo using deterministic mock/fake services.

Litinerary is conditionally ready for a private staging beta only if it is run as a mock-only, non-production, protected beta environment using the beta profile in `.env.beta.example`, exact CORS origins, disabled admin/debug routes, disabled external calls, and the dry-run gate in `scripts/beta_dry_run.ps1`.

Litinerary is not ready for production. Production blockers remain around managed authentication, durable rate/cost controls, real provider integration gates, production observability/alerting, deployment pipeline, secret management, migration/backup operations, and full private ownership enforcement.

Verification performed:

- Backend: `..\venv\Scripts\python.exe -m pytest --basetemp=.pytest_tmp_beta_audit` from `backend` passed: 191 passed, 3 skipped.
- Frontend: `npm test` from `frontend` passed: 55 passed.
- Frontend build: `npm run build` from `frontend` passed.
- Initial backend pytest run without `--basetemp` failed because pytest could not access `C:\Users\syahn\AppData\Local\Temp\pytest-of-syahn`; rerun with workspace `--basetemp` passed.

## 2. SDD Coverage

Implemented:

- Vue 3 + TypeScript frontend with routes for home, destinations, books, itinerary configuration, generated itinerary, public itinerary repository/detail, account, bookmarks, and subscriber chat (`frontend/src/router/index.ts`).
- FastAPI backend with public destination/book/itinerary endpoints, health/readiness endpoints, user account foundations, subscriber chat routes, admin ingestion/POI/seed scaffolding, and provider-neutral schemas (`backend/app/main.py`, `backend/app/api/routes/*`, `docs/api-contract.md`).
- Public itinerary repository behavior: exact-match lookup, partial adaptation, new mock generation, saved generated/adapted itineraries, public/private visibility foundations (`backend/app/services/mock_repository.py`, migrations under `backend/migrations/versions`).
- Leaflet map display and route geometry support in frontend/backend contracts (`frontend/src/components/map/ItineraryMap.vue`, `backend/app/schemas/domain.py`).
- Text narration fallback and placeholder audio metadata (`backend/app/services/narration_service.py`, `frontend/src/components/itinerary/ItineraryNarration.vue`).
- Book ingestion and POI verification admin foundations with copyright/licensing metadata (`backend/app/api/routes/ingestion.py`, `backend/app/api/routes/poi_admin.py`, `backend/migrations/versions/20260611_0003_book_ingestion.py`, `20260611_0004_poi_verification.py`, `20260612_0005_ownership_visibility_provenance.py`).
- Subscriber chat foundation using mock AI and subscriber-only private itinerary refinement (`backend/app/api/routes/subscriber_chat.py`, `backend/app/services/chat_service.py`, `backend/migrations/versions/20260614_0007_subscriber_chat.py`).

Mock/stubbed:

- Itinerary generation is deterministic mock AI, not a live LLM (`backend/app/services/mock_ai_service.py`).
- Vector search uses fake deterministic embeddings and fake/local stores by default (`backend/app/services/vector_service.py`, `backend/app/services/fake_vector_store.py`).
- POI verification is mock by default (`backend/app/services/poi_verification.py`).
- Routing is mock straight-line geometry by default (`backend/app/services/routing_service.py`).
- Ticketing, affiliate links, and TTS are provider-neutral placeholders only (`backend/app/services/ticketing_service.py`, `affiliate_service.py`, `narration_service.py`).
- Payment, checkout, commerce, live ticket inventory, and real voice audio are not implemented.

Behind feature flags:

- Real LLM: `ENABLE_REAL_LLM`, OpenAI-compatible adapter boundary in `backend/app/services/openai_compatible_llm_adapter.py`.
- Real Vector DB: `ENABLE_REAL_VECTOR_DB`, Qdrant boundary in `backend/app/services/qdrant_vector_store.py`.
- Real POI provider: `ENABLE_REAL_POI_PROVIDER`, Google Places boundary in `backend/app/services/google_places_poi_adapter.py`.
- Real routing: `ENABLE_REAL_ROUTING`, OpenRouteService boundary in `backend/app/services/openrouteservice_routing_adapter.py`.
- Real ticketing/TTS/affiliate: flags exist, but real adapters are intentionally not implemented.
- Auth: `ENABLE_AUTH`, `AUTH_REQUIRED_FOR_USER_FEATURES`, and dev-token validation boundary in `backend/app/core/auth.py`.

Missing or deferred:

- Managed auth provider, real JWT validation, `/api/me` current-user flow, and production-grade frontend route/session protection.
- Production owner/visibility model for private itinerary CRUD beyond current foundations.
- Durable distributed rate limits and cost metering; current usage policy is in-memory/local (`backend/app/services/usage_policy.py`).
- Real provider integration tests and live-provider operational gates.
- Deployment pipeline, secret manager integration, production logs/metrics/alerts, backups, rollback drills, dependency scanning, and data retention policy.
- Real transit routing, real ticket inventory, affiliate disclosure flow, e-commerce/payment, and generated audio storage.

## 3. Safety Gate Status

External-call blocking: Pass for beta. `backend/app/core/provider_guards.py` blocks live calls unless feature flag, `ALLOW_EXTERNAL_CALLS=true`, allowed environment, credentials, and integration-test opt-in requirements pass. Tests cover standard test blocking and transport-level guard behavior.

Feature flags: Pass for beta. Real provider flags default false in `backend/app/core/config.py`, `.env.beta.example`, and `.env.production.example`.

Admin route protections: Conditional pass. Admin routes are config-guarded by `require_admin_routes`; beta/production defaults disable them. Destructive seed reset/import routes are blocked in production even if admin routes are enabled. Gap: admin routes do not yet require authenticated admin identity if explicitly enabled.

Debug route protections: Pass for beta. `/api/users/{user_id}/recommendations/mock` is guarded by `require_debug_routes`; beta/production defaults disable debug routes.

CORS safety: Pass for beta templates. Local defaults are development origins; production strips wildcard origins. Beta and production examples use exact origins.

Secret handling: Pass for current repo templates. Env examples are placeholder-only, readiness exposes credential presence booleans only, and observability redacts sensitive key names. Real secret-manager integration remains production work.

Auth readiness: No-go for production. Auth foundation supports only local/test `dev:<user_id>:<roles>:<subscription_status>` tokens and rejects dev auth in production. Managed provider validation is not implemented.

Ownership/visibility model: Partial. Database fields and public repository filtering exist; subscriber refined itineraries are private/subscriber-only. Full production ownership route coverage depends on real auth and future private itinerary endpoints.

Rate limits: Partial. Local usage guardrails cover generation, subscriber chat, vector, POI, routing, ticketing, and TTS operations. They are in-memory and not production-grade.

Cost controls: Partial. Provider daily cost ceiling exists and defaults to `0`, but durable metering, billing reconciliation, alerts, and provider-specific spend enforcement are not implemented.

Logging safety: Good beta foundation. `backend/app/core/observability.py` emits request IDs and structured events with key-based redaction. No external logging backend, retention policy, PII policy, or alerting exists.

Test coverage: Strong for mock beta. Backend, frontend, smoke, negative-path, provider contract, guard, observability, usage policy, adapter-boundary, migration/model, and subscriber-chat tests are present and passing with workspace temp override.

## 4. Test Status

Backend tests:

- Command: `..\venv\Scripts\python.exe -m pytest --basetemp=.pytest_tmp_beta_audit`
- Result: 191 passed, 3 skipped.
- Coverage areas include API contract, MVP API, auth foundation, environment guards, external-call policy, provider contracts, mocked adapters, migrations/model metadata, persistence, seed manager, smoke path, subscriber chat, user accounts, vector service, usage policy, observability, and negative security paths.

Frontend tests:

- Command: `npm test`
- Result: 55 passed across 11 test files.
- Coverage includes API client error handling, catalog stores, itinerary stores, auth/user/subscriber chat stores, itinerary display components, service wrappers, and happy-path smoke flow.

E2E/smoke tests:

- Backend smoke path passed as part of backend suite (`backend/tests/test_smoke_happy_path.py`).
- Frontend happy-path smoke passed (`frontend/src/test/happyPath.smoke.test.ts`).
- Full `scripts/beta_dry_run.ps1` was inspected but not executed end to end during this audit.

Negative-path/security tests:

- Passed in `backend/tests/test_negative_security_paths.py`, `test_auth_foundation.py`, `test_environment_guards.py`, `test_external_call_policy.py`, and frontend API/store tests.

Provider contract tests:

- Passed in `backend/tests/test_provider_contracts.py`.
- Adapter-boundary tests passed for Google Places, OpenAI-compatible LLM, OpenRouteService, Qdrant, ticketing, affiliate, vector, and usage guardrails with fake transports/no live network.

Skipped integration tests:

- `backend/tests/test_google_places_poi_adapter.py::test_live_google_places_integration_skipped_by_default`
- `backend/tests/test_openai_compatible_llm_adapter.py::test_live_llm_integration_skipped_by_default`
- `backend/tests/test_openrouteservice_routing_adapter.py::test_live_openrouteservice_integration_skipped_by_default`

## 5. Known Blockers

Must fix before beta demo:

- No product-code blocker found for a local mock beta demo.
- Operational note: backend tests should be run with a workspace `--basetemp` on this machine, or the Windows temp permissions issue should be resolved.
- Confirm local database migrations/seed data before demo: `backend/migrations`, `backend/scripts/seed_database.py`.

Must fix before private staging:

- Run and pass `scripts/beta_dry_run.ps1` against the intended staging profile and URL.
- Confirm beta CORS origin and frontend `VITE_API_BASE_URL` match the deployed beta URLs.
- Use an explicit non-production database target and seed only approved beta data.
- Keep `ALLOW_EXTERNAL_CALLS=false` and all real provider flags false.
- Keep admin/debug routes disabled in staging unless behind a private deployment boundary plus authenticated admin controls.
- Decide whether private staging is staff-only/mock-only. If external beta users are invited, managed auth becomes a staging blocker.

Must fix before public production:

- Integrate managed auth provider and production JWT validation.
- Add durable per-user/session/provider rate limits and cost controls.
- Add production observability backend, dashboards, alerting, log retention, PII policy, and incident runbooks.
- Add secret manager/deployment environment integration.
- Add deployment pipeline and rollback procedure.
- Add migration backup/restore procedure and migration-state readiness check.
- Complete ownership checks for private/user-owned resources.
- Complete live provider gates, terms review, attribution/caching policy, and opt-in integration tests before enabling any real provider traffic.
- Add dependency/security scanning.

Future milestone:

- Real Vector DB backfill and deletion policy.
- Real POI verification/manual review workflow.
- Real routing, including transit limitations and attribution.
- Real LLM generation/judge operations with prompt/version governance.
- Real ticketing/affiliate provider selection with legal/product review.
- TTS audio generation, storage, retention, and accessibility policy.
- Payment/e-commerce and subscription billing.

## 6. Recommended Next Prompts

1. "Run the full beta dry run, fix any blockers, and update the beta runbook with exact commands and expected outputs."
2. "Integrate managed auth provider JWT validation behind `ENABLE_AUTH` without changing anonymous access."
3. "Add production-ready durable usage metering for itinerary generation, subscriber chat, and provider calls."
4. "Implement gated Qdrant integration test profile and vector backfill executor with deletion policy."
5. "Add gated live Google Places integration tests and provider observability before production POI traffic."
6. "Add gated live OpenRouteService integration tests and routing observability before production route traffic."
7. "Add gated live LLM integration tests, spend enforcement, and provider observability before production LLM traffic."
8. "Create deployment pipeline and production secret-management plan without connecting real providers."

## 7. Final Go/No-Go

Go for local demo.

Conditional go for private staging beta, limited to mock-only staged use after `scripts/beta_dry_run.ps1` passes against the target environment and admin/debug/external-call gates are verified.

No-go for production.

Files created or modified by this audit:

- Created: `docs/beta-go-no-go-report.md`

No real providers were connected. No deployment was performed.
