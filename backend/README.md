# Litinerary Backend

This directory contains the FastAPI backend for the Litinerary API.

## Layout

- `app/main.py` creates the FastAPI application and exposes a health-check endpoint.
- `app/api/` contains API route modules.
- `app/core/` contains settings, database configuration, and shared infrastructure.
- `app/models/` contains SQLAlchemy database models.
- `app/schemas/` will contain Pydantic request and response schemas.
- `app/services/` contains business logic, database mappers, and future integration boundaries.
- `app/data/` contains Phase 1 mock data used for fallback behavior and database seeding.
- `migrations/` contains Alembic migration support.
- `scripts/seed_database.py` initializes local mock data in the persistent database.

## Local Database

SQLite is the default local development database:

```bash
..\venv\Scripts\python.exe -m alembic upgrade head
..\venv\Scripts\python.exe -m scripts.seed_database
```

Set `LITINERARY_DATABASE_URL` to point at another SQLAlchemy-supported database URL for experiments. Do not commit production credentials.

## Environment Configuration

Configuration lives in `app/core/config.py` and is read from environment variables. Local development and tests are intentionally easy to run; production defaults are restrictive.

Recommended local values:

```powershell
$env:APP_ENV="development"
$env:DEBUG="true"
$env:ENABLE_ADMIN_ROUTES="true"
$env:ENABLE_DEBUG_ROUTES="true"
$env:ENABLE_MOCK_SERVICES="true"
$env:ENABLE_STAGED_INTERNAL_LLM_TESTING="false"
$env:ENABLE_INTERNAL_ACCESS_GATE="false"
$env:ENABLE_REAL_LLM="false"
$env:ENABLE_REAL_VECTOR_DB="false"
$env:ENABLE_REAL_POI_PROVIDER="false"
$env:ENABLE_REAL_ROUTING="false"
$env:ENABLE_REAL_TICKETING="false"
$env:ENABLE_AUTH="false"
$env:AUTH_PROVIDER="dev"
$env:AUTH_REQUIRED_FOR_USER_FEATURES="false"
$env:AUTH_ALLOW_DEV_USER_FALLBACK="true"
$env:CORS_ALLOWED_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"
```

Production expectations:

- Set `APP_ENV=production`.
- Set `DEBUG=false`.
- Set explicit `CORS_ALLOWED_ORIGINS`; do not use `*`.
- Leave `ENABLE_ADMIN_ROUTES=false` unless routes are protected by a separate deployment boundary.
- Leave `ENABLE_DEBUG_ROUTES=false`.
- Leave `ENABLE_MOCK_SERVICES=false` unless intentionally running a protected mock environment.
- Leave all `ENABLE_REAL_*` provider flags disabled until the matching adapter contract tests, cost controls, secrets, and monitoring are in place.
- Leave `ENABLE_AUTH=false` until a real provider is configured. When enabling auth, configure `AUTH_PROVIDER`, `AUTH_JWT_ISSUER`, `AUTH_JWT_AUDIENCE`, `AUTH_JWT_ALGORITHMS`, and either `AUTH_JWKS_URL` or `AUTH_PROVIDER_METADATA_URL`. Managed-auth JWKS/provider metadata lookups are live external calls and remain blocked unless `ALLOW_EXTERNAL_CALLS=true` and the current `APP_ENV` is listed in `EXTERNAL_CALL_ALLOWED_ENVIRONMENTS`.
- Never use `AUTH_PROVIDER=dev` as production authentication.
- Keep provider credentials out of the repository.

Beta/staging dry-run expectations:

- Set `APP_ENV=beta` or `APP_ENV=staging`.
- Set `DEBUG=false`.
- Set `ENABLE_ADMIN_ROUTES=false` and `ENABLE_DEBUG_ROUTES=false`.
- Keep `ENABLE_MOCK_SERVICES=true` for the current mock-only beta dry run.
- Keep all real provider flags and `ALLOW_EXTERNAL_CALLS` disabled.
- Use exact `CORS_ALLOWED_ORIGINS`.
- Keep provider credentials empty unless a future live integration gate explicitly approves them.

Staged internal live LLM testing uses `APP_ENV=internal` and is still no-go. The environment label exists only so staged-internal configuration can fail closed: live LLM calls require `ENABLE_STAGED_INTERNAL_LLM_TESTING=true` and `ENABLE_INTERNAL_ACCESS_GATE=true` in addition to every normal LLM and external-call gate. Do not set either flag for local mock/demo runs, controlled smoke tests, beta, staging, or production unless a later readiness review approves the staged internal test.

For controlled local live LLM smoke testing, prefer copying `.env.development.local.example` to ignored `.env.development.local`. The preflight script loads `.env.development.local` first, then `.env.local`, and reports only boolean credential presence. Use `scripts/live_llm_smoke_backend.ps1` from the repository root to start the backend with the same local env source after preflight passes.

Validate beta configuration from this directory:

```powershell
..\venv\Scripts\python.exe -m scripts.validate_beta_config --profile beta
```

Run the full repository dry run from the project root:

```powershell
.\scripts\beta_dry_run.ps1
```

Provider placeholder variables exist for future integrations but do not connect real services yet:

- `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL_NAME`, `LLM_BASE_URL`, plus compatibility alias `LITINERARY_AI_PROVIDER`.
- `VECTOR_DB_PROVIDER`, `VECTOR_DB_API_KEY`, plus compatibility alias `LITINERARY_VECTOR_PROVIDER`.
- `POI_PROVIDER` or `POI_VERIFICATION_PROVIDER`, API key via `POI_PROVIDER_API_KEY`, `GOOGLE_PLACES_API_KEY`, or `POI_VERIFICATION_API_KEY`, plus compatibility alias `LITINERARY_POI_VERIFICATION_PROVIDER`.
- `ROUTING_PROVIDER`, API key via `ROUTING_API_KEY` or `OPENROUTESERVICE_API_KEY`.
- `TICKETING_PROVIDER`, `TICKETING_API_KEY`.

Auth foundation variables:

- `ENABLE_AUTH`: enables the backend auth boundary.
- `AUTH_REQUIRED_FOR_USER_FEATURES`: requires auth for profile, preferences, bookmarks, reviews, and mock recommendations.
- `AUTH_PROVIDER`: `dev` for local/test tokens, or a provider label such as `oidc` for managed JWT validation.
- `AUTH_JWT_ISSUER`, `AUTH_JWT_AUDIENCE`, `AUTH_JWT_ALGORITHMS`: required for managed-provider JWT validation.
- `AUTH_JWKS_URL` or `AUTH_PROVIDER_METADATA_URL`: required for managed-provider signature validation.
- Managed-provider JWKS/provider metadata requests follow the global external-call policy: keep `ALLOW_EXTERNAL_CALLS=false` for standard local/test/demo runs.
- Claim mapping: `AUTH_USER_ID_CLAIM`, `AUTH_ROLES_CLAIM`, `AUTH_SUBSCRIPTION_CLAIM`, `AUTH_EMAIL_CLAIM`, and `AUTH_DISPLAY_NAME_CLAIM`.
- `AUTH_ALLOW_DEV_USER_FALLBACK`: allows missing-token fallback to `dev-reader` only in development/test; deployed environments reject it.

Local/test mock token format:

```text
Authorization: Bearer dev:<user_id>:<comma-separated-roles>:<subscription_status>
```

When a non-mock provider is configured without credentials, startup validation notes are available from settings, but local mock development is not blocked.

The existing MVP endpoints preserve Phase 1 behavior. When the database has been seeded, repository lookup and save operations use persisted rows; otherwise the app falls back to mock data.

The persisted public repository flow is:

1. Exact match by destination, book, duration, and transportation mode.
2. Partial match by destination and book.
3. Adapt and save a partial match when possible.
4. Generate and save a deterministic mock itinerary when no match exists.

Saved generated and adapted itineraries include source type, source itinerary ID when applicable, adaptation notes, and public visibility.

## Seed Data Admin Tools

Development-only seed data management lives in `app/services/seed_manager.py`. These tools are for local development databases only; there is no production admin authentication yet, and destructive reset/import actions must not be exposed in the user-facing frontend.

CLI-style commands from the `backend` directory:

```bash
..\venv\Scripts\python.exe -m scripts.seed
..\venv\Scripts\python.exe -m scripts.reset_dev_db
..\venv\Scripts\python.exe -m scripts.export_seed_data .\tmp\seed-export.json
..\venv\Scripts\python.exe -m scripts.import_seed_data .\tmp\seed-export.json
..\venv\Scripts\python.exe -m scripts.validate_seed_data
..\venv\Scripts\python.exe -m scripts.validate_seed_data --path .\tmp\seed-export.json
```

Development-only admin endpoints:

- `POST /api/admin/seed/reset`
- `GET /api/admin/seed/export`
- `POST /api/admin/seed/import`
- `GET /api/admin/seed/validate`

These endpoints require `ENABLE_ADMIN_ROUTES=true`. The destructive reset/import endpoints are blocked whenever `APP_ENV=production`, even if admin routes are explicitly enabled. Prefer the CLI commands above for local seed/reset workflows.

## Negative-Path and Security Tests

Run the focused backend security/negative suite from this directory:

```bash
..\venv\Scripts\python.exe -m pytest tests\test_auth_foundation.py tests\test_negative_security_paths.py tests\test_environment_guards.py
```

These tests cover invalid public API inputs, malformed generation payloads, missing POI data, mock judge rejection, invalid review/preference/bookmark operations, duplicate bookmark idempotency, current user-path scoping behavior, admin/debug route guard behavior, CORS production wildcard handling, and provider configuration failures.

Provider contract tests:

```bash
..\venv\Scripts\python.exe -m pytest tests\test_provider_contracts.py
```

Provider contracts and production-readiness gates are documented in `..\docs\provider-adapters.md` and `..\docs\production-readiness.md`.

Known limitations documented by tests:

- A provider-neutral auth foundation exists behind feature flags, including local/test tokens and managed JWT validation with mocked JWKS tests. No real provider is selected or connected in committed config.
- User endpoints such as `/api/users/{user_id}/preferences` can require current-user checks when `ENABLE_AUTH=true` and `AUTH_REQUIRED_FOR_USER_FEATURES=true`.
- Admin/development endpoints use config guards and require authenticated admin/developer identity when auth is enabled.
- The mock recommendation route is a debug route and must remain disabled outside intentional development/test use.

Seed export/import uses a JSON payload with `destinations`, `books`, `pois`, and `itineraries`. Validation checks required destination/book/POI text fields, valid book-to-destination links, POI destination/book links, itinerary city/book relationships, supported transportation modes, ordered day stops, stop-to-POI references, and required map coordinates.

`reset-dev-db` and `POST /api/admin/seed/reset` clear local development data, including users, preferences, reviews, bookmarks, ingestion jobs, generated itineraries, POIs, books, and destinations, then reload the bundled seed data.

## Mock AI Pipeline

The backend has provider-neutral AI boundaries in `app/services/ai_types.py` and deterministic mock implementations in `app/services/mock_ai_service.py`. The boundaries cover:

- Book ingestion.
- Summary and location extraction.
- POI extraction.
- POI verification preparation.
- Itinerary generation.
- Itinerary adaptation.
- LLM judge validation.
- Review feedback processing.

Local development uses `LITINERARY_AI_PROVIDER=fake`. The first real LLM boundary is `LLM_PROVIDER=openai_compatible`, disabled unless `ENABLE_REAL_LLM=true`.

The mock pipeline uses catalog summaries, public-domain-safe placeholders, and local mock POI data only. It does not ingest copyrighted full text and does not call any external LLM, place verification, routing, or mapping provider.

OpenAI-compatible adapter enablement for later integration:

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

This is approved only for controlled non-production smoke testing. Leave `ENABLE_REAL_VECTOR_DB`, `ENABLE_REAL_POI_PROVIDER`, `ENABLE_REAL_ROUTING`, `ENABLE_REAL_TICKETING`, `ENABLE_AFFILIATE_LINKS`, `ENABLE_REAL_TTS`, and managed-auth live-provider behavior disabled unless each boundary is separately configured and approved.

Required live LLM gates:

- `ENABLE_REAL_LLM=true`
- `LITINERARY_AI_PROVIDER=openai_compatible` or `LLM_PROVIDER=openai_compatible`
- `LLM_API_KEY` from environment/secret storage only
- `LLM_MODEL_NAME`
- `ALLOW_EXTERNAL_CALLS=true`
- Current `APP_ENV` listed in `EXTERNAL_CALL_ALLOWED_ENVIRONMENTS`
- Current `APP_ENV` listed in `LLM_ALLOWED_ENVIRONMENTS`

Optional settings:

- `LLM_BASE_URL`, default `https://api.openai.com/v1`
- `LLM_TIMEOUT_SECONDS`, default `20`
- `LLM_MAX_TOKENS`, default `1200`
- `LLM_OUTPUT_TOKEN_PARAMETER`, default `max_tokens`; use `max_completion_tokens`
  for GPT-5-family Chat Completions models.
- `LLM_MAX_RETRIES`, default `0`
- `LLM_MONTHLY_BUDGET_USD`, placeholder for future spend enforcement
- `LLM_MAX_LIVE_CALLS_PER_REQUEST`, default `4`
- `LLM_DAILY_LIVE_REQUEST_CEILING`, default `4`
- `LLM_DAILY_ESTIMATED_SPEND_CEILING_USD`, placeholder for future spend monitoring
- `LLM_LATENCY_ALERT_THRESHOLD_MS`, default `5000`
- `LLM_ERROR_RATE_ALERT_THRESHOLD_PERCENT`, default `10`
- `LLM_ALLOWED_ENVIRONMENTS`, default `development,production`; standard `APP_ENV=test` is blocked unless `ENABLE_INTEGRATION_TESTS=true` and both environment allow-lists include `test`
- `APP_ENV=internal` requires `ENABLE_STAGED_INTERNAL_LLM_TESTING=true` and `ENABLE_INTERNAL_ACCESS_GATE=true`, and remains no-go until staged-readiness blockers are closed

Public or beta user-facing live LLM itinerary generation is still not approved. Before that, add production auth, durable rate and cost enforcement, monitoring/alerting, staged provider runbooks, and validation of POI/routing quality under realistic inputs.

Grounding rules run before any real LLM provider call:

- Only `public_domain_text_reference`, `summary_document`, `manually_curated_location_list`, and `metadata_only` sources are allowed.
- Metadata fields that look like raw/full text are rejected.
- Copyrighted full text is blocked; copyrighted summaries are allowed only with `summary_only` processing.
- Source license or known copyright status is required where relevant.
- POIs used for itinerary tasks need usable coordinates, verification state, and provenance metadata or candidate source notes.
- Grounding context is represented as structured request data, not scattered prompt strings.

The generation pipeline is:

1. Repository exact-match lookup.
2. Repository partial-match adaptation, or deterministic mock candidate generation.
3. Mock judge validation.
4. Save approved generated/adapted itinerary.
5. Return the approved itinerary to the frontend.

The judge validates required itinerary fields, supported transportation modes, non-empty days, reasonable daily stop counts, stop ordering, stop text, POI coordinates, POI verification state, route metadata, low-confidence/review-needed POIs, provenance, and licensing flags. If the judge rejects a new candidate, the API returns a clear backend error with reasons, warnings, confidence, and required fixes instead of saving the malformed itinerary.

## Book Ingestion Scaffolding

Development-only book ingestion records are modeled with:

- `BookSourceModel`
- `BookIngestionJobModel`
- `BookLocationCandidateModel`
- `BookProcessingArtifactModel`

The safe source types are:

- `public_domain_text_reference`
- `summary_document`
- `manually_curated_location_list`
- `metadata_only`

The ingestion service rejects metadata fields that look like full-text payloads, such as `fullText`, `full_text`, `copyrightedFullText`, or `rawText`. This scaffolding does not upload files, read copyrighted books, call an LLM, or contact external data providers. It only stores safe references, summaries, metadata, and manually curated location hints.

Development-only admin endpoints:

- `POST /api/admin/ingestion/jobs`
- `GET /api/admin/ingestion/jobs`
- `GET /api/admin/ingestion/jobs/{job_id}`
- `POST /api/admin/ingestion/jobs/{job_id}/run`
- `POST /api/admin/ingestion/candidates/{candidate_id}/promote`

These routes require `ENABLE_ADMIN_ROUTES=true`.

Running a job uses deterministic mock extraction. It creates location candidates and processing artifacts, updates job status from `pending` to `processing` to `completed`, and stores extraction notes and warnings. Candidate promotion creates a POI linked to the source book and immediately runs mock verification. High-confidence local matches become `mock_verified`; lower-confidence or malformed candidates remain `needs_review` for manual development review.

## POI Verification Adapters

The backend has provider-neutral POI verification boundaries in `app/services/poi_verification.py`. The adapter interface covers:

- Searching places by name and city.
- Resolving ingestion location candidates to POI verification results.
- Validating coordinates.
- Fetching basic logistics metadata.
- Fetching ticketing URL placeholders.

Local development uses `LITINERARY_POI_VERIFICATION_PROVIDER=mock`. The mock adapter is deterministic, makes no network calls, and matches against local seeded/mock POIs only.

Google Places is the first real POI adapter boundary. It was selected because the SDD explicitly names Google Places API as a POI Search API option and because text search can normalize place identity, addresses, coordinates, opening-hours summaries, and public place URLs without changing route handlers. The adapter lives in `app/services/google_places_poi_adapter.py` and is only instantiated when real POI usage is explicitly enabled:

```powershell
$env:ENABLE_REAL_POI_PROVIDER="true"
$env:POI_PROVIDER="google_places"
$env:GOOGLE_PLACES_API_KEY="<secret>"
```

Required when enabled: `POI_PROVIDER_API_KEY`, `GOOGLE_PLACES_API_KEY`, or `POI_VERIFICATION_API_KEY`.

Optional settings:

- `POI_PROVIDER_BASE_URL`, default `https://places.googleapis.com`
- `POI_PROVIDER_TIMEOUT_SECONDS`, default `5`
- `POI_PROVIDER_RESULT_LIMIT`, default `5`
- `POI_PROVIDER_MIN_CONFIDENCE`, default `0.82`
- `POI_PROVIDER_REGION_CODE`
- `POI_PROVIDER_LANGUAGE_CODE`

Results at or above the confidence threshold become `provider_verified`. Low-confidence or no-match results remain `needs_review`; existing verification notes are preserved and manual review status is not overwritten once marked reviewed. Provider timeout, rate-limit, unavailable, missing config, and invalid-response cases are normalized with provider-neutral `ProviderError` codes.

POIs can carry verification metadata:

- `verification_status`: `unverified`, `mock_verified`, `needs_review`, or `rejected`
- `verification_provider`
- `verification_confidence`
- `verified_name`
- `verified_address`
- `verified_latitude`
- `verified_longitude`
- `opening_hours_note`
- `ticketing_url`
- `verification_notes`

Development-only admin endpoints:

- `POST /api/admin/poi/verify-candidate/{candidate_id}`
- `POST /api/admin/poi/verify/{poi_id}`
- `GET /api/admin/poi/unverified`
- `POST /api/admin/poi/{poi_id}/mark-reviewed`

These routes require `ENABLE_ADMIN_ROUTES=true`.

With the default mock adapter, these endpoints do not contact Google Places, Foursquare, Mapbox, ticketing providers, or any external API.

When `ENABLE_REAL_POI_PROVIDER=true`, the same admin/development endpoints use the selected adapter factory and can persist Google provider provenance, confidence, request/reference ID, source URL, warnings, and `externalProviderUsed=true`. Standard tests inject fake transports and do not make live provider calls. Live Google integration tests are skipped by default until an explicit integration profile is added.

## Routing Provider Adapters

The backend has a provider-neutral routing boundary in `app/services/routing_types.py` and `app/services/routing_service.py`. Local development uses `ROUTING_PROVIDER=mock`. The mock provider computes rough straight-line segment distance and duration, emits straight-line route geometry, and never calls an external routing API.

OpenRouteService is the first real routing adapter boundary because the frontend map is Leaflet/OpenStreetMap based. The adapter lives in `app/services/openrouteservice_routing_adapter.py` and is only instantiated when real routing is explicitly enabled:

```powershell
$env:ENABLE_REAL_ROUTING="true"
$env:ROUTING_PROVIDER="openrouteservice"
$env:OPENROUTESERVICE_API_KEY="<secret>"
```

Required when enabled: `ROUTING_API_KEY` or `OPENROUTESERVICE_API_KEY`.

Optional settings:

- `ROUTING_BASE_URL`, default `https://api.openrouteservice.org`
- `ROUTING_TIMEOUT_SECONDS`, default `5`
- `ROUTING_MAX_STOPS`, default `10`
- `ROUTING_SUPPORTED_MODES`, default `walking,car_taxi`
- `ROUTING_FALLBACK_BEHAVIOR`, default `mock`

Supported app modes:

- `walking`: OpenRouteService `foot-walking`
- `car_taxi`: OpenRouteService `driving-car`
- `public_transport`: not supported by this adapter by default; mock fallback is used during itinerary enrichment when `ROUTING_FALLBACK_BEHAVIOR=mock`

Generated and adapted itineraries can persist day-level `routeGeometry`, `routingProviderMetadata`, and `routingWarnings`. The frontend map uses provider geometry when present and falls back to marker-to-marker straight lines otherwise. Standard routing tests inject fake transports and do not make live provider calls. Live OpenRouteService integration tests are skipped by default until an explicit integration profile is added.

## Development User Accounts

The Phase 2 account foundation is intentionally simple. Users are identified by plain `user_id` in development-mode endpoints:

- `POST /api/users`
- `GET /api/users/{user_id}`
- `POST /api/users/{user_id}/preferences`
- `POST /api/users/{user_id}/bookmarks/{itinerary_id}`
- `DELETE /api/users/{user_id}/bookmarks/{itinerary_id}`
- `GET /api/users/{user_id}/bookmarks`
- `POST /api/users/{user_id}/reviews`
- `GET /api/users/{user_id}/reviews`

This supports profile records, preferences, itinerary bookmarks, and reviews. A feature-flagged auth boundary can protect these routes with local/test tokens or managed JWT validation. `GET /api/me` syncs the current bearer-token subject to a local user profile. There are no passwords, sessions, OAuth UI, provider SDK integration, or account recovery flows yet. Anonymous destination/book browsing and itinerary generation remain available.

## Vector Service Foundation

The backend has a provider-neutral vector abstraction in `app/services/vector_types.py` and `app/services/vector_service.py`. It defines interfaces for:

- Creating embeddings.
- Upserting vectors.
- Searching similar vectors.
- Deleting vectors.
- Fetching vectors by metadata.

Local development uses `FakeEmbeddingProvider`, `InMemoryVectorStore`, and optionally `LocalJsonVectorStore` from `app/services/fake_vector_store.py`. The fake implementation is deterministic, supports metadata filtering, and performs simple cosine-similarity search. Set `LITINERARY_VECTOR_STORE_PATH` to persist fake vectors to a local JSON file during development; leave it unset for process-local in-memory storage.

Supported collection names are:

- `user_preferences`
- `user_reviews`
- `itineraries`
- `book_city_mappings`
- `pois`

Configuration placeholders:

- `LITINERARY_VECTOR_PROVIDER=fake`
- `LITINERARY_VECTOR_DIMENSION=16`
- `LITINERARY_VECTOR_STORE_PATH` for future local-file/provider implementations
- `LITINERARY_AI_PROVIDER=fake`
- `LITINERARY_POI_VERIFICATION_PROVIDER=mock`
- `ROUTING_PROVIDER=mock`

User preference and review writes mirror into the fake vector service after relational persistence. The relational database remains the durable source of truth for users, preferences, reviews, bookmarks, and itineraries. Fake vectors are development scaffolding for future personalization work; they are process-local unless `LITINERARY_VECTOR_STORE_PATH` is set.

Preference vectors include user ID, preference ID, preference key, created timestamp, and city/book/itinerary IDs when present in the preference value. Review vectors include user ID, review ID, itinerary ID, rating, created timestamp, and the reviewed itinerary's city and book IDs.

Itinerary, book-to-city, and POI helpers can upsert vectors, fetch by metadata, and run similarity search with metadata filters. Development-only recommendation helpers can:

- Find itineraries similar to a user's saved preferences.
- Find itineraries similar to a user's positive reviews.
- Find POIs similar to a user's combined preference and positive-review interests.

The development-only endpoint `GET /api/users/{user_id}/recommendations/mock` seeds fake itinerary and POI vectors from the current relational database and returns deterministic mock recommendation results. It is not production AI and should not be treated as a real recommender.

This route requires `ENABLE_DEBUG_ROUTES=true` and fake vector services require `ENABLE_MOCK_SERVICES=true`.

This is only a Phase 2 foundation: no OpenAI, Pinecone, Qdrant, Milvus, or external embedding/vector service is called.

No production ticketing, payment, e-commerce, or live managed authentication provider configuration is implemented yet. OpenAI-compatible LLM, Qdrant, Google Places, OpenRouteService, and managed-JWT auth boundaries exist behind feature flags, but local development and standard tests continue to use fake/mock providers by default.
