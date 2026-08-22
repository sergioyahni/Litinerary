# Litinerary Re-Onboarding and Production Readiness Review

Date: 2026-08-15

Scope: read-only project re-onboarding review converted into a Markdown handoff document. No secrets are included. Local secret/configuration files were only assessed by variable names and presence.

## 1. Executive Summary

Litinerary is a literary travel planning application. Users choose a destination and a book, then generate or browse "Litineraries" with mapped book-related stops, narrative notes, routing metadata, narration text, and early account/subscriber features.

Current state: Litinerary is a strong mock/offline MVP plus provider-integration scaffolding. It is not production-ready for public users. The architecture is clear: Vue 3/Vite/Pinia frontend, FastAPI backend, SQLAlchemy/Alembic persistence, deterministic mock data/services by default, and guarded boundaries for LLM, vector DB, POI verification, routing, auth, ticketing, affiliate links, and TTS.

Largest strengths:

- Extensive documentation and runbooks.
- Explicit fail-closed provider guards.
- Broad backend and frontend test coverage in the repo.
- Migration and seed tooling.
- Production-readiness and Render rehearsal harnesses.
- Structured backend logging and readiness checks.
- UI copy that honestly labels mock/development features.

Largest risks:

- Production authentication is not enabled.
- User-feature authorization depends heavily on configuration.
- Rate/cost controls are in-memory only.
- Observability is local logging only.
- Live-provider readiness is intentionally no-go.
- Deployment docs have drift around Render/cloud rehearsal details.

Production readiness: suitable for local development and mock-only private demos; not ready for public production. The first development focus should be re-establishing a trustworthy baseline: run the documented harnesses, resolve ignored artifact permission warnings, update stale docs, and decide the next production target.

## 2. Repository Snapshot

- Repository path: `C:\Users\syahn\source\litinerary`
- Git root: `C:/Users/syahn/source/litinerary`
- Branch: `main`
- Remote: `origin https://github.com/sergioyahni/Litinerary.git`
- Tags: none visible.
- Working tree: tracked tree appeared clean: `## main...origin/main`.
- Ignored local/generated state included `.env`, `.env.development.local`, `frontend/.env`, `frontend/dist`, `frontend/node_modules`, `backend/litinerary.db`, `venv`, caches, and test artifacts.
- Warning: `git status --ignored` reported permission-denied warnings under `tests/.artifacts/tmp/...`; this conflicts with the repository hygiene restoration narrative.
- Recent commits indicate deployment/readiness work:
  - `86a40dc Fix deployment readiness profile imports`
  - `0e27a71 Update form-data dependency`
  - `7bee38e Restore repository hygiene and document development status`
  - several Render rehearsal documentation commits.

Major directories:

- `backend/`: FastAPI app, SQLAlchemy models, migrations, tests, scripts.
- `frontend/`: Vue 3/Vite/Pinia application, assets, tests, package manifests.
- `docs/`: design, API, readiness, beta, Render, live LLM, and runbook documentation.
- `scripts/`: PowerShell local/beta/deployment/Render/live-LLM harnesses.
- `tests/.artifacts/`: ignored local test artifacts.

## 3. Product Overview

Intended users:

- Literary travelers.
- Casual tourists.
- Local explorers.
- Readers planning place-based walks.

Primary user journeys:

- Browse supported destinations.
- Pick a book tied to a destination.
- Configure duration and transportation mode.
- Generate an itinerary.
- Review map, stop list, route summary, and narration.
- Browse public itinerary repository.
- Save/bookmark/review using development account features.
- Use subscriber mock chat to refine a route.

Implemented:

- Mock destination/book catalog.
- Itinerary generation and adaptation.
- Public itinerary repository.
- Leaflet map rendering.
- Text narration and placeholder audio metadata.
- Development account flows.
- Mock subscriber chat.
- Admin seed, ingestion, and POI verification routes.

Incomplete/planned:

- Real auth and production accounts.
- Production-safe user authorization.
- Real LLM rollout.
- Real vector embeddings.
- Real POI, routing, ticketing, TTS, and affiliate integrations.
- Billing/subscription system.
- Privacy lifecycle.
- Production operations.

## 4. Architecture

```text
Vue 3 app
  -> Pinia stores
  -> frontend/src/services/*Api.ts
  -> FastAPI /api/*
  -> backend/app/api/routes/*
  -> backend/app/services/*
  -> SQLAlchemy models + Alembic migrations
  -> SQLite locally / Postgres-compatible deployment
  -> mock/fake providers by default
  -> guarded real-provider adapters only when explicitly enabled
```

Key entry points:

- Frontend: `frontend/src/main.ts`, `frontend/src/router/index.ts`, `frontend/src/App.vue`
- Backend: `backend/app/main.py`
- Config: `backend/app/core/config.py`
- Database: `backend/app/core/database.py`, `backend/app/models/domain.py`
- Provider gates: `backend/app/core/provider_guards.py`, adapter services in `backend/app/services/`

## 5. Technology Stack

- Python/FastAPI: backend API in `backend/app/main.py`.
- SQLAlchemy/Alembic: ORM and migrations in `backend/app/models/domain.py` and `backend/migrations/`.
- SQLite/Postgres-compatible DB: default local SQLite; Render rehearsal docs used Postgres.
- Vue 3 + TypeScript + Vite: frontend app.
- Pinia: state stores under `frontend/src/stores`.
- Vue Router: routes in `frontend/src/router/index.ts`.
- Leaflet/OpenStreetMap tiles: map component in `frontend/src/components/map/ItineraryMap.vue`.
- Vitest/vue-test-utils/jsdom: frontend tests.
- Pytest/FastAPI TestClient: backend tests.
- PowerShell: runbooks and harnesses in `scripts/`.
- External provider boundaries: OpenAI-compatible chat completions, Qdrant, Google Places, OpenRouteService.
- Placeholder-only services: ticketing, affiliate links, and TTS real adapters are not implemented.

## 6. Repository Map

- `README.md`, `backend/README.md`: setup, config, provider posture, dry runs.
- `docs/`: design docs, API contract, readiness reports, beta/Render/live-LLM runbooks, template site.
- `backend/app/api/routes/`: API endpoints.
- `backend/app/core/`: config, auth, guards, DB, readiness, observability.
- `backend/app/services/`: business logic, repositories, mock AI, provider adapters, seed/ingestion/vector/chat/narration.
- `backend/app/schemas/`: Pydantic API models.
- `backend/app/models/domain.py`: relational schema.
- `backend/migrations/versions/`: Alembic revisions `20260610_0001` through `20260614_0007`.
- `backend/tests/`: 30 backend test modules.
- `frontend/src/views/`: pages.
- `frontend/src/components/`: layout, itinerary, and map components.
- `frontend/src/stores/`: Pinia state.
- `frontend/src/services/`: API clients and tests.
- `frontend/src/assets/template/`: copied visual assets from static template.
- `scripts/`: beta, deployment, Render, live LLM, local smoke/test harnesses.

No checked-in `.github`, Dockerfile, `render.yaml`, Vercel, or Netlify config was found during inspection.

## 7. Feature Inventory and Status

| Feature | Location | Status | Coverage/gaps |
|---|---|---|---|
| Destination/book browsing | `destinations.py`, `books.py`, Vue stores/views | Mostly complete for mock/persisted seed | Backend/frontend tests exist |
| Itinerary generation | `mock_repository.generate_itinerary`, `POST /api/itinerary/generate` | Mostly complete for mock MVP | Real LLM gated/no-go |
| Itinerary adaptation | `/api/itineraries/adapt`, mock/LLM pipeline | Partial | Real LLM adaptation does not fully rebuild days/stops |
| Public repository | `/api/itineraries`, `/api/itineraries/{id}` | Mostly complete | Public-only filtering by design |
| Map | `ItineraryMap.vue`, backend routing metadata | Mostly complete | Uses external OSM tiles directly |
| Narration | `narration_service.py`, `ItineraryNarration.vue` | Stubbed/partial | Text works; audio is placeholder metadata |
| Account/preferences/bookmarks/reviews | `users.py`, `user_repository.py`, Vue account components | Partial/dev | Production auth missing |
| Subscriber chat/refinement | `subscriber_chat.py`, `chat_service.py`, `SubscriberChatView.vue` | Partial/mock | No billing/subscription system |
| Admin seed/import/export | `seed_admin.py`, seed scripts | Development-only | Must remain disabled outside dev |
| Book ingestion/POI verification | `ingestion_service.py`, `poi_verification.py` | Development scaffold | Real POI adapter boundary exists |
| Real providers | adapter files | Boundary only | Production readiness no-go |

## 8. Frontend Assessment

The frontend is a functional Vue application, not merely the historical static template. It defines routes for home, destinations, books, itinerary configuration, generated itinerary, public repository, account, bookmarks, and subscriber chat.

Strengths:

- Straightforward Pinia store/service split.
- Loading, error, and empty states exist in major views.
- Map has a text alternative and escapes popup HTML.
- UI copy clearly marks mock/development behavior.
- API contract tests exist under `frontend/src/services` and `frontend/src/test`.

Gaps:

- No client-side route guards; subscriber/account access is UI/state based. Real enforcement must be server-side.
- `authService.ts` stores session only in module memory, so reload loses login.
- `ItineraryMap.vue` calls OpenStreetMap tile servers directly. Production needs privacy, CSP, attribution, and availability decisions.
- `frontend/src/assets/main.css` imports Google Fonts over the network.
- `frontend/src/components/layout/AppFooter.vue` contains mojibake: `â†’`, `Â©`.
- Newsletter form is inert.
- UI duration supports 1-3 days in `ItineraryConfigView.vue`, while backend schema/config allow up to 7.

## 9. Backend/API Assessment

Backend entry point: `backend/app/main.py`.

Endpoint inventory:

- `GET /api/health`
- `GET /api/readiness`
- `GET /api/destinations`
- `GET /api/books?city_id=...`
- `POST /api/itinerary/generate`
- `GET /api/itineraries`
- `GET /api/itineraries/{id}`
- `POST /api/itineraries/adapt`
- `GET /api/itineraries/{id}/narration`
- `POST /api/itineraries/{id}/narration`
- `GET /api/me`
- `/api/users...` profile, preferences, bookmarks, reviews, recommendations
- `/api/subscribers/chat/sessions...`
- `/api/admin/ingestion...`
- `/api/admin/poi-verification...`
- `/api/admin/seed...`

Strengths:

- Pydantic schemas are broad and explicit.
- Provider errors normalize into safe HTTP responses.
- Request IDs and structured logs exist.
- Readiness exposes provider posture without secret values.
- Provider calls are guarded by feature flags, env allowlists, credentials, and external-call gates.

Risks:

- `database_has_seed_data()` silently falls back to mock data if DB schema/data is missing. Render docs show this masked a DB misconfiguration.
- User routes can be public unless `AUTH_REQUIRED_FOR_USER_FEATURES=true`.
- Admin routes require auth role only when auth is enabled; otherwise config is the boundary.
- `_save_itinerary_once()` mutates module-level mock data even when DB is active.
- `itinerary_to_model()` silently drops stops whose POI is missing.
- No idempotency keys for generation/adaptation.
- Real provider rollout remains operationally unapproved.

## 10. Data Model and Persistence

Database implementation:

- SQLAlchemy models: `backend/app/models/domain.py`
- Alembic migrations: `backend/migrations/versions`
- Database config: `backend/app/core/database.py`

Main entities:

- `destinations`, `books`, `book_destinations`
- `pois`, `poi_books`
- `itineraries`, `itinerary_days`, `itinerary_stops`
- `users`, `user_preferences`, `user_reviews`, bookmark association
- `chat_sessions`, `chat_messages`, `chat_itinerary_references`
- `book_sources`, ingestion jobs/candidates/artifacts
- `embedding_records`

Seed data:

- 5 destinations, 10 books, 13 POIs, and 2 seed itineraries in `backend/app/data/mock_data.py`.
- Seed tooling in `backend/scripts/seed_database.py` and `backend/app/services/seed_manager.py`.

Persistence risks:

- Default local SQLite DB is ignored.
- Render docs show a past failure where missing `LITINERARY_DATABASE_URL` caused SQLite fallback and missing user tables.
- Limited visible indexing beyond primary/foreign key constraints.
- Many timestamp fields are strings, not DB-native timestamps.

## 11. Authentication and Authorization

Backend auth lives in `backend/app/core/auth.py`.

Current model:

- Auth disabled by default.
- Dev token format: `dev:<user_id>:<roles>:<subscription_status>`.
- Dev fallback rejected in deployed environments.
- Managed JWT validation foundation exists through issuer/audience/JWKS/provider metadata.
- Managed auth requires `ENABLE_AUTH=true`, non-dev provider, and external-call gates for metadata/JWKS.

Authorization:

- Subscriber chat uses `require_subscriber_user`.
- Admin route auth role only applies when auth is enabled.
- User features use `require_user_feature_access`, but if `AUTH_REQUIRED_FOR_USER_FEATURES=false`, access is effectively open.

Finding: production auth/user authorization is incomplete.

- Evidence: `backend/app/core/auth.py`, `backend/app/api/routes/users.py`, `.env.production.example`
- Impact: user data routes are unsafe if exposed with permissive flags.
- Recommendation: make production profile fail startup unless managed auth and `AUTH_REQUIRED_FOR_USER_FEATURES=true` are configured for user-data features.

## 12. External Integrations

| Service | Purpose | Code | Status |
|---|---|---|---|
| OpenAI-compatible LLM | Itinerary generation/adaptation/judge | `openai_compatible_llm_adapter.py` | Controlled smoke only; public no-go |
| Qdrant | Vector DB | `qdrant_vector_store.py` | Adapter boundary; fake embeddings still used |
| Google Places | POI verification | `google_places_poi_adapter.py` | Adapter boundary |
| OpenRouteService | Routing | `openrouteservice_routing_adapter.py` | Adapter boundary |
| OpenStreetMap tiles | Frontend map tiles | `ItineraryMap.vue` | Active browser dependency |
| Google Fonts | Typography | `main.css` | Active browser dependency |
| Ticketing | Ticket links | `ticketing_service.py` | Mock only; real not implemented |
| Affiliate | Book commerce links | `affiliate_service.py` | Mock only; real not implemented |
| TTS | Audio narration | `narration_service.py` | Mock/text only |
| Managed auth/JWT | Auth | `auth.py` | Foundation only |

## 13. Configuration and Environment Variables

Names and purposes only. Secret values were not printed or recorded.

App/env:

- `APP_ENV`: environment profile.
- `DEBUG`: debug behavior.
- `LOG_LEVEL`: logging verbosity.
- `PORT`: server port where relevant.
- `CORS_ALLOWED_ORIGINS`: allowed browser origins.
- `FRONTEND_URL`: frontend origin/reference.

Database:

- `LITINERARY_DATABASE_URL`: SQLAlchemy database URL.

Feature/admin gates:

- `ENABLE_ADMIN_ROUTES`: exposes admin/development routes.
- `ENABLE_DEBUG_ROUTES`: exposes debug routes.
- `ENABLE_MOCK_SERVICES`: allows mock providers.

External-call gates:

- `ALLOW_EXTERNAL_CALLS`: global external-call enablement.
- `EXTERNAL_CALL_ALLOWED_ENVIRONMENTS`: app env allowlist.
- `ENABLE_INTEGRATION_TESTS`: integration test override.

Auth:

- `ENABLE_AUTH`
- `AUTH_PROVIDER`
- `AUTH_REQUIRED_FOR_USER_FEATURES`
- `AUTH_ALLOW_DEV_USER_FALLBACK`
- `AUTH_JWT_ISSUER`
- `AUTH_JWT_AUDIENCE`
- `AUTH_JWT_ALGORITHMS`
- `AUTH_JWKS_URL`
- `AUTH_PROVIDER_METADATA_URL`
- `AUTH_USER_ID_CLAIM`
- `AUTH_ROLES_CLAIM`
- `AUTH_SUBSCRIPTION_CLAIM`
- `AUTH_EMAIL_CLAIM`
- `AUTH_DISPLAY_NAME_CLAIM`

LLM:

- `LITINERARY_AI_PROVIDER`
- `LLM_PROVIDER`
- `LLM_API_KEY`
- `OPENAI_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL_NAME`
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_TOKENS`
- `LLM_MAX_INPUT_CHARS`
- `LLM_MAX_OUTPUT_TOKENS`
- `LLM_MAX_RETRIES`
- `LLM_MONTHLY_BUDGET_USD`
- `LLM_MAX_LIVE_CALLS_PER_REQUEST`
- `LLM_DAILY_LIVE_REQUEST_CEILING`
- `LLM_DAILY_ESTIMATED_SPEND_CEILING_USD`
- `LLM_LATENCY_ALERT_THRESHOLD_MS`
- `LLM_ERROR_RATE_ALERT_THRESHOLD_PERCENT`
- `LLM_ALLOWED_ENVIRONMENTS`

Vector:

- `LITINERARY_VECTOR_PROVIDER`
- `VECTOR_DB_PROVIDER`
- `VECTOR_DB_URL`
- `VECTOR_DB_API_KEY`
- `QDRANT_URL`
- `QDRANT_API_KEY`
- `QDRANT_COLLECTION_PREFIX`
- `QDRANT_TIMEOUT_SECONDS`
- `LITINERARY_VECTOR_DIMENSION`
- `LITINERARY_VECTOR_STORE_PATH`

POI:

- `LITINERARY_POI_VERIFICATION_PROVIDER`
- `POI_VERIFICATION_PROVIDER`
- `POI_PROVIDER`
- `POI_PROVIDER_API_KEY`
- `GOOGLE_PLACES_API_KEY`
- `POI_VERIFICATION_API_KEY`
- `POI_PROVIDER_BASE_URL`
- `POI_PROVIDER_TIMEOUT_SECONDS`
- `POI_PROVIDER_RESULT_LIMIT`
- `POI_PROVIDER_MIN_CONFIDENCE`

Routing:

- `ROUTING_PROVIDER`
- `ROUTING_API_KEY`
- `OPENROUTESERVICE_API_KEY`
- `ROUTING_BASE_URL`
- `ROUTING_TIMEOUT_SECONDS`
- `ROUTING_MAX_STOPS`
- `ROUTING_SUPPORTED_MODES`
- `ROUTING_FALLBACK_BEHAVIOR`

Ticketing, affiliate, TTS:

- `TICKETING_PROVIDER`, `TICKETING_API_KEY`, `TICKETING_BASE_URL`, `TICKETING_TIMEOUT_SECONDS`
- `AFFILIATE_PROVIDER`, `AFFILIATE_API_KEY`, `AFFILIATE_BASE_URL`, `AFFILIATE_TIMEOUT_SECONDS`
- `TTS_PROVIDER`, `TTS_API_KEY`, `TEXT_TO_SPEECH_API_KEY`, `TTS_BASE_URL`, `TTS_TIMEOUT_SECONDS`

Frontend:

- `VITE_API_BASE_URL`
- `VITE_ENABLE_AUTH`
- `VITE_AUTH_PROVIDER`
- `VITE_AUTH_ALLOW_DEV_LOGIN`
- `VITE_AUTH_LOGIN_URL`
- `VITE_AUTH_LOGOUT_URL`

## 14. Testing Assessment

Backend tests: 30 modules under `backend/tests`, including auth, external-call policy, provider adapters, API contract, seed/migrations, security negatives, usage policy, subscriber chat, and smoke happy path.

Frontend tests: colocated Vitest tests under `frontend/src`, including stores, services, API integration, smoke flow, and itinerary display.

Important note: tests were not run during this document generation. The initial review was read-only, and the documented harness/test commands write temp artifacts/caches under `tests/.artifacts` and may produce build outputs. Historical docs claim recent passes such as backend `292` tests with `3` skipped and frontend build/test passes, but those are documentation evidence, not current execution proof.

Missing or limited:

- No true browser E2E suite was visible.
- No current dependency audit was run.
- No CI configuration was found.
- Production live-provider tests are intentionally gated or disabled.

## 15. Security Assessment

Strengths:

- Env files are ignored.
- Templates avoid real secret values.
- Readiness reports credential presence as booleans.
- Observability redacts sensitive key names.
- Provider external calls fail closed unless multiple gates align.
- CORS wildcard is stripped in production config parsing.
- Admin/debug routes are disabled by production templates.

Risks:

- Production auth is not configured.
- User endpoints can be public if `AUTH_REQUIRED_FOR_USER_FEATURES=false`.
- Admin routes rely on deployment config if auth is disabled.
- In-memory rate/cost controls are not durable across processes/restarts.
- Frontend dev login may be exposed if misconfigured.
- No visible CSRF design, though current auth is bearer-token oriented.
- User data lacks deletion/export/retention flows.
- Dependency vulnerabilities were recorded in Render docs; no fresh audit was run here.

## 16. Reliability, Performance, and Observability

Reliability:

- Provider timeouts exist for adapters.
- Provider error mapping exists.
- Fallbacks are intentional but can hide DB/config problems.
- Generation mutates in-memory mock data; not production-safe under concurrency.
- No job queue for expensive generation/provider tasks.

Performance:

- Current seed data is small, so current runtime performance should be acceptable for local/mock use.
- No clear pagination for itinerary/user/admin lists.
- Frontend map loads external tiles and renders stops client-side.
- Some repository access uses `selectinload`, reducing obvious N+1 risk.

Observability:

- Structured JSON logging exists in `backend/app/core/observability.py`.
- Health/readiness endpoints exist at `/api/health` and `/api/readiness`.
- No metrics, tracing, alerting, external log retention, Sentry, audit-log retention, or dashboards were found.

## 17. Deployment and Infrastructure

Docs describe mock-only beta/staging and a Render cloud-offline rehearsal.

Evidence:

- `scripts/deployment_readiness_check.ps1`
- `scripts/beta_dry_run.ps1`
- `scripts/cloud_offline_render_preflight.ps1`
- `docs/cloud-offline-rehearsal-record-render.md`

Current repo lacks checked-in CI/CD and IaC files such as `.github/workflows`, Dockerfile, `render.yaml`, Vercel, or Netlify config.

Render rehearsal docs show:

- Backend and frontend were deployed in mock/offline mode.
- CORS and DB URL misconfigurations were found and fixed during rehearsal.
- Services were later suspended.
- Postgres remained in place.
- NPM audit findings were noted during frontend Render build.

Production gaps:

- Managed auth.
- Durable DB backups.
- Rollback drill.
- Secrets manager.
- Monitoring and alerting.
- CI/CD.
- Staging policy.
- Dependency scanning.
- Live-provider gates.

## 18. Documentation vs. Implementation

| Claim/topic | Reconciliation |
|---|---|
| Vue/FastAPI/SQLAlchemy architecture | Verified in `frontend/src`, `backend/app`, and migrations |
| Mock/offline MVP default | Verified in config and services |
| `/api/health` and `/api/readiness` | Verified in code |
| Render record mentioning `/health` | Contradicted/stale vs code; app defines `/api/health` |
| Real LLM controlled smoke only | Verified by docs and gated code |
| Public/beta live LLM no-go | Supported by docs and provider guards |
| Real ticketing/TTS/affiliate | Docs and code agree: not implemented |
| Managed auth production-ready | Not production-ready; foundation only |
| Repository hygiene restored | Partially contradicted by current ignored artifact permission warnings |
| Cloud rehearsal not executed | Older docs obsolete; newer Render record says it was executed |
| Static template site | Historical/visual reference; current app is Vue implementation |
| API contract broad Phase 2 endpoints | Mostly verified; admin/dev and subscriber caveats apply |

Docs needing update:

- Render health endpoint/path wording.
- Older cloud-target placeholder docs that say no cloud rehearsal happened.
- Repo hygiene report versus current `tests/.artifacts` permission issue.
- Stale TODO roadmap entries now implemented or superseded.

## 19. Where Development Appears to Have Stopped

Most recent active area: deployment readiness, Render mock/offline rehearsal, repo hygiene, and dependency hygiene.

Completed:

- Mock MVP flows.
- Provider-gated adapter boundaries.
- Alembic/seed foundations.
- Readiness, beta, and Render harnesses.
- Render mock/offline rehearsal documentation.

Unfinished:

- Production auth and authorization hardening.
- Live LLM staged/internal readiness.
- Durable rate/cost controls.
- Observability, monitoring, and alerting.
- Real provider production rollout.
- CI/CD and production deployment automation.
- Cleanup of local artifact permission warnings.

No tracked unfinished working-tree changes were visible.

## 20. Known Bugs, Risks, Gaps, and Technical Debt

### P1 - Production auth/user authorization incomplete

- Evidence: `backend/app/core/auth.py`, `backend/app/api/routes/users.py`, `.env.production.example`
- Impact: user data routes are unsafe if exposed with permissive flags.
- Recommendation: make auth mandatory for user/subscriber features before real users.

### P1 - Durable abuse/cost controls missing

- Evidence: `backend/app/services/usage_policy.py` uses an in-memory store.
- Impact: limits reset on restart and do not work across processes.
- Recommendation: move rate/cost metering to DB, Redis, or provider billing integration.

### P1 - Production observability missing

- Evidence: only local structured logging and health/readiness were found.
- Impact: no alerting or incident visibility.
- Recommendation: add metrics, error reporting, log retention, dashboards, and alerts.

### P1 - Live-provider rollout remains no-go

- Evidence: live LLM docs, provider guards, ticketing/TTS/affiliate services.
- Impact: product value is mostly mock until integrations are approved.
- Recommendation: stage one provider at a time with rollback and monitoring.

### P2 - DB fallback can mask misconfiguration

- Evidence: `database_repository.database_has_seed_data()`, Render record DB fallback issue.
- Impact: app may appear alive while using the wrong DB.
- Recommendation: fail readiness/startup in deployed env if DB schema/seed expectations fail.

### P2 - Docs drift around Render/cloud and health path

- Evidence: `/api/health` in code versus `/health` wording in Render record; older cloud docs obsolete.
- Impact: future deployment work may follow stale instructions.
- Recommendation: consolidate deployment docs.

### P2 - In-memory mock itinerary mutation

- Evidence: `mock_repository._save_itinerary_once()`.
- Impact: concurrency and multi-process inconsistency.
- Recommendation: avoid module-level writes when DB is active.

### P2 - Missing POI stops silently dropped on save

- Evidence: `database_repository.itinerary_to_model()`.
- Impact: data loss or corrupt itinerary display.
- Recommendation: validate and fail loudly, or implement explicit orphan handling.

### P2 - LLM adaptation incomplete

- Evidence: `openai_compatible_llm_adapter.py`.
- Impact: real adaptation may not reflect provider response fully.
- Recommendation: implement full day/stop reconstruction and tests before enabling.

### P2 - No CI/CD found

- Evidence: no `.github`, Dockerfile, or deployment config found.
- Impact: quality gates are manual.
- Recommendation: add CI running backend tests, frontend tests/typecheck/build, and secret-template checks.

### P3 - Frontend mojibake/polish

- Evidence: `frontend/src/components/layout/AppFooter.vue`.
- Impact: visible production roughness.
- Recommendation: fix encoding and add a smoke assertion.

### P3 - Dependency classification cleanup

- Evidence: `frontend/package.json` puts Vite/plugin in dependencies; backend `requirements.txt` includes pytest.
- Impact: noisier production installs.
- Recommendation: split runtime and development dependency sets.

## 21. Production Readiness Checklist

- [?] Reproducible local setup: docs/scripts exist; not rerun here.
- [?] Build: historical pass only; not rerun.
- [x] Configuration templates: present and placeholder-oriented.
- [x] Local secrets ignored: verified by git ignored state.
- [ ] Production secrets management: not implemented.
- [?] Database migrations: migrations exist; not rerun.
- [x] Seed tooling: present.
- [ ] Production authentication: incomplete.
- [ ] Authorization hardening: incomplete.
- [x] Core mock user journeys: implemented.
- [ ] Real provider user journeys: incomplete/no-go.
- [x] Validation: broad Pydantic/domain validation exists.
- [?] Error handling: good structure, but not runtime-verified.
- [?] Testing: broad tests exist; not run.
- [ ] Security hardening: incomplete.
- [x] Structured logging: present.
- [ ] Monitoring/alerting: missing.
- [x] Health checks: `/api/health`, `/api/readiness`.
- [ ] Performance/scalability readiness: incomplete.
- [ ] Backups/DR: not implemented.
- [ ] Deployment automation: not found.
- [ ] CI/CD: not found.
- [?] Staging: Render mock rehearsal documented, currently suspended.
- [ ] Rollback: incomplete drill for live LLM/staged readiness.
- [ ] User-data/privacy lifecycle: missing deletion/retention/export.
- [ ] Documentation: extensive but drifted.
- [ ] Launch operations: incomplete.

## 22. Recommended Development Roadmap

### Stage 0 - Baseline

Run local setup intentionally, clear test artifact permissions, run backend/frontend tests/build/harness, and record actual current results.

### Stage 1 - Correctness Blockers

Fix deployed-env DB fail-fast behavior, remove silent stop dropping, align duration constraints, fix footer encoding, and update drifted docs.

### Stage 2 - Auth and User-Data Safety

Enable managed auth path in staging, enforce user ownership, add route guards, and decide privacy/account deletion requirements.

### Stage 3 - Core Product Completion

Choose whether production MVP remains mock-only or enables one live provider. Improve itinerary persistence, repository UX, subscriber flow, and narration expectations.

### Stage 4 - Testing and Hardening

Add CI, browser E2E, dependency audit gate, auth/security negative tests, and deployed-env config tests.

### Stage 5 - Production Infrastructure

Add deployment manifests, managed DB, migration process, backups, secrets manager, health checks, rollback, and monitoring.

### Stage 6 - Launch and Post-Launch

Run a gradual private beta, observe usage/errors/cost, then expand providers and features.

## 23. Immediate Next 10 Tasks

1. Priority P1: Run baseline verification.
   - Rationale: know current truth.
   - Dependencies: local environment ready.
   - Files: `scripts/deployment_readiness_check.ps1`, backend/frontend test configs.
   - Done: current test/build/harness results recorded.

2. Priority P1: Fix `tests/.artifacts/tmp` permission warnings.
   - Rationale: repo hygiene and tests rely on artifact cleanup.
   - Dependencies: filesystem access.
   - Files: `tests/.artifacts`, README hygiene docs.
   - Done: `git status --ignored` reports no permission warnings.

3. Priority P1: Update deployment docs drift.
   - Rationale: prevent stale deployment instructions.
   - Dependencies: current baseline confirmed.
   - Files: `docs/cloud-offline-*`, Render record, readiness docs.
   - Done: `/api/health` paths and Render state are consistent.

4. Priority P1: Make deployed DB misconfiguration fail loudly.
   - Rationale: avoid SQLite/mock fallback in staging/prod.
   - Dependencies: target deployed profiles defined.
   - Files: `database_repository.py`, `readiness.py`, config tests.
   - Done: deployed env readiness fails if intended DB is missing or unmigrated.

5. Priority P1: Define production auth target.
   - Rationale: blocks real users.
   - Dependencies: infrastructure/provider choice.
   - Files: `auth.py`, `.env.production.example`, `users.py`, docs.
   - Done: selected provider and required env/test matrix documented.

6. Priority P1: Enforce user ownership on user routes.
   - Rationale: prevent insecure direct object access.
   - Dependencies: auth target or current auth model.
   - Files: `users.py`, `auth.py`, `test_negative_security_paths.py`.
   - Done: non-admin users cannot access other users' data when auth is enabled.

7. Priority P2: Replace in-memory usage guard for deployed env.
   - Rationale: rate/cost controls must survive restart/process scale.
   - Dependencies: DB/Redis decision.
   - Files: `usage_policy.py`, DB models/migration.
   - Done: durable metering with tests.

8. Priority P2: Fix persistence integrity gaps.
   - Rationale: avoid silent itinerary data loss.
   - Dependencies: desired validation behavior.
   - Files: `database_repository.py`, tests.
   - Done: missing POI stops produce explicit validation errors.

9. Priority P2: Add CI.
   - Rationale: stop relying on manual harnesses.
   - Dependencies: GitHub/CI target.
   - Files: new workflow/deployment config.
   - Done: PR checks run backend tests, frontend tests/typecheck/build, and secret template checks.

10. Priority P2: Decide live-provider sequence.
    - Rationale: production value depends on real integrations.
    - Dependencies: product and budget decisions.
    - Files: provider docs/adapters/tests.
    - Done: one-provider rollout plan with staging, rollback, monitoring, and cost ceiling.

## 24. Open Questions

Product:

- Is the first public launch intended to be mock-only, curated-data-only, or live LLM-assisted?
- Which cities/books are required for beta?
- Is "Litineraries" intentional branding or a typo?
- What user account features are launch-critical?

Architecture:

- Should generation be synchronous API calls or background jobs?
- Should vector search be required for MVP?
- Should mock fallback ever be allowed in deployed environments?
- What is the source of truth for POI verification?

Infrastructure:

- Final hosting target: Render, Vercel/static plus API host, or another platform?
- Managed Postgres provider and backup policy?
- Secrets manager?
- CI/CD system?

Business/operations:

- Subscription/payment provider?
- Affiliate/ticketing partners?
- Privacy policy, data retention, deletion/export requirements?
- Monitoring/on-call expectations?

## 25. Suggested Context for the Next Codex Session

Litinerary is a Vue 3 + FastAPI literary travel planner at `C:\Users\syahn\source\litinerary`. It currently works as a mock/offline MVP with destination/book browsing, itinerary generation, repository browsing, Leaflet maps, narration text, development account features, subscriber mock chat, seed/admin tooling, and provider-neutral scaffolding. Backend defaults are mock/fake and real provider calls are guarded by config in `backend/app/core/config.py` and `backend/app/core/provider_guards.py`.

Current priority is not new features yet. First re-establish the baseline: inspect `git status`, fix local `tests/.artifacts/tmp` permission warnings, run `scripts/deployment_readiness_check.ps1` intentionally, run backend/frontend tests/build, and update stale deployment docs. Production blockers are managed auth, user authorization, durable rate/cost controls, observability, DB fail-fast behavior, CI/CD, backups/rollback, and live-provider readiness.

Read these first:

- `docs/litinerary-development-status-report.md`
- `docs/production-readiness.md`
- `docs/cloud-offline-rehearsal-record-render.md`
- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/core/auth.py`
- `backend/app/services/mock_repository.py`
- `backend/app/services/database_repository.py`
- `frontend/src/router/index.ts`
- `frontend/src/stores/userStore.ts`
- `scripts/deployment_readiness_check.ps1`
