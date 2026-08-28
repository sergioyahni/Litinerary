# Litinerary Development Status Report

Status note added 2026-08-15: this report is historical. For current Stage 1 auth and itinerary ownership status, use `docs/production-development-progress.md`, `docs/stage-1-s1-02-managed-auth-report.md`, and `docs/stage-1-s1-03-itinerary-ownership-report.md`.

## 1. Executive Summary

Litinerary is a functional mock/offline MVP with a Vue 3 frontend, FastAPI backend, SQLite/Postgres-compatible SQLAlchemy persistence, Alembic migrations, a local seed workflow, broad offline tests, and provider-neutral adapter boundaries. The current reliable evidence supports local mock development, local mock demo, and a completed mock-only Render cloud offline rehearsal. It does not support beta or production with real users or live providers.

Readiness conclusions:

| Stage | Rating | Conclusion |
| --- | --- | --- |
| Local development readiness | Ready with conditions | The repo documents setup, migrations, seed, backend/frontend tests, and local commands; use workspace test temp directories on this Windows machine because prior docs record a default temp permission failure. Evidence: `README.md` lines 14-31, 33-42, 73-81, 287-367; `docs/beta-go-no-go-report.md` lines 15-20. |
| Local demo readiness | Ready | Local mock/offline rehearsal passed health, readiness, seed reset/validate, mock generation, and shutdown without live providers. Evidence: `docs/local-offline-deployment-rehearsal-record.md` lines 3-58. |
| Cloud offline rehearsal readiness | Ready with conditions | Render mock-only rehearsal passed backend/frontend deploy, CORS fix, Postgres migration/seed/validation, mock itinerary smoke, log hygiene, and shutdown. It left the Render Postgres DB in place and recorded npm audit vulnerabilities. Evidence: `docs/cloud-offline-rehearsal-record-render.md` lines 230-425. |
| Beta readiness | Partially ready | Conditional only for a private, protected, mock-only beta after target-specific beta dry-run and config checks. External beta users or live LLM beta remain blocked. Evidence: `docs/beta-go-no-go-report.md` lines 9-13, 130-148, 172-178; `docs/internal-staged-testing-readiness-report.md` lines 18-24, 190-202. |
| Production readiness | Not ready | Production blockers remain: managed auth provider selection/staging, durable rate/cost controls, live provider gates, observability retention/alerting, deployment/backup/runbooks, dependency scanning, and future private itinerary CRUD/sharing policy. Evidence: `docs/production-readiness.md`; `.env.production.example` lines 1-3. |

## 2. Sources Reviewed

Project documentation reviewed: `README.md`, `backend/README.md`, `docs/api-contract.md`, `docs/App_Design_Document_v1.md`, `docs/App_Design_Document_v2.md`, `docs/beta-deployment-runbook.md`, `docs/beta-go-no-go-report.md`, all `docs/cloud-*` checklist/runbook/template/record files, `docs/cloud-target-decision.md`, `docs/cloud-target-readiness-checklist.md`, `docs/deployment-readiness-harness.md`, `docs/edit_app_design_document_v1.md`, `docs/generated-itinerary-quality-review-template.md`, `docs/git-workflow.md`, `docs/integration-test-matrix.md`, `docs/integration-test-strategy.md`, `docs/internal-live-llm-test-plan.md`, `docs/internal-staged-testing-readiness-report.md`, `docs/live-llm-*` runbooks/evidence/review/rollback/troubleshooting/controls files, `docs/local-offline-deployment-rehearsal.md`, `docs/local-offline-deployment-rehearsal-record.md`, `docs/production-readiness.md`, `docs/provider-adapters.md`, `docs/run_app_instructions.md`, `docs/staged-log-sink-redaction-review-plan.md`, and `docs/todo.md`.

Nested docs/template files reviewed for frontend provenance: `docs/webpage-template/index.html`, `docs/webpage-template/litinerary.html`, `docs/webpage-template/litineraries.html`, `docs/webpage-template/about.html`, `docs/webpage-template/contact.html`, and template vendor documentation such as `docs/webpage-template/Safario Travel -doc/index.html`. These appear to be preserved static template/reference assets rather than current app implementation.

Supporting repository files inspected: `.env.example`, `.env.test.example`, `.env.beta.example`, `.env.production.example`, `frontend/.env.example`, `frontend/.env.beta.example`, `frontend/.env.production.example`, `pytest.ini`, `frontend/package.json`, `frontend/src/router/index.ts`, `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/auth.py`, `backend/app/api/routes/__init__.py`, `backend/app/models/domain.py`, migration files under `backend/migrations/versions`, scripts under `scripts/`, test file inventory under `backend/tests` and `frontend/src`, `git status --short`, and recent `git log`.

## 3. Current Architecture and Implementation State

### Frontend

The implemented frontend is a Vue 3 + TypeScript app using Pinia, Vue Router, Vite, Leaflet, Vitest, and Vue Test Utils. Evidence: `README.md` lines 10-11; `frontend/package.json`; `frontend/src/router/index.ts` lines 1-79. Routes exist for home, destinations, books, itinerary configuration, generated itinerary, public repository/detail, account, bookmarks, and subscriber chat. The frontend follows the preserved static travel template visually, but current implementation is in `frontend/src`, not the static `docs/webpage-template` files. Evidence: `README.md` lines 3-5.

### Backend

The backend is FastAPI with request logging, CORS, startup validation for auth and providers, health/readiness endpoints, provider error normalization, and routed modules for destinations, books, itineraries, users, subscriber chat, ingestion, POI admin, and seed admin. Evidence: `backend/app/main.py` lines 34-58, 61-115, 118-158; `backend/app/api/routes/__init__.py` lines 1-24; `docs/api-contract.md` lines 63-722.

### Database

The database layer uses SQLAlchemy models and Alembic migrations. Local development defaults to SQLite; Render rehearsal used Postgres with `postgresql+psycopg`. Schema foundations include destinations, books, POIs, itineraries/days/stops, user profiles, preferences, reviews, bookmarks, chat, ingestion, verification, routing metadata, ownership/visibility, and provider provenance. Evidence: `README.md` lines 40-44, 105-119; `backend/migrations/versions`; `backend/app/models/domain.py` lines 29-260; `docs/cloud-offline-rehearsal-record-render.md` lines 334-359.

### Authentication and authorization

Auth is disabled by default. A provider-neutral boundary exists for dev bearer tokens and managed JWT validation, with dev tokens rejected in deployed environments and managed auth guarded as an external call. Evidence: `README.md` lines 95-103; `backend/app/core/auth.py` lines 39-58, 66-114, 191-232. Production auth is not configured in committed templates. Evidence: `.env.production.example` lines 22-37; `docs/production-readiness.md` lines 57-70.

### External service adapters

Provider boundaries exist behind flags. Current default behavior is fake/mock for LLM, vector, POI, routing, ticketing, affiliate, and TTS. OpenAI-compatible LLM, Qdrant, Google Places, and OpenRouteService adapter boundaries exist but are gated. Ticketing, affiliate/e-commerce, and TTS real providers are intentionally not implemented. Evidence: `docs/provider-adapters.md` lines 21-35, 138-180, 181-223, 224-259, 260-289, 290-362; `backend/app/core/config.py` lines 19-30, 47-107.

### LLM and retrieval

The default itinerary generation path is deterministic mock AI using seeded POIs. The OpenAI-compatible adapter has grounding checks and controlled smoke evidence, but public/beta live LLM remains blocked. Vector retrieval is deterministic fake embeddings and in-memory/local JSON fake store by default; Qdrant is an adapter boundary, and no external embedding API is connected. Evidence: `README.md` lines 129-182; `docs/internal-staged-testing-readiness-report.md` lines 5-18, 60-76; `docs/provider-adapters.md` lines 144-180, 187-215.

### Deployment infrastructure

Local and Render mock-only rehearsal scripts/runbooks exist. A Render offline rehearsal was completed and services were suspended afterward. Production deployment infrastructure is not production-ready; production templates are placeholder-only and explicitly not launch-ready. Evidence: `docs/local-offline-deployment-rehearsal-record.md` lines 3-58; `docs/cloud-offline-rehearsal-record-render.md` lines 230-425; `.env.production.example` lines 1-3; `docs/production-readiness.md` lines 133-151, 179-197.

### Testing and quality controls

Backend pytest, frontend Vitest, smoke, negative-path/security, provider contract, observability, usage-policy, migration/model, seed, adapter-boundary, and deployment-readiness harnesses are documented. Most recent documented backend Render gate: 292 passed, 0 failed, 3 skipped. Most recent documented beta audit: backend 191 passed/3 skipped, frontend 55 passed, frontend build passed. I did not run tests for this report. Evidence: `docs/cloud-offline-rehearsal-record-render.md` lines 151-176, 178-195; `docs/beta-go-no-go-report.md` lines 15-20, 87-120; `README.md` lines 287-367.

## 4. Completed and Verified Work

| Area | Completed work | Evidence | Verification level |
| --- | --- | --- | --- |
| Frontend app foundation | Vue/Vite app with MVP/account/subscriber routes and tests | `frontend/src/router/index.ts` lines 13-79; `README.md` lines 333-351; `docs/beta-go-no-go-report.md` lines 95-105 | Tested |
| Backend API foundation | FastAPI app, health/readiness, API router modules, provider error handling | `backend/app/main.py` lines 45-58, 101-158; `backend/app/api/routes/__init__.py` lines 15-24 | Implemented |
| Database schema and migrations | Alembic migrations through subscriber chat; SQLAlchemy models include ownership/provider/verification/routing/user fields | `backend/migrations/versions`; `backend/app/models/domain.py` lines 81-176, 203-260; `README.md` lines 40-44 | Implemented |
| Local mock demo | Offline local rehearsal passed readiness, seed validation, mock itinerary, shutdown | `docs/local-offline-deployment-rehearsal-record.md` lines 3-58 | Manually verified |
| Render mock-only rehearsal | Render backend/frontend deploy, CORS fix, Postgres migration/seed/validate, mock smoke, log hygiene, shutdown | `docs/cloud-offline-rehearsal-record-render.md` lines 230-425 | Cloud verified |
| Provider fail-closed posture | Feature flags, external-call guard policy, readiness booleans, standard tests offline | `docs/provider-adapters.md` lines 37-60; `README.md` lines 52-64, 73-93 | Tested |
| Auth foundation | Dev-token and managed-JWT boundary with deployed dev-token rejection and owner checks when auth-required flag is enabled | `backend/app/core/auth.py` lines 39-58, 66-114, 222-232; `docs/api-contract.md` lines 299-323 | Tested |
| LLM smoke threshold | Three controlled live LLM smoke tests documented with sanitized evidence | `docs/internal-staged-testing-readiness-report.md` lines 5-7, 20-24, 50-59 | Manually verified |
| Secret/log hygiene for Render rehearsal | Render logs/evidence reviewed, no visible secrets/provider payloads found | `docs/cloud-offline-rehearsal-record-render.md` lines 372-400 | Cloud verified |

## 5. Partially Completed Work

| Area | Current state | Remaining work | Evidence |
| --- | --- | --- | --- |
| Managed auth | Boundary supports dev tokens and managed JWT config, but no real provider selected/staged | Select provider, configure issuer/audience/JWKS, stage-test, add real frontend login/session UX | `README.md` lines 95-103; `.env.production.example` lines 22-37; `docs/production-readiness.md` lines 57-70 |
| Ownership/access controls | Ownership/visibility fields and public filtering exist; user endpoints can enforce owner/admin checks under auth flags | Production auth integration, private itinerary CRUD/ownership coverage, route-level hardening | `docs/api-contract.md` lines 61, 299-323, 543-545; `README.md` lines 369-375 |
| LLM integration | OpenAI-compatible adapter and smoke evidence exist; user-facing live LLM blocked | Durable rate/cost controls, internal access boundary, monitoring, rollback drill, staged log review, approvals | `docs/internal-staged-testing-readiness-report.md` lines 9-18, 60-76, 178-188 |
| Vector DB/retrieval | Fake vector store works; Qdrant boundary exists | Real Qdrant environment, integration test profile, backfill executor, deletion/retention policy, monitoring | `docs/provider-adapters.md` lines 181-223; `README.md` lines 129-149 |
| POI provider | Mock POI verification and Google Places boundary exist | Credentials, live opt-in tests, terms review, rate/cost monitoring, stale verification/manual review workflow | `docs/provider-adapters.md` lines 224-259 |
| Routing provider | Mock routing and OpenRouteService boundary exist | Credentials, live opt-in tests, attribution/terms review, transit strategy, route quality validation | `docs/provider-adapters.md` lines 260-289 |
| Observability | Local structured logging/readiness redaction exists; Render log hygiene reviewed | Production log sink, retention policy, dashboards, alerting, incident runbooks | `docs/production-readiness.md` lines 133-151; `docs/cloud-offline-rehearsal-record-render.md` lines 372-400 |
| Beta deployment | Mock-only private beta plan exists; Render mock rehearsal gives useful evidence | Target-specific beta dry run, protected access decision, exact beta URLs/CORS, non-production DB, audit vulnerabilities | `docs/beta-go-no-go-report.md` lines 130-138; `docs/cloud-offline-rehearsal-record-render.md` lines 292-299 |

## 6. Blocked, Gated, or Not Yet Started Work

| Area | Status | Prerequisites or blockers | Evidence |
| --- | --- | --- | --- |
| Public/beta live LLM | Blocked by missing operational controls | Production auth, durable quotas/costs, monitoring, POI/routing quality, privacy/logging, rollback, explicit later approval | `docs/internal-staged-testing-readiness-report.md` lines 190-202 |
| Staged internal live LLM | Blocked after smoke threshold | Internal-only access boundary, approved ceilings/spend, durable monitoring, rollback drill, owner mapping, log-sink review | `docs/internal-staged-testing-readiness-report.md` lines 60-76, 178-188, 319-333 |
| Production auth | Not implemented/configured | Managed provider selection and staging; production must not use dev provider | `.env.production.example` lines 22-37; `docs/production-readiness.md` lines 57-70 |
| Durable usage/cost controls | Not implemented | Replace in-memory usage store with durable metering and alerting | `docs/provider-adapters.md` lines 61-90; `docs/production-readiness.md` lines 98-107 |
| Real ticketing | Intentionally deferred / not implemented | Provider selection, legal/product review, stale inventory policy, terms, rate limits, monitoring | `docs/provider-adapters.md` lines 290-315 |
| Real affiliate/e-commerce/payment | Intentionally deferred / not implemented | Commerce/legal/security review, disclosure, provider selection; no payment before separate gate | `docs/provider-adapters.md` lines 317-339 |
| Real TTS/audio storage | Intentionally deferred / not implemented | Voice licensing, retention/deletion, storage/CDN policy, accessibility fallback | `docs/provider-adapters.md` lines 341-362 |
| Production deployment | Blocked | Auth provider staging, future private CRUD/sharing policy, durable limits, observability retention, deployment readiness checks, backups/rollback | `docs/production-readiness.md` |
| Staged log sink review | Planned but not executed | Actual staged log sink and retention review | `docs/staged-log-sink-redaction-review-plan.md` lines 3-32; `docs/internal-staged-testing-readiness-report.md` lines 72-74 |
| Rollback drill for staged live LLM | Attempted/incomplete | Completed drill capturing live-configured readiness before rollback | `docs/integration-test-matrix.md` lines 26-28; `docs/internal-staged-testing-readiness-report.md` lines 83-85, 180-182 |

## 7. Testing Status

Available suites include backend pytest (`pytest.ini` points to `backend/tests`), frontend Vitest (`frontend/package.json` scripts), smoke scripts, deployment readiness scripts, beta dry run, local offline rehearsal, live LLM preflight/smoke scripts, and Render cloud-offline preflight. Evidence: `pytest.ini`; `frontend/package.json`; `scripts/test_backend.ps1`, `scripts/test_frontend.ps1`, `scripts/test_smoke.ps1`, `scripts/deployment_readiness_check.ps1`, `scripts/beta_dry_run.ps1`, `scripts/local_offline_deployment_rehearsal.ps1`, `scripts/cloud_offline_render_preflight.ps1`.

Most recently documented outcomes:

| Evidence | Outcome |
| --- | --- |
| Render backend pytest gate | 292 passed, 0 failed, 0 errors, 3 skipped; no cloud provider contacted. `docs/cloud-offline-rehearsal-record-render.md` lines 151-176. |
| Render frontend build gate | Passed through Render cloud-offline preflight; no deployment performed by that preflight. `docs/cloud-offline-rehearsal-record-render.md` lines 178-195. |
| Local Render preflight | Passed after setting `PYTHONPATH`; first attempt failed with `ModuleNotFoundError: No module named 'app'`. `docs/cloud-offline-rehearsal-record-render.md` lines 197-228. |
| Beta audit | Backend 191 passed/3 skipped, frontend 55 passed, frontend build passed; default pytest temp failed until workspace basetemp was used. `docs/beta-go-no-go-report.md` lines 15-20. |
| Local offline rehearsal | Passed preflight, health, readiness, seed reset/validate, mock generation, shutdown. `docs/local-offline-deployment-rehearsal-record.md` lines 11-58. |

Known skipped tests are live-provider integrations for Google Places, LLM, and OpenRouteService. Evidence: `docs/cloud-offline-rehearsal-record-render.md` lines 168-176; `docs/beta-go-no-go-report.md` lines 116-120.

Security and negative-path coverage exists for auth foundation, negative security paths, environment guards, external-call policy, provider contracts, provider fail-closed integration, observability redaction, and frontend API/store error paths. Evidence: `README.md` lines 312-351; `backend/README.md` lines 155-178; `docs/integration-test-matrix.md` lines 13-20, 72-96.

I did not run tests while preparing this report. The documented evidence is strong but date-sensitive: the newest cloud record is more reliable for Render rehearsal status than older planning docs, while current local working-tree artifacts and dependency audit warnings mean the repo should be re-verified before any new release decision.

## 8. Deployment Readiness

### Local Development

Readiness rating: Ready with conditions.

Completed prerequisites: setup docs, local SQLite default, Alembic/seed commands, backend/frontend test commands, feature-flag defaults, mock services, local CORS, API base URL configuration. Evidence: `README.md` lines 14-31, 33-42, 46-71, 262-286.

Missing prerequisites: clean local artifact tree and/or consistent workspace `--basetemp`; fresh full test run after any new change.

Blockers: none for mock local development.

Required evidence before proceeding: current backend pytest and frontend Vitest/build results, preferably using workspace artifacts.

### Local Demo

Readiness rating: Ready.

Completed prerequisites: local offline rehearsal passed preflight, health, readiness, seed validation, London/Sherlock mock itinerary, shutdown, and no live providers. Evidence: `docs/local-offline-deployment-rehearsal-record.md` lines 3-58.

Missing prerequisites: frontend runtime preview remains partly separate from the backend loopback rehearsal; docs say frontend tests/typecheck/build are covered by preflight. Evidence: `docs/local-offline-deployment-rehearsal-record.md` lines 54-58.

Blockers: none for a mock/offline local demo.

Required evidence before proceeding: rerun local rehearsal if code/config changed since the recorded date.

### Render Cloud Offline Rehearsal

Readiness rating: Ready with conditions.

Completed prerequisites: Render target selected, backend/frontend deployed mock-only, CORS fixed, Render Postgres configured, migrations/seed/validation passed, mock itinerary smoke passed, logs reviewed, services suspended. Evidence: `docs/cloud-offline-rehearsal-record-render.md` lines 230-425.

Missing prerequisites: resolve tracked npm audit vulnerabilities before broader exposure; decide whether to delete or retain the Render Postgres DB; refresh rehearsal if commit has changed since recorded `2defe81`. Evidence: `docs/cloud-offline-rehearsal-record-render.md` lines 236-239, 292-299, 415-418.

Blockers: no blocker for completed mock-only rehearsal; not enough for public beta or production.

Required evidence before proceeding: fresh Render or target-cloud smoke from intended commit, vulnerability review, and database cleanup/retention decision.

### Beta Deployment

Readiness rating: Partially ready.

Completed prerequisites: mock-only beta plan, beta env templates, dry-run script, local/offline and Render mock rehearsal evidence. Evidence: `docs/beta-go-no-go-report.md` lines 9-13, 130-138; `.env.beta.example`; `frontend/.env.beta.example`.

Missing prerequisites: target-specific `scripts/beta_dry_run.ps1` pass, protected access decision, exact beta CORS/API URLs, approved non-production DB and seed data, admin/debug disabled, external calls disabled, vulnerability review. Evidence: `docs/beta-go-no-go-report.md` lines 130-149; `docs/production-readiness.md` lines 179-197.

Blockers: managed auth becomes a staging blocker if external beta users are invited; live provider beta remains no-go.

Required evidence before proceeding: beta dry-run output, cloud smoke, log/secret review, and explicit decision that beta is mock-only and protected.

### Production Deployment

Readiness rating: Not ready.

Completed prerequisites: foundational code and contracts, restrictive production template, production readiness checklist.

Missing prerequisites: managed auth provider staging, future private itinerary CRUD/sharing policy, durable rate/cost controls, live provider gates and terms reviews, production secret management, observability backend, dashboards, alerts, log retention, backups, rollback drills, dependency/security scanning, migration-state readiness. Evidence: `docs/production-readiness.md`.

Blockers: production template explicitly says not ready for launch until auth, durable rate limits, observability retention, and provider gates pass. Evidence: `.env.production.example` lines 1-3.

Required evidence before proceeding: every production readiness gate must have current passing evidence, not just a checklist.

## 9. Documentation Quality and Consistency

The documentation is broad and mostly explicit about mock/offline boundaries, but status is spread across overlapping runbooks, readiness reports, and evidence records.

Contradictions and stale claims:

| Issue | Conflict | Most reliable source |
| --- | --- | --- |
| Cloud rehearsal status | `docs/integration-test-matrix.md` says cloud offline deployment rehearsal is planned/missing (`lines 23, 43-44, 57-62, 126-130`), while `docs/cloud-offline-rehearsal-record-render.md` documents a completed Render rehearsal. | `docs/cloud-offline-rehearsal-record-render.md` is newer, target-specific, and records observed deploy/smoke/shutdown results. |
| Cloud target selection | Placeholder cloud target docs still exist beside Render-specific docs. | Render-specific files are more reliable for current target; placeholder files remain templates. |
| Beta readiness age | `docs/beta-go-no-go-report.md` is dated 2026-06-15 and predates later Render rehearsal evidence. | Use beta report for beta blockers, but combine with newer Render record for cloud mock rehearsal evidence. |
| Test counts vary | Beta audit records 191 backend tests; Render record records 292 backend tests. | Render record is newer for backend suite size/outcome; neither substitutes for a fresh current run. |
| Staged live LLM wording | Smoke evidence threshold is complete, but staged internal remains no-go. | `docs/internal-staged-testing-readiness-report.md` lines 5-24 and 178-188 clearly distinguishes smoke success from staged approval. |

Ambiguities and quality gaps:

- Several runbooks/checklists are templates or planned gates; unchecked checklist items must not be read as completed. Examples: `docs/cloud-offline-deployment-rehearsal-record-template.md`, `docs/cloud-offline-checklist-cloud-target-placeholder.md`.
- `docs/cloud-offline-rehearsal-record-render.md` begins with many unfilled metadata/template fields before later appended evidence; readers must not stop at the empty template section.
- The Render frontend build output has mojibake for a check mark (`âœ“ built`), a minor documentation encoding issue. Evidence: `docs/cloud-offline-rehearsal-record-render.md` lines 280-283.
- `docs/todo.md` still references "Prompt 34: Real POI verification adapter behind feature flags", while current docs/code indicate a Google Places boundary exists behind flags. This likely stale todo should be reconciled with `docs/provider-adapters.md` lines 224-259.
- `git status --short` reported deleted/untracked files under `tests/.artifacts/tmp/legacy/...` and permission warnings. These are test artifacts, but they reduce repository hygiene confidence before release.
- No current CI status or production deployment file was verified in repository contents.

## 10. Risks

| Priority | Risk | Impact | Evidence | Recommended mitigation |
| --- | --- | --- | --- | --- |
| Critical | Production launched before managed auth, durable limits, observability, and provider gates | User data exposure, abuse/cost overrun, unsafe provider calls | `.env.production.example` lines 1-3; `docs/production-readiness.md` lines 199-210 | Keep production no-go; close production gates with fresh evidence. |
| High | Live LLM exposed to beta/public users before staged blockers close | Cost, abuse, unsafe output, weak rollback | `docs/internal-staged-testing-readiness-report.md` lines 178-202 | Keep public/beta live LLM disabled; complete access boundary, durable metering, rollback, monitoring, owner approval. |
| High | Managed auth foundation mistaken for configured production auth | Unauthorized access or dev-token misuse if misconfigured | `backend/app/core/auth.py` lines 50-58; `.env.production.example` lines 22-37 | Select managed provider, stage-test, disable dev fallback, add frontend provider UX and ownership tests. |
| High | In-memory usage controls mistaken for production rate/cost controls | Multi-process bypass and spend exposure | `docs/provider-adapters.md` lines 61-90; `docs/production-readiness.md` lines 98-107 | Implement durable per-user/session/provider metering and alerting. |
| High | Dependency vulnerabilities from Render build ignored before exposure | Security exposure in beta/production | `docs/cloud-offline-rehearsal-record-render.md` lines 292-299 | Run `npm audit`, triage critical/high findings, document accepted risk or remediation. |
| Medium | Cloud rehearsal evidence tied to older commit and suspended services | Readiness drift from current repository state | `docs/cloud-offline-rehearsal-record-render.md` lines 236-239, 402-425 | Rehearse intended release commit and record current commit SHA. |
| Medium | Repo/test artifact hygiene problems obscure release status | Dirty state, permission failures, misleading test artifacts | `git status --short`; `docs/beta-go-no-go-report.md` lines 15-20 | Clean ignored artifacts safely, fix temp permissions or standardize `--basetemp`, re-run tests. |
| Medium | Cloud docs overlap causes stale readiness decisions | Operators may follow placeholders instead of Render evidence | `docs/integration-test-matrix.md` lines 23, 57-62; `docs/cloud-offline-rehearsal-record-render.md` lines 230-425 | Add a current deployment status index and mark templates as templates. |
| Low | Static template files confuse frontend implementation status | Reviewers may treat `docs/webpage-template` as app code | `README.md` lines 3-11 | Document template assets as visual reference only. |

## 11. Recommended Next Steps

### 1. Immediate repository hygiene and verification

1. Objective: reconcile test artifact dirtiness and permission warnings.
   Why required: `git status` showed deleted/untracked files under `tests/.artifacts/tmp/legacy/...` and permission warnings.
   Relevant files/components: `tests/.artifacts/tmp`, `.gitignore`, `pytest.ini`.
   Completion criteria: clean or intentionally documented artifact state; no permission warnings during `git status`.
   Dependencies: decide whether artifacts should be removed, ignored, or restored.

2. Objective: run fresh safe local verification without live providers.
   Why required: documented test evidence may be stale relative to the current working tree.
   Relevant files/components: `backend/tests`, `frontend/src/**/*.test.ts`, `scripts/test_backend.ps1`, `scripts/test_frontend.ps1`.
   Completion criteria: backend pytest, frontend Vitest, and frontend build pass with workspace artifact paths; skipped live tests remain skipped.
   Dependencies: artifact/temp cleanup.

3. Objective: triage npm audit findings.
   Why required: Render frontend build recorded 6 vulnerabilities including 1 critical.
   Relevant files/components: `frontend/package.json`, `frontend/package-lock.json`.
   Completion criteria: critical/high findings remediated or risk-accepted in docs with rationale.
   Dependencies: fresh `npm audit` in a non-production/local context.

### 2. Local readiness

1. Objective: rerun local offline rehearsal from current commit.
   Why required: confirms local demo remains ready after any changes.
   Relevant files/components: `scripts/local_offline_deployment_rehearsal.ps1`, `docs/local-offline-deployment-rehearsal-record.md`.
   Completion criteria: health/readiness/seed/mock itinerary/shutdown pass and record updated with date/commit.
   Dependencies: local test verification.

2. Objective: verify frontend runtime preview against backend.
   Why required: existing local rehearsal emphasizes backend loopback and preflight tests/build, not browser-level app/backend runtime.
   Relevant files/components: `frontend/src`, `backend/app`, `VITE_API_BASE_URL`.
   Completion criteria: browser-level destination/book/generate/repository path works locally.
   Dependencies: backend and frontend local servers.

### 3. Render offline rehearsal

1. Objective: repeat Render mock-only rehearsal for the intended release commit.
   Why required: existing Render record references commit `2defe81` and suspended services.
   Relevant files/components: Render backend/static site, Render Postgres, `docs/cloud-offline-rehearsal-record-render.md`.
   Completion criteria: backend/frontend build/deploy, CORS, Postgres migration/seed/validate, mock itinerary, log hygiene, and shutdown pass.
   Dependencies: cloud access and approved non-production target.

2. Objective: decide database retention/cleanup.
   Why required: Render Postgres was left in place for evidence continuity.
   Relevant files/components: Render Postgres database.
   Completion criteria: DB retained with documented owner/purpose or deleted/reset with evidence.
   Dependencies: cloud operator approval.

### 4. Beta-readiness work

1. Objective: define beta scope as protected mock-only or require managed auth.
   Why required: beta report says managed auth becomes a blocker if external beta users are invited.
   Relevant files/components: `.env.beta.example`, `frontend/.env.beta.example`, `docs/beta-deployment-runbook.md`.
   Completion criteria: written beta audience/access decision and matching config.
   Dependencies: product/security decision.

2. Objective: run target beta dry run.
   Why required: private staging beta is conditional on `scripts/beta_dry_run.ps1` passing.
   Relevant files/components: `scripts/beta_dry_run.ps1`, `docs/beta-deployment-runbook.md`.
   Completion criteria: dry run passes with admin/debug disabled, external calls blocked, health/readiness OK, tests/build pass.
   Dependencies: beta env variables and target URLs.

3. Objective: keep all live providers disabled for beta unless a separate review approves them.
   Why required: public/beta live generation is no-go.
   Relevant files/components: `.env.beta.example`, provider flags in `backend/app/core/config.py`.
   Completion criteria: readiness shows mock/fake providers and `externalCalls.allowed=false`.
   Dependencies: beta deployment config.

### 5. Production-readiness work

1. Objective: select and stage managed auth.
   Why required: production auth is not selected/configured.
   Relevant files/components: `backend/app/core/auth.py`, frontend auth store/services, `.env.production.example`.
   Completion criteria: managed JWT validation staged, `/api/me` sync verified, dev provider/fallback disabled, ownership tests pass.
   Dependencies: provider selection and secrets.

2. Objective: implement durable rate/cost metering.
   Why required: current guardrails are in-memory/local.
   Relevant files/components: `backend/app/services/usage_policy.py`, database models/migrations, readiness/observability.
   Completion criteria: durable per-user/session/provider counters, enforced budgets, alert paths, tests.
   Dependencies: auth/account identity and storage decision.

3. Objective: complete production observability and runbooks.
   Why required: no paid/production observability backend, retention policy, alerts, or incident runbooks are connected.
   Relevant files/components: `backend/app/core/observability.py`, `docs/staged-log-sink-redaction-review-plan.md`, `docs/production-readiness.md`.
   Completion criteria: logs/metrics/error tracking configured, retention/redaction reviewed, alert owners assigned, incident/rollback drills recorded.
   Dependencies: deployment platform and owner mapping.

4. Objective: close real provider gates one provider at a time.
   Why required: adapters are gated; real traffic needs credentials, terms review, integration tests, monitoring, and costs.
   Relevant files/components: `docs/provider-adapters.md`, provider services under `backend/app/services`.
   Completion criteria: opt-in live integration profile, provider terms/attribution policy, fail-closed tests, monitored staged smoke.
   Dependencies: auth, durable limits, observability, secrets.

## 12. Go/No-Go Conclusions

| Target | Conclusion | Explanation |
| --- | --- | --- |
| Local demo | GO | Mock/offline local rehearsal passed and no live-provider dependency is required. Evidence: `docs/local-offline-deployment-rehearsal-record.md` lines 3-58. |
| Render cloud offline rehearsal | GO | Render mock-only rehearsal completed with backend/frontend deploy, Postgres migration/seed, mock itinerary, log hygiene, and shutdown. Conditions: refresh for current commit and address npm audit findings before broader exposure. Evidence: `docs/cloud-offline-rehearsal-record-render.md` lines 230-425. |
| Beta deployment | CONDITIONAL GO | Only for protected, mock-only private beta after target beta dry-run, exact CORS/API config, non-production DB, disabled admin/debug/external calls, and vulnerability review. No-go for public/beta live LLM. Evidence: `docs/beta-go-no-go-report.md` lines 130-148, 172-178; `docs/internal-staged-testing-readiness-report.md` lines 190-202. |
| Production deployment | NO-GO | Production auth provider staging, durable limits/cost controls, future private CRUD/sharing policy, live provider gates, observability, backups/rollback, security scanning, and release evidence are incomplete. Evidence: `.env.production.example` lines 1-3; `docs/production-readiness.md`. |
