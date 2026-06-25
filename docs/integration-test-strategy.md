# Integration Test Strategy

## Status

This is a planning document for pre-deployment integration testing. It does not
enable live providers, staged internal testing, beta live generation, public live
generation, deployment, or external calls.

Current release posture:

- Controlled live LLM smoke-test evidence threshold: complete, `3 of 3`.
- Staged internal live LLM testing: no-go.
- Public/beta live LLM generation: no-go.
- Default integration tests: offline/mock only.

## Goals

- Prove the backend and frontend work together through the MVP journey without
  relying on external providers.
- Prove environment gates fail closed for live LLM, Vector DB, POI verification,
  routing, ticketing, affiliate, TTS, managed auth, and external-call policy.
- Prove readiness and deployment dry-run checks expose safe state without
  leaking secrets.
- Prove seeded data, migrations, repository matching, itinerary generation,
  auth boundaries, and frontend API contracts stay stable before deployment.
- Define a later optional provider-gated track that is disabled by default and
  cannot run in CI without explicit opt-in.

## Non-Goals

- No live LLM requests.
- No `/v1/chat/completions` calls.
- No staged internal testing enablement.
- No public/beta live generation.
- No deployment.
- No live Vector DB, POI verification, routing, ticketing, affiliate, TTS,
  managed auth, or other external providers.
- No production-grade auth implementation in this test-strategy phase.
- No durable monitoring or spend-control implementation in this document.

## Test Layers

1. Backend offline integration tests: FastAPI `TestClient`, SQLite test database,
   seeded data, fake/mock providers, and no network.
2. Provider boundary tests: adapter selection, fail-closed guards, mocked
   transports, safe diagnostics, grounding/provenance checks, and skipped live
   integration placeholders.
3. Frontend/API integration tests: Pinia stores, API service wrappers, router
   flows, component rendering, mocked API responses, and auth-token handling.
4. Deployment-readiness dry run: mock-only beta/staging profile, migrations,
   seed checks, `/api/health`, `/api/readiness`, route protection, tests, and
   frontend build.
5. Optional provider-gated tests: explicit local-only or approved environment
   runs after separate approval; disabled by default and never required for CI.

## Offline Default Integration Tests

Offline/default tests must be safe for local and CI execution:

- `APP_ENV=test` or a mock-only dry-run profile.
- `ALLOW_EXTERNAL_CALLS=false`.
- `ENABLE_INTEGRATION_TESTS=false`.
- All `ENABLE_REAL_*` flags false.
- `ENABLE_AFFILIATE_LINKS=false`.
- `ENABLE_STAGED_INTERNAL_LLM_TESTING=false`.
- `ENABLE_INTERNAL_ACCESS_GATE=false`.
- `ENABLE_AUTH=false` unless testing mocked/dev auth behavior.
- No provider credentials in files, logs, or command output.

The current backend suite already covers health, readiness, MVP itinerary
generation, seed validation/reset/import/export, provider contracts, environment
guards, auth foundation, usage limits, observability redaction, and adapter
boundaries with mocked transports.

The current frontend suite already covers API service calls, Pinia stores, auth
token attachment, itinerary display, and a routed happy-path smoke flow with
mocked backend services.

## Provider-Gated Tests

Provider-gated tests are optional and disabled by default. They may exist as
skipped test placeholders or separate scripts, but they must require all of:

- Explicit environment flags such as `ENABLE_INTEGRATION_TESTS=true`.
- Explicit provider enablement for the one provider under test.
- `ALLOW_EXTERNAL_CALLS=true`.
- `APP_ENV` included in `EXTERNAL_CALL_ALLOWED_ENVIRONMENTS`.
- Provider-specific environment allow-list, where applicable.
- Secret values supplied only from approved secret storage or ignored local env.
- A runbook that states scope, request count, rollback, and evidence rules.

For LLM provider-gated tests, staged internal testing must still remain no-go
until the staged-readiness blockers are closed. Public/beta live LLM generation
must remain blocked.

## Frontend/API Integration Tests

Frontend/API integration testing should remain offline by default:

- Service tests assert request paths, methods, payloads, query strings, and auth
  header attachment without a real backend.
- Store tests assert loading, error, reset, generation, repository, auth, and user
  workflows with mocked API functions.
- Routed smoke tests mount the app and exercise destination selection, book
  selection, itinerary configuration, generation, display, repository detail,
  bookmark, review, and preference flows.
- A future optional browser-level harness can start a mock-only backend and
  frontend locally, then exercise the same happy path through HTTP. This should
  remain mock-only and must not require live providers.

## Deployment-Readiness Checks

Before any mock-only beta/staging deployment attempt:

- Run backend tests from `backend`.
- Run frontend tests, typecheck, and build from `frontend`.
- Run or improve `scripts/beta_dry_run.ps1`.
- Validate the beta/staging env template keeps all live providers disabled.
- Run Alembic migrations against a non-production database.
- Seed approved non-production data and validate expected counts.
- Check `/api/health`.
- Check `/api/readiness` for database `ok`, provider mock/fake modes, external
  calls disabled, and secret-free booleans.
- Confirm admin and debug routes are disabled in beta/staging mode.
- Confirm logs include request IDs and do not include secrets, raw prompts, raw
  provider payloads, bearer tokens, Authorization headers, or copyrighted text.

## CI And Local Execution

CI expectations:

- CI runs offline/default integration tests only.
- CI must not have provider API keys.
- CI must not set `ALLOW_EXTERNAL_CALLS=true`.
- CI must not set `ENABLE_REAL_LLM=true` or other live-provider flags.
- CI may run backend tests, frontend tests, typecheck, build, and mock-only dry
  run checks.

Local expectations:

- Developers may run the same offline/default integration tests.
- Controlled live smoke or provider-gated tests require separate runbooks and
  explicit approval.
- Ignored files such as `.env.development.local` may be used only for approved
  local smoke tests and must never be committed.

## Safety Rules

- No live LLM calls in default integration tests.
- No external calls in CI.
- Provider-gated tests must require explicit environment flags and must be
  skipped by default.
- No secrets in tracked files.
- Raw provider payloads must not be logged.
- Readiness must expose credential presence as booleans only.
- Provider diagnostics must remain allow-listed and safe.
- Public/beta live generation remains blocked.
- Staged internal live LLM testing remains no-go until rollback, access-boundary,
  spend/monitoring, owner, and log-sink blockers are resolved.

## Current Coverage Summary

Already exists:

- Backend API contract tests for public, user, and development admin shapes.
- Backend health/readiness, environment guard, external-call policy, and
  observability redaction tests.
- Backend seed, migration metadata, repository persistence, MVP API, and smoke
  happy-path tests.
- Backend provider boundary tests for LLM, POI, routing, vector, ticketing,
  affiliate, TTS, and provider contracts.
- Backend grounding/provenance and live-smoke preflight redaction tests.
- Backend auth foundation and ownership-style user feature tests.
- Frontend service, store, display, auth, and routed happy-path smoke tests.

Partially exists:

- Deployment-readiness dry run exists, but it is a script/runbook rather than a
  consistently named integration-test harness.
- Frontend/API integration exists with mocked services, but not yet as a
  browser-level test against a temporary mock backend.
- Secret hygiene exists through targeted tests and manual scans, but not as a
  single reusable CI script.
- Provider-gated tests are represented by skipped placeholders and smoke
  runbooks, but they are intentionally not default tests.

Missing:

- A dedicated backend offline integration test module that groups readiness,
  seed validation, itinerary generation, and provider mock-mode assertions.
- A reusable deployment-readiness test harness that can be run locally and in CI
  without PowerShell policy surprises.
- A browser-level mock-only frontend/backend happy-path integration test.
- A repository-wide secret hygiene script suitable for CI.
- A passing rollback drill and staged log-sink review, which remain staged
  blockers rather than integration-test blockers.

## Recommended Implementation Order

Batch 1: backend offline integration tests

- Add a focused backend integration module for `/api/health`, `/api/readiness`,
  seed validate/reset in development, mocked itinerary generation, repository
  lookup, and provider mock-mode assertions.

Batch 2: provider fail-closed and negative-path integration tests

- Add grouped tests proving live-provider flags fail closed across LLM, POI,
  routing, vector, ticketing, affiliate, TTS, and managed auth without network.
- Add or consolidate grounding/provenance failure tests around the itinerary
  generation path.

Batch 3: frontend/API integration tests

- Keep existing mocked service/store tests.
- Add a mock-only browser-level or component-level integration path that uses
  stable API fixtures and verifies user-facing errors for generation failures.

Batch 4: deployment-readiness test harness

- Wrap beta dry-run checks into a repeatable mock-only integration harness:
  config validation, migrations, seed, temporary backend, health/readiness,
  protected routes, frontend test/typecheck/build, and secret scan.

Batch 5: optional provider-gated tests

- Keep disabled by default.
- Require explicit flags, approved runbook, non-production credentials, and
  rollback evidence.
- Do not run in CI.
