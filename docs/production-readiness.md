# Production Readiness Checklist and Pre-Integration Gate

This document is the gate before Litinerary connects real auth, LLM, embedding, Vector DB, POI, routing, ticketing, text-to-speech, affiliate, payment, or e-commerce providers.

Current related docs/modules:

- SDD: `docs/App_Design_Document_v2.md`
- API contract: `docs/api-contract.md`
- Provider contracts: `docs/provider-adapters.md`
- Root setup: `README.md`
- Backend setup: `backend/README.md`
- Environment example: `.env.example`
- Beta runbook: `docs/beta-deployment-runbook.md`
- Config: `backend/app/core/config.py`
- Guards: `backend/app/core/guards.py`
- External-call guard: `backend/app/core/provider_guards.py`
- Usage/cost guardrails: `backend/app/services/usage_policy.py`
- Backend tests: `backend/tests`
- Frontend tests: `frontend/src/**/*.test.ts`

## 1. Environment and Configuration

| Check | Required before production |
|---|---|
| `APP_ENV` | Set to `production`. |
| `DEBUG` | Set to `false`. |
| CORS | `CORS_ALLOWED_ORIGINS` must list exact frontend origins. No wildcard. |
| Admin routes | `ENABLE_ADMIN_ROUTES=false` unless protected by authenticated admin and deployment boundary. |
| Debug routes | `ENABLE_DEBUG_ROUTES=false`. |
| Mock services | `ENABLE_MOCK_SERVICES=false` unless running a protected mock environment. |
| Provider feature flags | Keep `ENABLE_REAL_LLM`, `ENABLE_REAL_VECTOR_DB`, `ENABLE_REAL_POI_PROVIDER`, `ENABLE_REAL_ROUTING`, `ENABLE_REAL_TICKETING`, `ENABLE_REAL_TTS`, and `ENABLE_AFFILIATE_LINKS` false until each gate below passes. |
| External calls | Keep product-provider external calls disabled until integration is approved. Deployed managed auth requires `ALLOW_EXTERNAL_CALLS=true` for JWKS/provider metadata and the current environment in `EXTERNAL_CALL_ALLOWED_ENVIRONMENTS`. |
| Integration tests | Keep `ENABLE_INTEGRATION_TESTS=false` for standard test runs. Live integration tests must opt in per command and remain skipped by default. |
| Usage limits | Set finite per-minute and per-day limits for itinerary generation and subscriber chat, finite provider request budgets, and bounded vector search, POI batch, routing stop, ticketing lookup, and LLM input/output sizes. |
| Durable usage controls | Set `ENABLE_DURABLE_USAGE_CONTROLS=true`; deployed startup fails without it. |
| Database URL | Set `LITINERARY_DATABASE_URL` explicitly in every deployed profile. Deployed startup fails when the variable is missing, malformed, or still using the default local SQLite fallback. |
| Cost ceiling | Keep `PROVIDER_DAILY_COST_CEILING_USD=0` until a live-provider spend owner approves a nonzero ceiling and alerting exists. |
| Secrets | Use a secret manager or deployment environment variables. Never commit credentials. |
| `.env.example` | Keep as placeholder-only documentation. |
| Startup validation | Missing real provider credentials should produce visible validation notes. |

Beta/staging dry-run templates exist in `.env.beta.example` and `frontend/.env.beta.example`. Production planning templates exist in `.env.production.example` and `frontend/.env.production.example`; these are placeholder-only and must not contain secrets.

## 2. Database and Migrations

| Check | Required before production |
|---|---|
| Migration tooling | Alembic must be the only schema migration path. |
| Startup DB enforcement | Internal, beta, staging, and production startup must validate the configured database, connectivity, and Alembic head before the app accepts traffic. |
| No schema auto-create | `Base.metadata.create_all`/`init_db` is allowed only for local/test workflows; deployed environments must run Alembic migrations explicitly. |
| Migration order | Ownership/visibility/auth/provenance/licensing fields are present in `20260612_0005`; `20260815_0008` adds the itinerary owner foreign key plus public/owner visibility indexes; `20260815_0009` adds durable usage counters. |
| Backup strategy | Backup before every production migration. |
| Rollback strategy | Document rollback for each migration and validate against a copy of production data. |
| Seed separation | Seed/reset tools must never run against production data. |
| Data retention | Define retention for users, reviews, generated itineraries, chat sessions, and vector records. |
| Public/private data | Public repository rows use `is_public=true` and `visibility=public`; private/unlisted rows are hidden from public listings. Detail/narration can return private/unlisted rows only to the verified owner or an admin. Until sharing is implemented, `unlisted` is treated like private. |
| User data | Auth provider subject, role, subscription status, and updated timestamp fields exist. `/api/me` syncs managed-provider subjects to local profiles. |
| Review data | Decide moderation/public visibility policy. |
| Vector metadata | `embedding_records` tracks collection, provider, model, dimension, external ID, metadata version, last embedded timestamp, and provenance metadata. Backfill/deletion policy is still pending. |
| Usage counter retention | `usage_limit_counters` rows are bounded by UTC windows and should be periodically cleaned after `USAGE_COUNTER_RETENTION_DAYS`. |
| Fallback protection | Deployed environments must not fall back to mock repository data when a database session exists but the database is empty, unmigrated, or misconfigured; those states are startup/readiness failures. |

## 3. Authentication and Authorization

| Check | Required before production |
|---|---|
| Auth provider | Choose managed provider. Do not roll custom passwords initially. |
| Auth feature flags | Deployed envs require `ENABLE_AUTH=true`, a non-`dev` `AUTH_PROVIDER`, `AUTH_JWT_ISSUER`, `AUTH_JWT_AUDIENCE`, production `AUTH_JWT_ALGORITHMS`, `AUTH_JWKS_URL` or `AUTH_PROVIDER_METADATA_URL`, claim mapping variables, `AUTH_REQUIRED_FOR_USER_FEATURES=true`, `AUTH_ALLOW_DEV_USER_FALLBACK=false`, `ALLOW_EXTERNAL_CALLS=true`, and the current `APP_ENV` in `EXTERNAL_CALL_ALLOWED_ENVIRONMENTS`. |
| JWT/session validation | FastAPI verifies provider JWTs using configured JWKS or provider metadata. The contract is provider-neutral; production still requires selecting and staging a real managed provider. |
| Registered flow | `/api/me` validates the bearer token and syncs the current provider subject to a local profile. |
| Anonymous flow | Keep destinations/books/basic generation/public repository available. |
| Subscriber access | Gate chat/refinement/premium features by entitlement. |
| Admin roles | Add authenticated admin/developer role checks on top of config guards. |
| Ownership checks | Preferences, bookmarks, reviews, chat sessions, private itinerary detail/narration, and subscriber private refinements enforce owner/admin checks server-side. Dedicated private itinerary CRUD and sharing routes remain future work. |
| 401/403 behavior | Standardize backend responses and frontend handling. |
| Frontend protection | Auth store, token attachment, `/api/me` sync, 401/403 handling, logout/session reset, and provider-login placeholders exist. Add real provider UI/SDK during provider selection. |

## 4. External Provider Integration Gates

| Provider | Required env vars | Feature flag | Gate before integration |
|---|---|---|---|
| LLM | `LLM_PROVIDER=openai_compatible`, `LLM_API_KEY`, `LLM_MODEL_NAME` | `ENABLE_REAL_LLM` | OpenAI-compatible adapter boundary tests, structured grounding checks, copyright-safe ingestion, judge validation, allowed environments, cost/rate controls, timeout/retry policy, monitoring. |
| Embedding | `VECTOR_DB_PROVIDER` or embedding-specific provider vars | `ENABLE_REAL_VECTOR_DB` | Embedding model/dimension lock, backfill plan, deletion policy, metadata isolation, batch cost controls. |
| Vector DB | `VECTOR_DB_PROVIDER=qdrant`, `QDRANT_URL` or `VECTOR_DB_URL`, optional `QDRANT_API_KEY` / `VECTOR_DB_API_KEY` | `ENABLE_REAL_VECTOR_DB` | Qdrant adapter boundary tests, index/collection plan, metadata schema, migration/backfill/rollback, tenant/user isolation tests. |
| POI verification | `POI_PROVIDER=google_places` or `POI_VERIFICATION_PROVIDER=google_places`, plus `POI_PROVIDER_API_KEY` / `GOOGLE_PLACES_API_KEY` / `POI_VERIFICATION_API_KEY` | `ENABLE_REAL_POI_PROVIDER` | Google Places adapter boundary tests, confidence threshold policy, manual review workflow, provider request IDs, stale verification policy, cost/rate-limit controls, Google terms review. |
| Routing | `ROUTING_PROVIDER=openrouteservice`, plus `ROUTING_API_KEY` or `OPENROUTESERVICE_API_KEY` | `ENABLE_REAL_ROUTING` | OpenRouteService adapter boundary tests, max-stop controls, timeout/retry/cost controls, fallback policy, transit limitation handling, no straight-line mislabeling, provider terms review. |
| Ticketing | `TICKETING_PROVIDER`, `TICKETING_API_KEY`, `TICKETING_BASE_URL`, `TICKETING_TIMEOUT_SECONDS` | `ENABLE_REAL_TICKETING` | Boundary exists with mock placeholders only. Before real use: affiliate disclosure, stale inventory warnings, no payment secrets, provider terms review, rate limits, monitoring. |
| Text-to-speech | `TTS_PROVIDER`, `TTS_API_KEY` or `TEXT_TO_SPEECH_API_KEY`, `TTS_TIMEOUT_SECONDS` | `ENABLE_REAL_TTS` | Boundary exists with mock text narration and placeholder audio metadata only. Before real use: voice licensing, audio retention/deletion, accessibility fallback, provider terms, rate limits, monitoring, and storage/CDN review. |
| Affiliate/e-commerce | `AFFILIATE_PROVIDER`, `AFFILIATE_API_KEY`, `AFFILIATE_BASE_URL`, `AFFILIATE_TIMEOUT_SECONDS` | `ENABLE_AFFILIATE_LINKS` | Boundary exists with mock book links only. Separate commerce/security review, disclosure policy, tracking disclosure, no payment implementation without new gate. |

For every provider:

- `require_external_call_allowed` must run before any external HTTP request.
- `ProviderUsageGuard` must run before provider-like work that can consume quota, tokens, or money.
- `ALLOW_EXTERNAL_CALLS=true` must be explicit.
- Standard `APP_ENV=test` runs must remain blocked unless `ENABLE_INTEGRATION_TESTS=true`.
- Contract tests must pass.
- Missing credentials must fail clearly.
- Timeouts and bounded retries must be configured.
- Logs must exclude secrets and raw sensitive payloads.
- Cost, quota, and latency metrics must be observable.
- Fallback behavior must be explicit.

## 4.1 Usage Guardrails

The current guardrails support local/mock and durable deployed enforcement:

- Local development and standard tests can use in-memory usage records in
  `backend/app/services/usage_policy.py`.
- Deployed environments require `ENABLE_DURABLE_USAGE_CONTROLS=true` and use
  DB-backed UTC-window counters in `usage_limit_counters`.
- Standard tests exercise anonymous generation, registered-user generation, subscriber chat, routing stop count, POI batch size, LLM input size, vector search size, estimated cost ceiling, and UTC day-window reset behavior.
- Limit-related failures normalize to provider error codes such as `rate_limited`, `quota_exceeded`, `input_too_large`, `unsupported_batch_size`, `too_many_stops`, and `cost_limit_exceeded`.
- FastAPI maps those provider errors to explicit HTTP responses, and the frontend API client displays the safe `message` field.

Before production provider traffic, add alerting, reconcile estimated cost with
provider billing, and decide how limits vary by anonymous, registered,
subscriber, and admin roles.

## 5. Security Checklist

| Check | Status needed |
|---|---|
| No committed secrets | Required. |
| Admin endpoints | Config-guarded and authenticated admin-guarded. |
| Destructive routes | Disabled in production. |
| CORS | Exact origins only. |
| Rate limiting | Local guardrails exist; replace with durable distributed enforcement before real LLM/routing/POI/ticketing/TTS traffic. |
| Input validation | Pydantic schemas plus domain validation. |
| Output sanitization | No raw provider payloads or secrets to frontend. |
| Logging | Avoid sensitive user data, copyrighted text, tokens, API keys. |
| Dependency scanning | Add before deployment. |
| User data isolation | Owner/admin checks are implemented and tested for user routes, chat sessions, private itinerary detail/narration, bookmark/review writes, and bookmark list filtering. Dedicated private itinerary CRUD/sharing still needs a separate launch gate. |
| Copyright-safe ingestion | Source license/copyright/processing-mode fields exist; real provider ingestion still requires policy review and tests. |

## Subscriber Chat Foundation

- Subscriber chat routes exist under `/api/subscribers/chat`.
- The foundation uses `require_subscriber_user`; it does not implement billing, payment, checkout, or subscription purchase.
- Current chat replies and itinerary refinements use the local mock AI pipeline only.
- Chat-generated itineraries are private, subscriber-only, owned by the current user, and excluded from the public repository.
- Before production launch, configure and stage-test a managed auth provider, connect subscription entitlement sync, add moderation/retention policy, and keep real LLM usage behind the existing LLM grounding/judge gates.

## 6. Observability and Operations

| Check | Required before production |
|---|---|
| Structured logging | Include request IDs and provider request IDs. |
| Request IDs | API middleware emits and returns `X-Request-ID`; future edge/proxy layers should preserve it. |
| Error tracking | Capture backend/frontend errors without secrets, raw prompts, copyrighted text, tokens, or provider credentials. |
| Provider metrics | Local provider telemetry hooks capture provider type, name, operation, success/failure, latency, estimated cost, warning count, error type, and request ID. |
| Health checks | `/api/health` remains a minimal liveness endpoint. |
| Readiness checks | `/api/readiness` verifies safe DB configuration, connectivity, Alembic head, provider mock/real mode, durable usage controls, and credential-presence booleans without exposing secrets or database URLs. |
| Backup monitoring | Verify backup freshness and restore drills. |
| Migration monitoring | Track migration success/failure and rollback path. |

Current observability is local logging only:

- Event names are centralized in `backend/app/core/observability.py`.
- Structured events cover request start/end, provider selection, provider success/failure, external-call blocks, rate-limit decisions, itinerary generation, POI verification, routing, judge rejection, auth failures, and admin/development actions.
- Readiness and provider status responses redact credentials and expose only safe booleans.
- No paid observability backend is connected. Production should choose log retention, sampling, PII policy, dashboards, alerting, and incident runbooks before beta traffic expands.

## 7. Testing Gate

Required commands before provider integration:

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest
..\venv\Scripts\python.exe -m pytest tests\test_provider_contracts.py tests\test_negative_security_paths.py tests\test_environment_guards.py
```

```powershell
cd frontend
npm test
npm run test:smoke
```

Checklist:

- Backend tests pass.
- Frontend tests pass.
- Smoke/E2E path passes.
- Negative-path/security tests pass.
- Provider contract tests pass.
- Tests require no external network calls.
- No real credentials are required.

## 7.1 Beta Deployment Dry Run

Before any beta/staging deployment attempt, run:

```powershell
.\scripts\beta_dry_run.ps1
```

The dry run:

- Validates `APP_ENV=beta` configuration with admin/debug routes disabled.
- Verifies external calls remain blocked and real provider flags remain disabled.
- Checks Alembic heads/current migration status.
- Runs backend and frontend tests.
- Builds the frontend.
- Starts a temporary backend server.
- Confirms `/api/health` and `/api/readiness`.
- Confirms admin routes return `403`.
- Performs no deployment and uses no real secrets.

## 8. Real Integration Readiness Score

| Area | Status | Blockers | Recommended next prompt |
|---|---|---|---|
| Auth provider | Backend Contract Ready | Provider-neutral JWT validation, `/api/me`, claim mapping, local profile sync, deployed startup fail-fast checks, and admin-role checks exist. A real managed provider and frontend SDK/login flow are still not selected, configured, or stage-tested. | "Select provider and implement frontend managed-auth login/session integration." |
| LLM provider | Almost Ready | OpenAI-compatible adapter boundary, grounding checks, structured judge results, and mocked contract tests exist, but production traffic still needs rate limiting, spend enforcement, prompt/version governance, monitoring, and explicit integration-test opt-in. | "Add gated live LLM integration tests, spend enforcement, and provider observability before production LLM traffic." |
| Vector DB | Almost Ready | Qdrant adapter boundary, contract tests, and metadata model exist, but production deployment still needs a real Qdrant environment, explicit backfill execution, deletion/retention policy, and monitoring. | "Implement gated Qdrant integration test profile and vector backfill executor with deletion policy." |
| POI provider | Almost Ready | Google Places adapter boundary, mocked contract tests, confidence policy, and persistence metadata exist, but production traffic still needs real credentials, rate limiting, monitoring, terms review, and explicit integration-test opt-in. | "Add gated live Google Places integration tests and provider observability before production POI traffic." |
| Routing provider | Almost Ready | OpenRouteService adapter boundary, mocked contract tests, day-level route geometry, and fallback policy exist, but production traffic still needs real credentials, rate limiting, monitoring, attribution/terms review, and explicit integration-test opt-in. | "Add gated live OpenRouteService integration tests and routing observability before production route traffic." |
| Ticketing provider | Needs Review | Provider-neutral boundary and mock links exist, but no real provider is implemented; affiliate/legal/product policy, stale inventory language, provider terms review, rate limits, and monitoring are still needed. | "Select a real ticketing provider and add gated integration tests after legal/product review." |
| Affiliate provider | Needs Review | Provider-neutral boundary and mock book links exist, but no real provider, tracking disclosure, or commerce review is implemented. | "Select an affiliate provider and add disclosure-safe integration tests after commerce/legal review." |
| Production deployment | Blocked | Managed auth provider selection/staging, durable rate limits, observability retention, deployment readiness checks, private itinerary CRUD/sharing policy, and release operations remain incomplete. | "Create production deployment hardening plan with readiness checks and secret management." |

## 9. Recommended Next Prompts

1. "Select and configure managed auth provider in staging with mocked fallback disabled."
2. "Implement gated Qdrant integration test profile and vector backfill executor with deletion policy."
3. "Add gated live Google Places integration tests and provider observability before production POI traffic."
4. "Add gated live OpenRouteService integration tests and routing observability before production route traffic."
5. "Add gated live LLM integration tests, spend enforcement, and provider observability before production LLM traffic."
6. "Select a real ticketing provider and add gated integration tests after legal/product review."
7. "Select an affiliate provider and add disclosure-safe integration tests after commerce/legal review."
