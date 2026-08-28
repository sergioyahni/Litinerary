# Litinerary

Litinerary is a book-oriented travel itinerary MVP. It lets a user choose a supported destination, choose a book connected to that place, configure a short route, generate a deterministic mock itinerary, view mapped stops, and browse reusable public itineraries.

The current implementation follows the visual direction of the preserved static travel template in `docs/webpage-template`, while using a Vue 3 frontend and FastAPI backend for the Phase 1 flow described in `docs/App_Design_Document_v2.md`.

## Project Structure

- `docs/` contains the Software Design Document and the original static webpage template.
- `backend/` contains the FastAPI app, mock data, SQLAlchemy models, SQLite/Alembic setup, repository matching/adaptation logic, and backend tests.
- `frontend/` contains the Vue 3 + TypeScript app, Pinia stores, API services, Leaflet map display, and frontend tests.
- `venv/` is the local Python virtual environment used by this workspace.

## Frontend Setup

```bash
cd frontend
npm install
```

Useful frontend scripts:

```bash
npm run dev
npm run build
npm run typecheck
npm test
npm run test:smoke
```

The frontend dev server defaults to Vite's local port, usually `http://localhost:5173`. API calls default to `http://127.0.0.1:8000`; set `VITE_API_BASE_URL` if the backend is running elsewhere.

## Backend Setup

```bash
cd backend
..\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Database Setup

Local development uses SQLite by default at `backend/litinerary.db`. Override this with `LITINERARY_DATABASE_URL` when needed.

The current schema includes enforced itinerary ownership/visibility fields, user auth-provider mapping, role/subscription status, provider provenance, POI verification state, source licensing/copyright safety, and future vector metadata (`embedding_records`). Public repository itineraries remain anonymous and ownerless; subscriber/private itineraries are owner-bound and hidden from other users. Real provider integrations and the hosted auth frontend flow are still disabled or placeholder-gated.

## Backend Environment Guardrails

Backend configuration is centralized in `backend/app/core/config.py`. Local development and tests use permissive defaults; production defaults are restrictive.

Supported environment variables:

- `APP_ENV`: `development`, `test`, `internal`, `beta`, `staging`, or `production`. Defaults to `development`. `internal` is reserved for staged internal testing and is not enabled by default.
- `DEBUG`: defaults to `true` outside production and `false` in production.
- `ENABLE_ADMIN_ROUTES`: enables `/api/admin/*` routes. Defaults to `true` outside production and `false` in production.
- `ENABLE_DEBUG_ROUTES`: enables development/debug routes such as `GET /api/users/{user_id}/recommendations/mock`. Defaults to `true` outside production and `false` in production.
- `ENABLE_MOCK_SERVICES`: allows fake/mock AI, vector, and POI verification services. Defaults to `true` outside production and `false` in production.
- Real provider feature flags: `ENABLE_REAL_LLM`, `ENABLE_REAL_VECTOR_DB`, `ENABLE_REAL_POI_PROVIDER`, `ENABLE_REAL_ROUTING`, `ENABLE_REAL_TICKETING`, `ENABLE_REAL_TTS`, and `ENABLE_AFFILIATE_LINKS`. All default to `false`.
- External-call safety: `ALLOW_EXTERNAL_CALLS=false` blocks live provider requests even if a real provider flag is accidentally enabled. This includes managed-auth JWKS/provider metadata lookups when `AUTH_PROVIDER` is not `dev`. `ENABLE_INTEGRATION_TESTS=false` keeps standard `APP_ENV=test` runs blocked. `ENABLE_STAGED_INTERNAL_LLM_TESTING=false` and `ENABLE_INTERNAL_ACCESS_GATE=false` keep `APP_ENV=internal` live LLM usage blocked unless explicitly approved later. `EXTERNAL_CALL_ALLOWED_ENVIRONMENTS=production` means development and test runs cannot call live providers unless explicitly added for a deliberate integration test run.
- Durable usage guardrails: `ENABLE_DURABLE_USAGE_CONTROLS`, `ANONYMOUS_ITINERARY_GENERATIONS_PER_MINUTE`, `ANONYMOUS_ITINERARY_GENERATIONS_PER_DAY`, `REGISTERED_USER_ITINERARY_GENERATIONS_PER_MINUTE`, `REGISTERED_USER_ITINERARY_GENERATIONS_PER_DAY`, `SUBSCRIBER_CHAT_MESSAGES_PER_MINUTE`, `SUBSCRIBER_CHAT_MESSAGES_PER_DAY`, `PROVIDER_DAILY_REQUEST_CEILING`, `PROVIDER_DAILY_COST_CEILING_USD`, `USAGE_COUNTER_RETENTION_DAYS`, `ITINERARY_GENERATION_MAX_DAYS`, `LLM_MAX_INPUT_CHARS`, `LLM_MAX_OUTPUT_TOKENS`, `LLM_MAX_LIVE_CALLS_PER_REQUEST`, `LLM_DAILY_LIVE_REQUEST_CEILING`, `VECTOR_SEARCH_MAX_RESULTS`, `POI_VERIFICATION_MAX_BATCH_SIZE`, `ROUTING_MAX_STOPS`, and `TICKETING_LOOKUP_MAX_REQUESTS_PER_ITINERARY`. Deployed environments require durable DB-backed counters at startup; local development may use the in-memory fallback.
- Auth flags: `ENABLE_AUTH`, `AUTH_PROVIDER`, `AUTH_JWT_ISSUER`, `AUTH_JWT_AUDIENCE`, `AUTH_JWT_ALGORITHMS`, `AUTH_JWKS_URL`, `AUTH_PROVIDER_METADATA_URL`, claim mapping variables, `AUTH_REQUIRED_FOR_USER_FEATURES`, and `AUTH_ALLOW_DEV_USER_FALLBACK`.
- `CORS_ALLOWED_ORIGINS`: comma-separated frontend origins. Local default is `http://localhost:5173,http://127.0.0.1:5173`; production default is empty and wildcard origins are ignored.
- Provider placeholders: `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL_NAME`, `LLM_BASE_URL`, `VECTOR_DB_PROVIDER`, `VECTOR_DB_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, `POI_PROVIDER`, `POI_VERIFICATION_PROVIDER`, `POI_PROVIDER_API_KEY`, `GOOGLE_PLACES_API_KEY`, `POI_VERIFICATION_API_KEY`, `ROUTING_PROVIDER`, `ROUTING_API_KEY`, `OPENROUTESERVICE_API_KEY`, `TICKETING_PROVIDER`, `TICKETING_API_KEY`.

Example local values are provided in `.env.example`. Production should set explicit frontend origins, disable admin/debug/mock routes unless intentionally operating a protected internal environment, and keep all provider credentials outside the repository.

Environment templates are available for local, test, beta/staging, and production planning:

- Backend/root: `.env.example`, `.env.test.example`, `.env.beta.example`, `.env.production.example`
- Frontend: `frontend/.env.example`, `frontend/.env.beta.example`, `frontend/.env.production.example`

Beta dry-run instructions live in `docs/beta-deployment-runbook.md`.

Standard tests are safe by default and should run without real API keys:

```bash
cd backend
..\venv\Scripts\python.exe -m pytest

cd ..\frontend
npm test
```

Limit and quota failures return provider-neutral error codes such as `rate_limited`, `quota_exceeded`, `input_too_large`, `unsupported_batch_size`, `too_many_stops`, and `cost_limit_exceeded`; `429` responses include `Retry-After` when the failing window is known. The frontend displays the safe backend message and preserves retry-after seconds on `ApiError`.

Future live integration tests must be opt-in and should set all of these intentionally for that run only:

```bash
APP_ENV=test
ENABLE_INTEGRATION_TESTS=true
ALLOW_EXTERNAL_CALLS=true
ENABLE_REAL_<PROVIDER>=true
EXTERNAL_CALL_ALLOWED_ENVIRONMENTS=test
```

Current auth foundation:

- Auth is disabled by default, so anonymous destination/book browsing, public repository browsing, and basic public itinerary generation still work.
- When `ENABLE_AUTH=true` and `AUTH_REQUIRED_FOR_USER_FEATURES=true`, user-specific endpoints require a bearer token.
- Local/test development supports mock bearer tokens: `dev:<user_id>:<roles>:<subscription_status>`.
- Auth0 is the selected managed auth provider. The frontend uses `@auth0/auth0-vue` for SPA login, callback processing, session restoration, silent access-token acquisition, and logout.
- Managed JWT validation is available for Auth0 through the provider-neutral backend contract using configured issuer, audience, algorithms, and either `AUTH_JWKS_URL` or `AUTH_PROVIDER_METADATA_URL`; JWKS/provider metadata retrieval is blocked unless `ALLOW_EXTERNAL_CALLS=true` and `APP_ENV` is listed in `EXTERNAL_CALL_ALLOWED_ENVIRONMENTS`.
- `GET /api/me` syncs the current authenticated subject to a local user profile.
- Development fallback to `dev-reader` is allowed only in development/test when `AUTH_ALLOW_DEV_USER_FALLBACK=true`; beta/staging/production reject it.
- Deployed environments (`internal`, `beta`, `staging`, and `production`) fail startup unless auth is enabled with a managed provider label, issuer, audience, production JWT algorithms, JWKS or provider metadata, `AUTH_REQUIRED_FOR_USER_FEATURES=true`, `AUTH_ALLOW_DEV_USER_FALLBACK=false`, `ALLOW_EXTERNAL_CALLS=true`, and the current environment listed in `EXTERNAL_CALL_ALLOWED_ENVIRONMENTS`.
- Production must not use `AUTH_PROVIDER=dev`; configure and stage-test a managed provider before production traffic.
- Itinerary detail and narration are public for public repository rows and owner/admin-only for private or unlisted rows. Unauthorized private itinerary IDs return `404`, matching missing-resource behavior.

Frontend Auth0 configuration:

- `VITE_AUTH_PROVIDER=auth0`
- `VITE_AUTH0_DOMAIN`
- `VITE_AUTH0_CLIENT_ID`
- `VITE_AUTH0_AUDIENCE`
- `VITE_AUTH0_CALLBACK_URL`, normally `/auth/callback` on the frontend origin
- `VITE_AUTH0_LOGOUT_RETURN_URL`
- `VITE_AUTH0_USE_REFRESH_TOKENS=false` by default; the SDK uses in-memory token cache and Auth0 silent session checks.
- `VITE_AUTH0_CACHE_LOCATION=memory` by default; use `localstorage` only after accepting the higher XSS persistence risk.

Staging and production must use separate Auth0 tenants/apps, audiences, callback URLs, logout URLs, allowed web origins, and backend issuer/JWKS settings. The frontend obtains an Auth0 access token only when an SDK-authenticated session exists, attaches `Authorization: Bearer <access-token>` centrally through the API client, calls `/api/me`, and treats the returned backend profile as the Litinerary identity. Public anonymous endpoints continue without a bearer token. Deployed UI does not expose development-token login.

Initialize the schema with Alembic:

```bash
cd backend
..\venv\Scripts\python.exe -m alembic upgrade head
```

Seed the current mock catalog, POIs, and public itineraries into the database:

```bash
cd backend
..\venv\Scripts\python.exe -m scripts.seed_database
```

The backend endpoints still fall back to Phase 1 mock data if no seeded database is available. Once seeded, destination lookup, book lookup, public itinerary listing/detail, exact-match lookup, partial-match lookup, and saved generated/adapted itineraries use the database.

Repository generation flow with a seeded database:

1. Search for an exact public itinerary by city, book, duration, and transportation mode.
2. If found, return that itinerary as an exact match.
3. If not found, search for a partial public match by city and book.
4. If found, adapt the itinerary, save the adapted route, and return it.
5. If no match exists, generate a deterministic mock itinerary from seeded POIs, save it, and return it.

## Vector Service Foundation

The backend includes a provider-neutral vector service layer for future Pinecone, Milvus, Qdrant, or similar integrations. Qdrant is the first real adapter boundary because it is local/dev-friendly and can be self-hosted, but current local development still uses a deterministic fake provider by default:

- Fake embeddings are generated locally and deterministically.
- Vectors are stored in an in-memory fake store.
- Metadata filtering and similarity search are implemented without external calls in the fake store.
- User preferences and reviews are mirrored into the fake vector layer after relational saves.

Configured placeholders:

- `LITINERARY_VECTOR_PROVIDER`, default `fake`
- `VECTOR_DB_PROVIDER`, default `fake`; set to `qdrant` only with `ENABLE_REAL_VECTOR_DB=true`
- `QDRANT_URL` or `VECTOR_DB_URL`, required only when real Qdrant is enabled
- `QDRANT_API_KEY` or `VECTOR_DB_API_KEY`, optional for local Qdrant and required if your Qdrant deployment needs it
- `QDRANT_COLLECTION_PREFIX`, default `litinerary`
- `QDRANT_TIMEOUT_SECONDS`, default `5`
- `LITINERARY_VECTOR_DIMENSION`, default `16`
- `LITINERARY_VECTOR_STORE_PATH`, optional local JSON fake-store persistence path

Vector collection concepts exist for user preferences, user reviews, itineraries, book-to-city mappings, and POIs. Tests do not make external Vector DB calls; Qdrant unit tests inject a recording transport. No external embedding API is connected yet.

Print the future vector backfill plan without writing data:

```bash
cd backend
..\venv\Scripts\python.exe -m scripts.vector_backfill_plan
```

## LLM Provider Boundary

Local development still uses `LITINERARY_AI_PROVIDER=fake` and `ENABLE_REAL_LLM=false`. The mock AI pipeline is deterministic, uses catalog summaries and seeded POIs only, and does not call an external LLM.

The first real LLM boundary is an OpenAI-compatible JSON adapter. It is provider-neutral at the Litinerary service layer and can later point at OpenAI, Azure OpenAI, or a compatible gateway through `LLM_BASE_URL`:

```powershell
$env:APP_ENV="development"
$env:ENABLE_REAL_LLM="true"
$env:ALLOW_EXTERNAL_CALLS="true"
$env:EXTERNAL_CALL_ALLOWED_ENVIRONMENTS="development"
$env:LITINERARY_AI_PROVIDER="openai_compatible"
$env:LLM_PROVIDER="openai_compatible"
$env:LLM_API_KEY="<secret>"
$env:LLM_MODEL_NAME="gpt-4.1-mini"
$env:LLM_ALLOWED_ENVIRONMENTS="development"
```

Required live LLM gates are `ENABLE_REAL_LLM=true`, `LITINERARY_AI_PROVIDER=openai_compatible` or `LLM_PROVIDER=openai_compatible`, `LLM_API_KEY`, `LLM_MODEL_NAME`, `ALLOW_EXTERNAL_CALLS=true`, and an `APP_ENV` present in both `LLM_ALLOWED_ENVIRONMENTS` and `EXTERNAL_CALL_ALLOWED_ENVIRONMENTS`. Secrets must come from environment or secret storage; do not place real keys in source files, examples, tests, logs, or shell history you intend to share.

Optional settings include `LLM_BASE_URL`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_TOKENS`, `LLM_MAX_RETRIES`, `LLM_MONTHLY_BUDGET_USD`, `LLM_ALLOWED_ENVIRONMENTS`, `LLM_MAX_LIVE_CALLS_PER_REQUEST`, `LLM_DAILY_LIVE_REQUEST_CEILING`, `LLM_DAILY_ESTIMATED_SPEND_CEILING_USD`, `LLM_LATENCY_ALERT_THRESHOLD_MS`, and `LLM_ERROR_RATE_ALERT_THRESHOLD_PERCENT`. Standard `APP_ENV=test` runs block real LLM startup unless `ENABLE_INTEGRATION_TESTS=true`, and even then the environment must be present in both allow-lists. `APP_ENV=internal` also requires `ENABLE_STAGED_INTERNAL_LLM_TESTING=true` and `ENABLE_INTERNAL_ACCESS_GATE=true`; staged internal testing is still no-go until the readiness blockers are closed.

Before any real LLM transport call, grounding checks require safe source types, reject full-text metadata fields, block copyrighted full text, require source licensing/copyright context where relevant, and require POIs to have usable coordinates plus verification/provenance context. Judge validation returns structured reasons, warnings, confidence, and required fixes. Standard tests inject fake LLM transports and do not make network calls.

Controlled non-production LLM smoke testing is allowed only with the gates above and with vector DB, POI, routing, ticketing, affiliate, TTS, and managed auth live-provider flags left disabled unless separately approved. Public or beta user-facing live LLM itinerary generation remains blocked pending provider observability, staged POI/routing validation, and an approved live-provider rollout plan.

Live LLM operational documents:

- `docs/live-llm-smoke-test-runbook.md`
- `docs/live-llm-operational-controls.md`
- `docs/live-llm-smoke-test-evidence-template.md`
- `docs/live-llm-rollback-drill.md`
- `docs/generated-itinerary-quality-review-template.md`
- `docs/internal-live-llm-test-plan.md`
- `docs/internal-staged-testing-readiness-report.md`

For local credential handoff before a controlled smoke test, prefer copying `.env.development.local.example` to ignored `.env.development.local`, then run `scripts/live_llm_smoke_preflight.ps1`. The backend can be started for that smoke window with `scripts/live_llm_smoke_backend.ps1`, which loads the same ignored local file after preflight passes.

## POI Verification Provider Boundary

Local development still uses `LITINERARY_POI_VERIFICATION_PROVIDER=mock` and `ENABLE_REAL_POI_PROVIDER=false`. The mock adapter is deterministic, verifies against seeded POIs only, and does not make external calls.

Google Places is the first real POI adapter boundary because the SDD names Google Places API as a POI Search API option and it can return place identity, coordinates, addresses, opening-hours summaries, and public place URLs through one provider-specific adapter. To instantiate it later, set:

```powershell
$env:ENABLE_REAL_POI_PROVIDER="true"
$env:POI_PROVIDER="google_places"
$env:GOOGLE_PLACES_API_KEY="<secret>"
```

Optional POI settings include `POI_PROVIDER_BASE_URL`, `POI_PROVIDER_TIMEOUT_SECONDS`, `POI_PROVIDER_RESULT_LIMIT`, `POI_PROVIDER_MIN_CONFIDENCE`, `POI_PROVIDER_REGION_CODE`, and `POI_PROVIDER_LANGUAGE_CODE`. The default confidence threshold is `0.82`; lower-confidence and no-match results stay in `needs_review`. Standard tests inject fake Google transports and do not make network calls.

## Routing Provider Boundary

The frontend map uses Leaflet with OpenStreetMap tiles, so OpenRouteService is the first real routing adapter boundary. Local development still uses `ROUTING_PROVIDER=mock` and `ENABLE_REAL_ROUTING=false`; mock routing emits straight-line distance, duration, and geometry estimates without network calls.

To instantiate OpenRouteService later:

```powershell
$env:ENABLE_REAL_ROUTING="true"
$env:ROUTING_PROVIDER="openrouteservice"
$env:OPENROUTESERVICE_API_KEY="<secret>"
```

Optional routing settings include `ROUTING_BASE_URL`, `ROUTING_TIMEOUT_SECONDS`, `ROUTING_MAX_STOPS`, `ROUTING_SUPPORTED_MODES`, and `ROUTING_FALLBACK_BEHAVIOR`. The adapter maps `walking` to `foot-walking` and `car_taxi` to `driving-car`. OpenRouteService transit is not enabled by default; `public_transport` uses mock fallback when `ROUTING_FALLBACK_BEHAVIOR=mock` or raises a normalized provider error when set to `error`. Standard tests inject fake routing transports and do not make network calls.

Run the backend locally:

```bash
cd backend
..\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Useful backend endpoints:

- `GET /api/health`
- `GET /api/readiness`
- `GET /api/destinations`
- `GET /api/books?city_id=london`
- `POST /api/itinerary/generate`
- `GET /api/me`
- `GET /api/itineraries`
- `GET /api/itineraries/{itinerary_id}`
- `POST /api/users`
- `GET /api/users/{user_id}`
- `POST /api/users/{user_id}/preferences`
- `POST /api/users/{user_id}/bookmarks/{itinerary_id}`
- `DELETE /api/users/{user_id}/bookmarks/{itinerary_id}`
- `GET /api/users/{user_id}/bookmarks`
- `POST /api/users/{user_id}/reviews`

Development/admin-only endpoints are guarded by backend configuration:

- Book ingestion: `/api/admin/ingestion/*`
- POI verification: `/api/admin/poi/*`
- Seed data: `/api/admin/seed/*`
- Debug recommendations: `/api/users/{user_id}/recommendations/mock`

Destructive seed-data routes, including `POST /api/admin/seed/reset` and `POST /api/admin/seed/import`, are blocked in production even if admin routes are explicitly enabled. Use the CLI seed/reset tools only against local development databases.

Backend observability is local-only by default. API responses include an `X-Request-ID` header, request start/end events are logged through the `litinerary` logger, and provider telemetry hooks record provider type, provider name, operation, success/failure, latency, warning count, estimated cost, and error type when available. Logs must not include secrets, raw prompts, copyrighted text, bearer tokens, or provider credentials.

`GET /api/readiness` returns safe beta-readiness checks for database connectivity, mock/real provider mode, feature flags, external-call policy, whether provider credentials and required non-secret config are present, and whether the selected LLM environment gates are satisfied. It exposes booleans only for credentials and never returns secret values.

## Running the App Locally

Start the backend in one terminal:

```bash
cd backend
..\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend in another terminal:

```bash
cd frontend
npm run dev
```

Then open the Vite URL shown in the frontend terminal. The intended MVP path is:

1. Select a destination.
2. Select a book.
3. Configure duration and transportation.
4. Generate the itinerary.
5. View the route summary, map, and text itinerary.
6. Browse the public itinerary repository.

## Testing

Backend tests use `pytest` and FastAPI `TestClient` against deterministic local mock data:

```bash
cd backend
..\venv\Scripts\python.exe -m pytest
```

Pytest artifacts are centralized under `tests/.artifacts/`:

- `tests/.artifacts/logs/` stores pytest runtime logs and captured local smoke/backend logs.
- `tests/.artifacts/reports/` stores JUnit XML and other machine-readable test reports.
- `tests/.artifacts/coverage/` stores coverage.py data, XML, and HTML output.
- `tests/.artifacts/pytest-cache/` stores pytest cache data.
- `tests/.artifacts/pytest-tmp/` stores the normal pytest basetemp directory.
- `tests/.artifacts/tmp/` is reserved for ad hoc harness-specific temporary files.

The artifact tree is ignored by Git except for `.gitkeep` placeholders. To clean local artifacts, remove the contents of `tests/.artifacts/logs/`, `tests/.artifacts/reports/`, `tests/.artifacts/coverage/`, and `tests/.artifacts/tmp/` while leaving the `.gitkeep` files in place.

Run only the backend smoke path:

```bash
cd backend
..\venv\Scripts\python.exe -m pytest tests\test_smoke_happy_path.py
```

Run backend negative-path and security-focused tests:

```bash
cd backend
..\venv\Scripts\python.exe -m pytest tests\test_auth_foundation.py tests\test_negative_security_paths.py tests\test_environment_guards.py
```

Run backend data-model migration/readiness tests:

```bash
cd backend
..\venv\Scripts\python.exe -m pytest tests\test_model_metadata_migrations.py
```

Run backend vector adapter boundary tests:

```bash
cd backend
..\venv\Scripts\python.exe -m pytest tests\test_vector_service.py tests\test_qdrant_vector_adapter.py
```

Frontend tests use Vitest, jsdom, Vue Test Utils, and mocked API calls:

```bash
cd frontend
npm test
```

Run only the frontend happy-path smoke test:

```bash
cd frontend
npm run test:smoke
```

Frontend negative-path coverage is included in the store/API unit tests:

```bash
cd frontend
npm test
```

Convenience scripts from the repository root:

```powershell
.\scripts\test_backend.ps1
.\scripts\test_frontend.ps1
.\scripts\test_smoke.ps1
.\scripts\beta_dry_run.ps1
```

The smoke path covers the MVP journey from destination and book selection through itinerary generation, mapped/text itinerary display, public repository detail, and Phase 2 development-user preference, bookmark, and review actions.

The beta dry-run script validates beta-safe config, checks migration status, runs tests, starts a temporary backend, verifies `/api/health` and `/api/readiness`, confirms admin routes are disabled, and builds the frontend. It does not deploy or connect live providers.

The test suites do not require real LLM, vector database, map provider, ticketing provider, auth provider, or external API calls.

Security-sensitive limitations before production auth provider integration:

- User-specific endpoints can be protected by the feature-flagged auth foundation, and managed JWT validation exists, but no real external auth provider is selected or connected in the templates.
- Admin/development routes are protected by environment/config guards and require authenticated admin/developer identity when auth is enabled.
- Debug/mock recommendation routes are development-only and can be disabled with `ENABLE_DEBUG_ROUTES=false`.
- Destructive seed reset/import routes are blocked in production mode.
- Ownership/visibility checks are enforced server-side for itinerary detail/narration, subscriber private itinerary creation, user bookmark/review operations, and bookmark list filtering. Dedicated private itinerary CRUD and sharing/unlisted UI remain future work.

Provider integration and production readiness docs:

- `docs/provider-adapters.md`
- `docs/production-readiness.md`

## MVP Limitations

- Data is local mock data, not production content.
- Itinerary generation is deterministic and mock-based.
- Public repository persistence is SQLite-backed after database initialization and seeding; otherwise the Phase 1 in-memory mock fallback is used.
- User accounts are backed by the verified auth subject returned through `/api/me`. The frontend has Auth0 SPA login/session/logout integration, but real Auth0 tenant/app values are not committed and real staging E2E remains blocked until external Auth0 resources are provisioned.
- Vector search uses deterministic fake embeddings and an in-memory store by default. A gated Qdrant adapter boundary exists, but no real Vector DB is enabled without `ENABLE_REAL_VECTOR_DB=true`.
- Map lines use day-level route geometry when available and straight-line mock geometry otherwise. Production route optimization, transit routing, and turn-by-turn UX remain future work.
- Ticketing notes are static mock text, not live ticket inventory or booking links. The Google Places POI adapter may preserve a provider-supplied public place URL, but ticket inventory remains out of scope for the future ticketing adapter.
- Real LLM, Vector DB, POI, and routing adapter boundaries exist behind feature flags, but standard local flows still use fake/mock providers. Auth0 frontend integration exists with placeholder configuration only; e-commerce, affiliate, payment, and production ticketing integration are not connected.

## Future Implementation Phases

- Replace mock data with ingestion-backed literary location data.
- Add dedicated user-owned itinerary save/edit/share flows on top of the existing ownership boundary.
- Integrate vector search and personalization after the MVP flow is stable.
- Add LLM generation and judge review with guardrails and deterministic test fixtures.
- Add production routing, richer map behavior, and verified POI/ticketing data.
- Add accounts, subscriber chat, reviews, voice narration, affiliate/e-commerce flows, and payment integrations in later phases.
