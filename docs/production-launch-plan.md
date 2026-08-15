# Litinerary Production Launch Plan and Remaining Gap Audit

Last updated: 2026-08-15

## Executive Summary

Litinerary is in `PRODUCTION-HARDENING`. Stage 0 and S1-01 through S1-05 have produced a strong backend production foundation, but the repository is not yet staging-ready or launch-candidate for real users.

PLU-01 is complete. Product and platform decisions are now owner-approved in `docs/production-decisions.md`: Auth0 for managed auth, Render for frontend/backend hosting, managed PostgreSQL with Render Postgres preferred, Render-managed environment/secrets for v1, mock/curated product providers for v1, no live product providers before launch, private itinerary CRUD/share deferred, subscriber chat excluded from public v1, GitHub Actions for CI/CD, and a minimal hosted observability/backup/security/privacy launch posture.

The next implementation unit is PLU-02: managed auth provider and frontend session integration, after the owner-authorized S1-01 through S1-05 Git checkpoint is created. PLU-08 is post-launch and is not required for initial Production GO.

No production feature work was implemented in PLU-01. The work was documentation and decision recording only.

## Current Production-Readiness Classification

Classification: `PRODUCTION-HARDENING`.

Rationale:

- `FOUNDATIONAL` is too low: S1-01 through S1-05 resolved major backend security, authorization, usage-control, and DB readiness foundations.
- `MID-DEVELOPMENT` is too low: the core user-facing application and validation baseline exist.
- `STAGING-READY` is too high: real frontend auth, production infrastructure, CI/CD, observability, backup/restore, rollback, and staging E2E proof are missing.
- `LAUNCH-CANDIDATE` is too high: at least eight true P1 launch blockers remain.

## Current Repository State

| Item | Current Evidence |
|---|---|
| Repository | `C:\Users\syahn\source\litinerary` |
| Branch | `main...origin/main` |
| Current commit | `86a40dc90ff7dcfd4497ef1da190dc2da35e73ca` |
| Recent commits | `86a40dc Fix deployment readiness profile imports`; `0e27a71 Update form-data dependency`; `7bee38e Restore repository hygiene and document development status`; recent Render rehearsal docs. |
| Working tree | Dirty. S1-01 through S1-05 implementation and report work remains uncommitted in modified tracked files and untracked files. |
| Modified tracked files | Environment templates, README files, backend auth/config/readiness/database/repository/usage/route/test files, frontend API/detail files, deployment scripts, production docs. |
| Untracked files | `backend/app/core/database_readiness.py`, S1 migrations `20260815_0008` and `20260815_0009`, ownership/readiness tests, Stage 0/S1 reports, `docs/production-development-progress.md`, and this launch plan. |
| Migration head | `20260815_0009 (head)` |
| CI directory | `.github` directory not found in current repository state. |
| S1 commit status | S1-01 through S1-05 are not committed; they remain in the working tree. Production planning must preserve and account for that state. |
| PLU-01 decision record | `docs/production-decisions.md` records owner-approved Gate A decisions. |

No reset, clean, stash, revert, discard, or unrelated overwrite was performed.

## Completed Foundations

| Foundation | Status | Evidence |
|---|---|---|
| Stage 0 baseline | Complete | Stage 0 reports and progress tracker record repo hygiene, backend, frontend, migrations, seed, startup, health, and readiness evidence. |
| Authentication backend boundary | Complete for backend | Deployed managed-auth config fails closed; dev auth is rejected in deployed profiles; `/api/me` syncs verified identity; owner/admin authorization exists. |
| Itinerary security | Complete for current routes | S1-03 added ownership, visibility, owner/admin private access, cross-user denial, and intentional public itinerary behavior. |
| Usage/cost controls | Complete for backend enforcement | S1-04 added durable DB counters, atomic reservation behavior, fail-closed store failure, and provider request/cost budget windows. |
| Database readiness | Complete for deployed fail-fast behavior | S1-05 requires explicit DB URL, connectivity, Alembic head, and blocks local/mock fallback in deployed profiles. |
| Validation baseline | Complete through S1-05 evidence | Latest recorded full backend pytest: 350 passed, 3 skipped, 114 warnings. Frontend typecheck, full Vitest, and production build passed. Health/readiness and migration rehearsal evidence recorded. |

## Historical P0/P1 Resolution

| Finding | Classification | Repository Evidence |
|---|---|---|
| Deployed user-owned routes could accept permissive identity behavior. | RESOLVED | S1-01 route/auth changes and tests enforce authenticated owner/admin access. |
| Production auth config could be incomplete without startup failure. | PARTIALLY RESOLVED | Backend startup enforcement is resolved in S1-02; real provider selection and frontend login/session integration remain open. |
| Private/public itinerary semantics were unclear. | RESOLVED | S1-03 schema, migration, route, repository, and tests enforce access semantics for current routes. |
| Usage/rate/cost limits were in-memory only. | RESOLVED | S1-04 durable `usage_limit_counters` and fail-closed limiter behavior exist. |
| Deployed DB could use local SQLite/mock fallback or ignore migration drift. | RESOLVED | S1-05 blocks deployed startup/readiness for missing, unavailable, unmigrated, behind, or unknown DB states. |
| Live provider rollout had no safe production gate. | STILL OPEN | Product providers remain disabled/mock; live provider rollout still lacks staging proof, budgets, monitoring, and owner approval. |
| Observability lacked production retention/alerts. | STILL OPEN | Structured logs/readiness exist, but no hosted alerting/monitoring config was found. |
| CI/CD was not checked in. | STILL OPEN | `.github` directory is absent. |
| Frontend auth/session was development-oriented. | STILL OPEN | `authService.ts` keeps in-memory session state and development-token helpers. |
| Missing POI stops could be silently dropped during persistence. | STILL OPEN | `itinerary_to_model()` filters stops with `if db.get(POIModel, stop.poi.id) is not None`. |

## Litinerary v1 Production Definition

Owner-approved v1: launch with real managed authentication, real production infrastructure, durable DB-backed persistence, and mock/curated product providers.

### Included User Journeys

- Browse destinations and books.
- Generate deterministic seeded/mock itineraries.
- Browse public itinerary repository entries.
- View public itinerary details, narration text, and map/route data.
- Use authenticated bookmarks, reviews, preferences, and account-backed profile features.
- Exclude subscriber chat/refinement from the initial public v1. Keep the existing implementation intact but do not expose it as a required public v1 journey.

### Anonymous Functionality

- Destination browsing.
- Book browsing.
- Basic itinerary generation.
- Public itinerary list/detail/narration.

### Authenticated Functionality

- Real managed login/logout/session lifecycle.
- `/api/me` hydration from verified identity.
- Preferences, bookmarks, reviews, and any owner-bound private reads exposed by current routes.

### Subscriber Functionality

- Subscriber chat/refinement is excluded from public v1 and should be revisited post-launch.

### Launch-Required Live Provider Functionality

- Managed auth provider: Auth0 is required.
- Product providers: live LLM/vector/POI/routing/ticketing/TTS/affiliate work is post-launch and not required for initial Production GO.

### Features Intentionally Deferred

| Feature | Classification | Rationale |
|---|---|---|
| Private itinerary management UI | POST-LAUNCH | Useful but not necessary for mock/curated public itinerary v1. |
| Private itinerary list | POST-LAUNCH | Backend access boundaries exist; a dedicated list UI is not required for v1 unless owner changes scope. |
| Private itinerary save/edit/delete | POST-LAUNCH | Owner approved deferral for initial v1. |
| Publish/unpublish | POST-LAUNCH | Public/private schema exists but workflow is not necessary for initial v1. |
| Sharing links | POST-LAUNCH | Not needed for coherent public browsing/generation v1. |
| Unlisted sharing contract | POST-LAUNCH | `unlisted` currently behaves like private; true unlisted sharing needs a future product contract. |

### Operational Capabilities Required

Auth0 auth, managed PostgreSQL, Render-hosted frontend/backend, Render-managed secrets, GitHub Actions CI/CD, hosted observability, backups, restore proof, rollback proof, production-like staging, and final GO/NO-GO approval.

## Remaining Launch Blockers

| ID | Priority | Area | Blocker | Evidence | Why launch-blocking | Dependency |
| -- | -------- | ---- | ------- | -------- | ------------------- | ---------- |
| PLB-01 | P1 | Git checkpoint | S1-01 through S1-05 remain uncommitted and owner requires a clean checkpoint before PLU-02. | `git status --short --branch` shows dirty/untracked S1 work. | PLU-02 should not mix new auth implementation with uncheckpointed production-foundation work. | Separate owner authorization for Git commit/push operation. |
| PLB-02 | P1 | Authentication | Auth0 is selected, but real provider/frontend auth integration is incomplete. | `authService.ts` uses in-memory session and dev-token helpers; env templates contain auth placeholders. | Real users cannot safely authenticate end to end. | Auth0 tenant/application provisioning and checkpoint. |
| PLB-03 | P1 | Infrastructure | Render frontend/backend, managed PostgreSQL, Render secrets, domain/DNS/TLS, and staging/prod environments are not provisioned. | Deployment docs are rehearsal/template oriented; current repo has no active prod provisioning proof. | Public traffic needs stable, secure runtime infrastructure. | PLU-03 and owner-provided Render/domain/DNS details. |
| PLB-04 | P1 | CI/CD | GitHub Actions production gates are approved but absent. | `.github` directory not found. | Manual-only validation is unsafe for production changes. | PLU-04. |
| PLB-05 | P1 | Observability | Approved minimal hosted logs, error reporting, monitoring, alerts, and owner route are not wired. | Structured logs/readiness exist; no external alerting config found. | Production incidents may go undetected. | PLU-05 and selected tools that satisfy approved architecture. |
| PLB-06 | P1 | Backup/recovery | Hosted backups, restore rehearsal, migration rollback, and app rollback proof are missing. | S1-05 identifies these as remaining risks. | Data loss/bad deploy recovery is unproven. | PLB-03. |
| PLB-07 | P1 | Persistence integrity | Missing POI itinerary stops are silently dropped. | `database_repository.itinerary_to_model()` filters missing POIs. | Core itinerary data can be silently corrupted/truncated. | Engineering task. |
| PLB-08 | P1 | Staging validation | Production-like staging E2E rehearsal is missing. | Current evidence is local/offline or prior cloud rehearsal docs, not full launch proof with real auth and managed DB. | Launch requires proof of integrated production behavior. | PLB-02 through PLB-07. |
| PLB-09 | Post-launch | Live providers | Live provider rollout gates are incomplete. | Provider docs keep live product providers disabled/mock. | Not launch-blocking because owner excluded live product providers from v1. | PLU-08 after launch if owner later approves. |

## Product / Human Decisions Required

Gate A decisions are approved in `docs/production-decisions.md`.

| Decision | Approved Choice | Remaining Follow-Up |
| -------- | --------------- | ------------------- |
| S1 checkpoint | Create a clean S1-01 through S1-05 Git checkpoint before PLU-02. | Requires separate owner authorization to commit/push. |
| Initial v1 scope | Narrow mock/curated-provider v1. | None for Gate A. |
| Managed-auth provider | Auth0. | Provision staging and production tenants/apps in PLU-02. |
| Auth tenant strategy | Separate Auth0 staging and production tenants. | Tenant/app details needed for PLU-02. |
| Backend hosting | Render. | Provision in PLU-03. |
| Frontend hosting | Render. | Provision in PLU-03. |
| Managed database platform | Managed PostgreSQL, Render Postgres preferred unless PLU-03 finds a blocker. | Provision staging/prod DBs in PLU-03. |
| Secrets/config store | Render-managed environment variables/secrets/environment groups. | Configure separated staging/prod secrets in PLU-03. |
| Domain/DNS/TLS | `app.[YOUR_DOMAIN]`, `api.[YOUR_DOMAIN]`, `staging.[YOUR_DOMAIN]`, `api-staging.[YOUR_DOMAIN]`; Render-managed TLS. | Literal domain and DNS provider values must be finalized before Production GO. |
| Initial live providers | None. Managed auth is the only real external provider for v1. | PLU-08 post-launch. |
| Quota values and budgets | Existing production-template limits; live product-provider cost budget `$0`. | Revalidate in staging and revisit before any live-provider rollout. |
| Private itinerary CRUD/share | Defer to post-launch. | None for v1. |
| Subscriber chat/refinement | Exclude from public v1. | Revisit retention/privacy/provider implications post-launch. |
| Backup retention/RPO/RTO | Paid managed PostgreSQL with PITR where available, daily logical backup/export, 30-day external retention, pre-migration backup, restore rehearsal, RPO 24h, RTO 4h. | Implement/rehearse in PLU-06. |
| Analytics | No product analytics in v1. | Revisit post-launch. |
| Privacy/data handling | Manual support deletion process for v1; logs 30 days; usage counters 90 days; no v1 chat retention policy. | Document and verify in PLU-06. |
| Seed/reference data | Reviewed curated seed/reference data through controlled release setup. | Approve exact production content set before seeding. |
| CI/CD policy | GitHub Actions with PR checks, protected `main`, automated validation, staging automation allowed, production manual approval. | Implement in PLU-04. |
| Observability | Minimal hosted logs, frontend/backend errors, uptime, health/readiness, DB/auth/5xx/rate/usage alerts. | Configure in PLU-05. |
| Security posture | Exact CORS, CSP/security headers, dependency scan, secret scan, debug/admin verification, exception/log review, HTTPS-only. | Implement/verify in PLU-04 and PLU-06. |
| Support/incident owners | Role-based owner: Project Owner for incident, security, DB/backup, auth, support, and GO/NO-GO authority. | May delegate named people before GO. |

## External Resources Required

Infrastructure classification:

| Component | Classification | Evidence |
|---|---|---|
| Frontend hosting | CONFIGURED BUT NOT PROVISIONED | Render is approved; service provisioning remains PLU-03. |
| Backend hosting | CONFIGURED BUT NOT PROVISIONED | Render is approved; service provisioning remains PLU-03. |
| Managed DB | CONFIGURED BUT NOT PROVISIONED | Managed PostgreSQL is approved, with Render Postgres preferred unless PLU-03 finds a blocker. |
| Secrets/config store | CONFIGURED BUT NOT PROVISIONED | Render-managed env/secrets are approved; values must be configured outside Git. |
| Staging environment | CONFIGURED BUT NOT PROVISIONED | Approved: Render frontend/backend, Auth0 staging tenant, managed PostgreSQL, mock product providers. |
| Production environment | CONFIGURED BUT NOT PROVISIONED | Approved stack exists, but production services are not active. |
| Domain | CONFIGURED BUT NOT PROVISIONED | Hostname pattern approved; literal `[YOUR_DOMAIN]` remains provisioning detail before GO. |
| DNS | CONFIGURED BUT NOT PROVISIONED | DNS provider placeholder `[YOUR_DNS_PROVIDER]` remains provisioning detail before GO. |
| TLS | CONFIGURED BUT NOT PROVISIONED | Render-managed TLS and HTTPS enforcement approved. |
| Scheduled job infrastructure | CONFIGURED BUT NOT PROVISIONED | Daily Render scheduled/cron usage cleanup approved for PLU-05. |
| Backup service | CONFIGURED BUT NOT PROVISIONED | Paid managed PostgreSQL with PITR where available, daily logical backup/export, and 30-day external retention approved. |
| Monitoring | CONFIGURED BUT NOT PROVISIONED | Minimal hosted logs/errors/uptime/readiness/DB/auth alerting architecture approved. |
| External providers | CONFIGURED BUT NOT PROVISIONED | Auth0 approved and required; live product providers are post-launch. |

| Resource/account | Purpose | Currently available? | Information Codex will need | Dependent Unit |
|---|---|---:|---|---|
| Auth0 staging/production tenants and apps | Real user login and JWT verification. | Approved, not provisioned. | Issuer, audience, client ID, JWKS/metadata URL, callback/logout URLs, claim mapping. | PLU-02 |
| Render frontend hosting service | Host production frontend. | Approved, not provisioned. | Project/service ID, build settings, env vars, domain. | PLU-03 |
| Render backend hosting service | Host API. | Approved, not provisioned. | Project/service ID, start command, env vars, health/readiness URLs. | PLU-03 |
| Render Postgres or approved managed PostgreSQL | Durable production data store. | Approved, not provisioned. | URL/secret, backup settings, migration role, restore target. | PLU-03/PLU-06 |
| Render env/secrets/environment groups | Externalized config and credentials. | Approved, not configured. | How to set/read env vars, rotation approach. | PLU-03 |
| Domain/DNS | Public URL and auth origins. | Pattern approved; literal values pending. | Domain, DNS provider, records, TLS policy. | PLU-03 |
| Monitoring/error service | Logs, errors, uptime/readiness alerts. | Architecture approved; tool not yet configured. | Project DSN/API key, alert targets, retention. | PLU-05 |
| CI provider/workflows | Automated validation. | GitHub repo exists; workflows absent. | Desired branch rules, secrets for staging deploy. | PLU-04 |
| Backup facility | DB snapshot/restore. | No production proof. | Backup cadence, retention, restore procedure access. | PLU-06 |
| LLM account | Post-launch live generation. | Not required for v1. | API key, model, budgets, allow-list when PLU-08 is later approved. | Post-launch PLU-08 |
| Vector DB account | Post-launch live retrieval/search. | Not required for v1. | Endpoint, credentials, collection policy when PLU-08 is later approved. | Post-launch PLU-08 |
| POI provider account | Post-launch live place data. | Not required for v1. | API key, quotas, terms, fallback policy when PLU-08 is later approved. | Post-launch PLU-08 |
| Routing provider account | Post-launch live routing. | Not required for v1. | API key, quotas, rate limits, fallback policy when PLU-08 is later approved. | Post-launch PLU-08 |
| Ticketing/TTS/affiliate accounts | Post-launch commerce/audio links. | Not required for v1. | API credentials, terms, disclosure requirements when later approved. | Post-launch PLU-08 |

## Authentication Completion Plan

| Item | Classification | Remaining Work |
|---|---|---|
| Provider selection | Approved | Auth0. |
| Tenant/project creation | Infrastructure setup | Create separate Auth0 staging and production tenants/apps. |
| Frontend SDK/OIDC flow | Implementation work and launch blocker | Add Auth0 SPA login, redirect/callback, token acquisition, session restore, refresh, and logout. |
| Token/session persistence | Implementation work and launch blocker | Preserve session safely across reloads; avoid dev-token UX in deployed builds. |
| `/api/me` hydration | Partly complete; launch blocker end to end | Backend exists; frontend must hydrate real provider token claims. |
| Protected user-feature UX | Implementation work | Friendly login prompts and 401/403 handling for bookmarks/reviews/preferences/subscriber areas. |
| Environment configuration | Infrastructure setup and launch blocker | Set Auth0 issuer, audience, algorithms, JWKS/metadata, CORS, callback/logout URLs. |
| Staging E2E auth test | Launch blocker | Anonymous path, login, `/api/me`, user feature, subscriber if included, logout, invalid token, cross-user denial. |
| Production smoke test | Launch blocker | Health/readiness plus real login and one authenticated user-feature smoke. |

## Database / Backup Plan

Database launch minimum:

- Managed hosted DB provisioned.
- Explicit `LITINERARY_DATABASE_URL` in deployed secrets.
- Alembic migrations run to `20260815_0009` or current head at time of launch.
- Production seed/reference-data strategy approved.
- Readiness confirms configured/connectivity/migrations current.
- Deployed startup blocks missing/unavailable/unmigrated/behind/unknown revision.

Backup/restore launch minimum:

- Paid managed PostgreSQL with provider point-in-time recovery where available.
- Daily logical database backup/export configured.
- External backup copy retained for 30 days.
- Backup or snapshot created and verified before every production migration.
- Restore runbook documented.
- Actual restore rehearsal to a disposable DB completed.
- Migration rollback strategy documented: reversible downgrade, forward fix, or snapshot restore.
- Application rollback documented and rehearsed to the agreed level.
- Launch RPO target: 24 hours maximum for the logical-backup layer, with provider PITR used for finer recovery where available.
- Launch RTO target: 4 hours.

Post-launch maturity:

- Formal recurring RPO/RTO drills.
- Cross-region disaster recovery.
- Periodic restore drills.
- Backup integrity monitoring dashboards.

## Usage / Cost Control Operations

S1-04 completed durable DB-backed usage counters and provider request/cost budget controls. Deployed environments require durable usage controls and fail closed when the usage store fails.

Usage-counter cleanup assessment:

- Expected growth: one or more rows per subject/action/window, accumulating over minute/day windows for anonymous generation, authenticated generation, subscriber chat, provider requests, and provider cost budgets.
- Material launch risk: low for a small initial launch if rows are indexed and the system has manual cleanup/runbook coverage; risk grows with traffic.
- Required frequency: daily cleanup is sufficient for initial launch unless high traffic is expected.
- Appropriate mechanism: daily Render scheduled/cron job.
- Deployment scheduler support: approved for Render scheduled/cron job wiring in PLU-05.
- Classification: `LAUNCH HARDENING`. It must be wired or explicitly runbooked before Production GO, but it is not a reason to expand v1 product scope.

## Live Provider Plan

Recommended ordering:

```text
Product/provider decision
  -> auth frontend integration
  -> production infrastructure
  -> CI/CD
  -> observability and budgets
  -> staging environment
  -> live provider staged test
  -> production enablement only after GO approval
```

Live providers should not be enabled before observability, before frontend auth, or before staging exists. Cost-bearing and externally unreliable behavior must be tested only in staging first.

| Provider | Current mode | Required for v1? | Cost-bearing? | Credentials available? | Monitoring ready? | Staging verified? |
| -------- | ------------ | ---------------- | ------------- | ---------------------- | ----------------- | ----------------- |
| Managed auth | Backend boundary/provider-neutral; frontend incomplete. | Yes | Depends on vendor | No evidence | No | No |
| LLM | OpenAI-compatible boundary; mock/fake default. | No, conditional | Yes | No evidence | No | No |
| Vector database/search | Fake/local boundary; Qdrant-style future path. | No, conditional | Yes | No evidence | No | No |
| POI | Seed/mock data; Google Places-style future path. | No, conditional | Yes | No evidence | No | No |
| Routing | Mock routing; OpenRouteService-style future path. | No, conditional | Yes | No evidence | No | No |
| Ticketing | Mock placeholder. | No | Yes/commerce | No evidence | No | No |
| TTS | Placeholder/text-only behavior. | No | Yes | No evidence | No | No |
| Affiliate | Disabled/mock placeholder. | No | Commerce/revenue | No evidence | No | No |
| Map tiles/fonts | Browser external dependencies. | Yes if current UI remains | Usually no direct app spend | Not applicable | No | Partially via local/browser use only |

Minimum live-provider set for coherent recommended v1: managed auth only. Product providers can remain mock/curated.

## Observability Plan

Already exists:

- Structured logs.
- Request IDs/correlation patterns.
- Health/readiness split.
- DB/provider readiness metadata without secrets.
- Usage-control and provider-selection telemetry patterns.

Required before production:

- Hosted backend log retention.
- Frontend and backend application error reporting.
- External uptime monitoring for frontend/backend.
- Health/readiness monitoring.
- Alerts for startup failure, readiness failure, DB connectivity/migration failure, auth provider/JWKS failures, authorization spikes, 5xx errors, rate/quota exhaustion, and budget exhaustion.
- Provider error/latency/budget alerts if any live provider is enabled.
- Incident owner and notification route.
- Sensitive logging review.

Post-launch hardening:

- Distributed tracing.
- SLO dashboards.
- Product analytics after privacy approval.
- Synthetic journeys for login, generation, bookmark/review, and subscriber flows.

## CI/CD Plan

Current state: no checked-in `.github` workflows were found. Validation exists as local commands/scripts and S1 reports.

| Capability | Current State | Required State |
|---|---|---|
| Backend full pytest | Manual evidence exists. | Automated on change. |
| Frontend typecheck | Manual evidence exists. | Automated on change. |
| Frontend tests | Manual evidence exists. | Automated on change. |
| Frontend build | Manual evidence exists. | Automated on change. |
| Migration validation | Local rehearsal evidence exists. | Automated head/migration check against disposable DB. |
| Environment/config validation | Scripts exist. | Automated beta/staging/production template validation. |
| Security/dependency checks | Not proven. | Python/npm vulnerability review in CI. |
| Secret scanning | Not proven. | Automated secret scan and template placeholder check. |
| Deployment | Rehearsal scripts/docs exist. | Repeatable staging deploy; production deploy with approval. |
| DB migration step | Scripts/migrations exist. | Controlled release step with pre-migration backup. |
| Post-deploy health/readiness | Scripts partly cover. | Automated post-deploy health/readiness smoke. |
| Post-deploy core smoke | Partial local evidence. | Production-like staging and production smoke checks. |

## Security Review

| Area | Current Assessment | Launch Severity |
|---|---|---|
| Authentication | Backend managed-auth boundary exists; real provider/frontend missing. | P1 |
| Authorization/IDOR | Current user-owned and private itinerary routes are protected server-side after S1-01/S1-03. | No open P1 for current routes |
| CSRF | Bearer-token model reduces CSRF risk; revisit if cookies are introduced. | Decision-dependent |
| CORS | Production wildcard behavior is guarded; exact production origins still need final config. | P1 configuration |
| XSS | Vue escaping helps; CSP/security headers still missing. | P1/P2 launch hardening |
| SSRF | Provider external calls are gated; live provider URL governance needed before enablement. | Conditional P1 |
| SQL/injection | SQLAlchemy/Pydantic patterns reduce risk; no exploitative testing performed. | No open P1 found |
| Provider-input risk | Live providers disabled; prompts/adapters need staging proof before live. | Conditional P1 |
| Rate limiting/abuse | Durable controls exist; values/budgets/alerts still need production config. | P1 configuration |
| Secrets | Templates use placeholders; production secret store not provisioned. | P1 |
| Dependency vulnerabilities | No current automated scan evidence. | P1 |
| Debug/admin routes | Production/debug guards are documented; deployed verification still required in staging. | P1 smoke |
| Exception leakage | Production `DEBUG=false` expected; staged smoke required. | P1 configuration |
| Security headers | Not recorded complete. | P1/P2 launch hardening |
| Sensitive logging | Redaction/log hygiene exists, but production sink review remains. | P1 |

## Privacy / User Data Review

User data Litinerary stores or can store:

- User profile IDs.
- Auth provider and subject.
- Email/display name if supplied by auth claims.
- Role and subscription status.
- Preferences.
- Bookmarks.
- Reviews.
- Chat sessions and messages.
- Private itineraries and generated itinerary metadata.
- Provider provenance/metadata.
- Usage counters by subject/action/window.
- Logs that may contain request metadata and errors.

Open privacy/user-data requirements:

| Item | Current State | Decision/Work Needed |
|---|---|---|
| Account deletion | Not recorded. | Product/legal decision and implementation if required for v1. |
| User-data deletion | Not recorded. | Product/legal decision; at least manual support process before launch. |
| Retention | Not locked. | Decide retention for accounts, usage counters, reviews, chat, logs. |
| Export | Not recorded. | Product/legal decision; likely post-launch unless required. |
| Analytics | Not chosen. | Decide no analytics versus privacy-approved analytics. |
| Third-party provider sharing | Product providers disabled; auth provider required. | Disclose auth provider; live providers require additional disclosure. |
| Logs containing user data | Redaction patterns exist. | Review production sink and retention before launch. |
| Privacy disclosures | Not recorded. | Product/legal approval before real users. |

No legal conclusion is provided.

## Persistence Integrity

The missing-POI-stop defect still exists.

Affected code:

```text
backend/app/services/database_repository.py
itinerary_to_model()
for stop in day.stops
if db.get(POIModel, stop.poi.id) is not None
```

Impact:

- Stops whose POI row is missing are silently omitted from the persisted itinerary.
- This can truncate itinerary content without an explicit failure.
- It affects any journey that saves an itinerary with a missing POI reference: generated itinerary persistence, subscriber refinement/private itinerary persistence, future imports, and any future save/edit flow.
- Current seeded/mock public generation is lower risk because seed POIs exist, but production persistence should not silently corrupt core itinerary data.

Classification: launch-blocking P1 for any production launch that persists generated or user-associated itineraries.

Implementation task:

- Replace silent filtering with explicit validation/failure, or a deliberately modeled missing-POI error state before persistence.
- Affected files likely include `backend/app/services/database_repository.py`, repository tests, generation/refinement tests, and API error handling if a new error surface is chosen.
- Tests required: missing POI during itinerary save fails loudly; successful seeded itinerary save remains unchanged; subscriber/private refinement path handles validation; no partial/truncated itinerary is committed.
- Definition of done: missing POI references cannot silently drop stops, regression tests pass, and API behavior is documented if surfaced.

## Dependency Graph

```text
PLU-01 Product/platform decisions COMPLETE
  -> owner-authorized S1 checkpoint
  -> PLU-02 Auth0 provider + frontend auth integration
  -> PLU-03 Render hosting + managed PostgreSQL + Render secrets + domain/TLS
  -> PLU-04 CI/CD + security/dependency/secret scanning
  -> PLU-05 Observability + alerts + usage cleanup operations
  -> PLU-06 Backup/restore + rollback + security/privacy launch controls
  -> PLU-07 Persistence integrity + production-like staging rehearsal
  -> Production GO/NO-GO

PLU-01 Live-provider stance: no live product providers in v1
  -> PLU-08 post-launch
```

Specific dependency examples:

- Auth0 tenant/app provisioning -> frontend Auth0 integration -> authenticated E2E staging.
- Render hosted DB -> approved backup policy -> restore rehearsal -> production deployment gate.
- GitHub Actions pipeline -> staging deployment -> launch qualification.
- Observability foundation -> v1 operations; live provider staging remains post-launch.
- Product scope decision -> private CRUD/share and subscriber chat deferred post-launch.

## Production Gates

| Gate | Objective | Prerequisites | Work Included | Human Input Required | Exit Criteria |
|---|---|---|---|---|---|
| Gate A - Product / Vendor / Platform Decisions | Lock launch scope and required external choices. | S1-01 through S1-05 evidence. | Decision record for v1 scope, auth, hosting, DB, secrets, domain, observability, backups, budgets, privacy. | Complete. | COMPLETE: `docs/production-decisions.md`. |
| Gate B - Remaining Core Engineering | Complete real auth and persistence integrity. | Gate A complete and S1 checkpoint. | Auth0 frontend integration, `/api/me` hydration, protected UX, missing-POI persistence fix. | Auth0 tenant/app details. | Auth E2E and persistence tests pass. |
| Gate C - Infrastructure / CI / Observability | Make staging production-like. | Gates A/B inputs. | Hosting, managed DB, secrets, CI/CD, security scans, logs, errors, alerts, usage cleanup. | Platform and alert owner. | Staging deployable with automated checks and alerts. |
| Gate D - Staging / Live Provider Validation | Prove integrated launch behavior. | Gates B/C. | Staging E2E, migration/seed, backup/restore, rollback, live provider gate if v1 requires it. | GO authority and provider approvals. | Staging rehearsal passes; conditional provider gate passes. |
| Gate E - Production Launch Qualification | Decide final GO/NO-GO. | Gate D. | Production smoke checklist, final scan, rollback readiness, owner approval. | Yes. | GO approval recorded; no NO-GO criteria present. |

## Remaining Implementation Units

| Unit | Objective | Prerequisites | Likely systems/files | Human decision required? | Definition of Done | Gate enabled |
| ---- | --------- | ------------- | -------------------- | ------------------------ | ------------------ | ------------ |
| PLU-01 | Product/platform decision record and launch-scope lock. | Current audit. | Docs, env decision records, launch checklist. | Complete. | COMPLETE: approved decisions recorded in `docs/production-decisions.md`. | Gate A |
| PLU-02 | Managed Auth0 provider and frontend session integration. | PLU-01 complete, S1 checkpoint, Auth0 tenant/app details. | `frontend/src/services/authService.ts`, auth store/router/views, env templates, backend auth smoke tests. | Auth0 provisioning details. | Real login/callback/token/session/refresh/logout and `/api/me` staging smoke pass; dev login absent in deployed UX. | Gate B |
| PLU-03 | Render infrastructure and deployed environment setup. | PLU-01 complete. | Deployment docs/scripts, env templates, Render config, managed PostgreSQL config, migration/seed process. | Render/domain/DNS provisioning details. | Staging/prod env config, managed DB, secrets, CORS, TLS, migrations, readiness pass. | Gate C |
| PLU-04 | GitHub Actions CI/CD and security gates. | PLU-01 and PLU-03. | CI workflows, test scripts, migration checks, dependency/security/secret scans, smoke scripts. | Branch/deploy policy approved. | Automated backend/frontend/migration/config/security/post-deploy gates run. | Gate C |
| PLU-05 | Observability and operational alerts. | PLU-01 and PLU-03. | Logging/error config, readiness monitors, alert docs, Render scheduled cleanup job/runbook. | Tooling may be selected/configured to satisfy approved architecture. | Logs/errors/uptime/readiness/DB/Auth0/usage alerts active; daily usage cleanup scheduled or runbooked. | Gate C |
| PLU-06 | Backup/restore, rollback, security headers, privacy controls. | PLU-01 and PLU-03. | Runbooks, deployment config, frontend/backend headers, privacy docs. | Backup/privacy/security policies approved. | Backup retention, restore proof, rollback proof, CSP/security headers, privacy launch controls complete. | Gate D |
| PLU-07 | Persistence integrity and production-like staging launch rehearsal. | PLU-02 through PLU-06. | `database_repository.py`, backend tests, staging smoke/E2E docs/scripts. | GO owner. | Missing POI stops cannot be silently dropped; staging rehearsal passes all GO/NO-GO checks. | Gate D/E |
| PLU-08 | Post-launch first live-provider rollout gate. | New owner live-provider decision after v1. | Provider adapters/config/tests/runbooks. | Yes. | One live provider has staging proof, credentials, budgets, monitoring, fallback, rollback, and owner approval. | Post-launch, not required for initial Production GO |

## Production GO Checklist

### Application

- [ ] Full backend test suite passes.
- [ ] Frontend typecheck passes.
- [ ] Full frontend tests pass.
- [ ] Production frontend build passes.
- [ ] Core v1 journeys pass end-to-end.

### Authentication

- [ ] Production provider selected and configured.
- [ ] Login works.
- [ ] Session/token lifecycle works.
- [ ] Logout works.
- [ ] `/api/me` works with real identity.
- [ ] Cross-user authorization remains enforced.

### Database

- [ ] Hosted database provisioned.
- [ ] Migration workflow verified.
- [ ] Production DB at Alembic head.
- [ ] Backups configured.
- [ ] Restore procedure verified to agreed launch level.

### Usage / Cost Controls

- [ ] Durable controls enabled.
- [ ] Production quotas explicitly configured.
- [ ] Provider budgets explicitly configured.
- [ ] Cleanup operational if classified as launch-required or launch-hardening for expected traffic.

### Live Providers

- [ ] Auth0 verified in staging.
- [ ] Live product providers remain disabled for v1.
- [ ] Credentials stored outside source control.
- [ ] Failure behavior verified.
- [ ] Budget enforcement verified.
- [ ] Provider disable/rollback mechanism verified.

### Observability

- [ ] Application errors visible.
- [ ] Health/readiness externally monitored.
- [ ] Critical DB/provider failures alert operators.
- [ ] Provider/usage failures are diagnosable.

### CI/CD

- [ ] Required automated validation runs on change.
- [ ] Deployment process is repeatable.
- [ ] Database migrations are controlled.
- [ ] Post-deploy smoke validation exists.

### Security

- [ ] No unresolved launch-blocking security findings.
- [ ] Dependency vulnerability review performed.
- [ ] Secret scan performed.
- [ ] Production debug/admin exposure verified.

### Staging

- [ ] Production-like staging environment exists.
- [ ] Auth E2E passes.
- [ ] Database/migration rehearsal passes.
- [ ] Core journey E2E passes.
- [ ] Live-provider tests pass if live providers are v1-required.
- [ ] Failure scenarios pass.

### Launch Operations

- [ ] Rollback procedure documented.
- [ ] Backup/restore plan documented.
- [ ] Production smoke test defined.
- [ ] Final GO/NO-GO review completed.

## Production NO-GO Criteria

- Backend or frontend validation fails.
- Real production auth is incomplete.
- Frontend still relies on dev/manual token injection for deployed auth.
- Hosted production DB is missing.
- DB migration state is missing, behind, unknown, or not at head.
- Deployed persistence can fall back to SQLite/mock state.
- Backups are unavailable or restore has not been rehearsed.
- Auth0 is missing or not verified in staging.
- A live product provider is enabled in the v1 path without a new owner-approved PLU-08 decision.
- Provider spend is uncontrolled or budgets are not configured.
- Production errors/readiness/DB/auth failures are not visible to operators.
- A launch-blocking P0/P1 security defect remains unresolved.
- Missing POI stops can still be silently dropped.
- Staging core journey or auth E2E fails.
- Rollback capability is missing.
- Literal production domain/DNS provisioning details, privacy launch documentation, or required owner roles are missing before GO.

## Remaining Distance

| Measure | Count |
|---|---:|
| Remaining production gates | 4 major gates after Gate A completion. |
| Remaining launch implementation units | 6 launch units: PLU-02 through PLU-07, plus an owner-authorized S1 checkpoint before PLU-02. |
| Human decisions | Gate A decisions approved; literal domain/DNS values and optional named-role delegation remain provisioning/finalization details before GO. |
| External services/resources | Auth0, Render frontend/backend, Render Postgres/managed PostgreSQL, Render secrets, domain/DNS/TLS, monitoring/error reporting, GitHub Actions, backup/export storage. Product-provider accounts are post-launch. |

Classification remains `PRODUCTION-HARDENING`: backend foundations and Gate A decisions are complete, but production launch still needs the S1 checkpoint, Auth0 integration, Render infrastructure, CI/CD, observability, backup/recovery, persistence integrity, and staging proof.

## Recommended Next Implementation Unit

PLU-02: Managed Auth0 provider and frontend session integration.

Why next:

- Auth0 is now selected, so the highest-risk user-facing launch blocker can move from planning to implementation.
- Real frontend login/callback/session/refresh/logout is required before public user-specific features can launch.
- Backend auth enforcement already exists, so PLU-02 can integrate the chosen provider without redesigning backend authorization.

Prerequisites:

- Owner-authorized S1-01 through S1-05 Git checkpoint.
- Auth0 staging and production tenant/application details.

Why competing tasks come later:

- PLU-03 can proceed after Gate A, but frontend Auth0 integration is the direct blocker for authenticated v1 user journeys.
- PLU-08 is post-launch because live product providers are excluded from v1.
- CI/CD, observability, backup/security/privacy, and staging depend on the selected auth and infrastructure shape.

## Prompt Compliance Matrix

| # | Requirement | Status | Evidence |
| - | ----------- | ------ | -------- |
| 1 | Read all production-readiness reports and current relevant docs. | DONE | Stage 0/S1 reports, progress tracker, re-onboarding review, production/deployment/API/provider docs, runbooks, and env templates were reviewed across this audit and the immediately preceding pass. |
| 2 | Inspect current repository state. | DONE | Branch, commit, status, modified/untracked files, migration head, and recent commits are recorded in Current Repository State. |
| 3 | Verify completed production foundations. | DONE | Completed Foundations covers auth boundary, itinerary security, durable usage/cost controls, DB readiness, and validation baseline. |
| 4 | Build complete remaining-production inventory. | DONE | Remaining blockers, auth, infrastructure, observability, CI/CD, backup, usage cleanup, provider, persistence, security, and privacy sections cover the inventory. |
| 5 | Reassess every historical P0/P1 finding. | DONE | Historical P0/P1 Resolution classifies each as resolved, partially resolved, still open, or superseded where applicable. |
| 6 | Identify remaining true launch blockers. | DONE | Remaining Launch Blockers table uses P1/conditional P1 only for launch-blocking items. |
| 7 | Separate MVP launch requirements from roadmap work. | DONE | Litinerary v1 Production Definition classifies private CRUD/list/share/unlisted features. |
| 8 | Resolve remaining authentication dependency. | DONE | Authentication Completion Plan classifies each remaining auth item. |
| 9 | Reassess whether live-provider rollout should be next. | DONE | Live Provider Plan rejects S1-06 as next and orders providers after auth/infra/observability/staging. |
| 10 | Inventory all provider integrations. | DONE | Live Provider Plan includes provider table and minimum live-provider set. |
| 11 | Define minimum production observability. | DONE | Observability Plan separates existing, required-before-production, and post-launch hardening. |
| 12 | Define minimum CI/CD requirements. | DONE | CI/CD Plan includes current-state versus required-state matrix. |
| 13 | Define production infrastructure requirements. | DONE | External Resources and Remaining Launch Blockers classify missing/decision-required infrastructure without assuming an unproven cloud. |
| 14 | Define backup, restore, and rollback requirements. | DONE | Database / Backup Plan separates launch minimums from later maturity. |
| 15 | Resolve usage-counter cleanup scheduling. | DONE | Usage / Cost Control Operations classifies cleanup as `LAUNCH HARDENING`. |
| 16 | Reassess missing-POI-stop persistence issue. | DONE | Persistence Integrity confirms exact code, impact, task, files, tests, and definition of done. |
| 17 | Perform production security gap review. | DONE | Security Review classifies remaining auth, CORS, headers, secrets, dependency, debug/admin, logging, and provider risks. |
| 18 | Perform privacy/user-data gap review. | DONE | Privacy / User Data Review inventories stored data and open privacy decisions. |
| 19 | Define Litinerary v1 production scope. | DONE | Litinerary v1 Production Definition provides included/deferred journeys and operational requirements. |
| 20 | Build remaining dependency graph. | DONE | Dependency Graph maps prerequisite relationships. |
| 21 | Define finite Production Gates. | DONE | Production Gates replaces open-ended Stage 1 with five gates and exit criteria. |
| 22 | Convert remaining work into bounded implementation units. | DONE | Remaining Implementation Units defines eight substantive units. |
| 23 | Identify every human decision. | DONE | Product / Human Decisions Required includes 15 decisions with options and timing. |
| 24 | Identify external accounts/resources required. | DONE | External Resources Required lists resource, purpose, availability, needed info, and dependent unit. |
| 25 | Create definitive Production GO criteria. | DONE | Production GO Checklist uses Markdown checkboxes and covers all required areas. |
| 26 | Create definitive Production NO-GO criteria. | DONE | Production NO-GO Criteria lists prohibitive conditions grounded in current evidence. |
| 27 | Estimate remaining distance without fake percentage. | DONE | Remaining Distance reports gates, units, decisions, resources, and exact classification. |
| 28 | Recommend exactly one next implementation unit. | DONE | Recommended Next Implementation Unit recommends only PLU-01 and explains sequencing. |
| 29 | Update production-development progress. | DONE | `docs/production-development-progress.md` updated with classification, v1 scope, gates, decisions, resources, units, GO/NO-GO, and next unit. |
| 30 | Create the Production Launch Plan. | DONE | `docs/production-launch-plan.md` created with the required sections. |
| 31 | Include one compliance row for each requirement 1 through 31. | DONE | This matrix contains rows 1 through 31 individually. |
