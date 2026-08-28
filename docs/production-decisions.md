# Litinerary Production Decisions

## Decision Record Metadata

- Date: 2026-08-15
- Repository commit: `86a40dc90ff7dcfd4497ef1da190dc2da35e73ca`
- Decision owner: Project Owner
- Status: Approved for Production Gate A
- Scope: PLU-01 Product / Platform Decision Record and Launch-Scope Lock

These decisions record the owner-approved production contract for the initial Litinerary v1 launch path. Do not store real credentials, tokens, database URLs, API keys, or secret values in this file.

## Litinerary v1 Scope

Decision: launch the narrow mock/curated-provider v1.

Included:

- Real managed authentication.
- Real production infrastructure.
- Managed database persistence.
- Durable usage controls.
- Public destination/book browsing.
- Public itinerary generation using curated/seeded/mock product-provider behavior.
- Existing authenticated profile, preferences, bookmarks, and reviews functionality.

Rationale: this is the smallest coherent public product that proves production auth, infrastructure, persistence, authorization, usage controls, CI/CD, observability, backup/restore, rollback, staging, and operations without adding live provider complexity to the critical path.

Downstream PLU units affected: PLU-02, PLU-03, PLU-04, PLU-05, PLU-06, PLU-07.

## Deferred Product Scope

Decision: defer the following until post-launch unless a later owner-approved scope change reclassifies them:

- Live LLM integration.
- Live vector database/search integration.
- Live POI provider integration.
- Live routing provider integration.
- Live ticketing provider integration.
- Live TTS provider integration.
- Affiliate integrations.
- Payment or commerce flows.
- Private itinerary list.
- Private itinerary save/edit/delete.
- Publish/unpublish.
- Sharing links.
- True unlisted sharing behavior.
- Product analytics.
- Self-service account/data deletion.

Rationale: these are useful product or operational expansions, but not required for the approved v1 scope.

Downstream PLU units affected: PLU-08 is post-launch for v1; private itinerary CRUD/share work is post-launch.

## Live Provider Stance

Decision: no live product providers in initial v1.

Managed authentication is the only required real external provider for v1. Live LLM, vector, POI, routing, ticketing, TTS, and affiliate integrations are post-launch.

Rationale: excluding live product providers reduces cost, reliability, privacy, support, observability, and rollback risk for the first safe launch.

Downstream PLU units affected: PLU-08 is `POST-LAUNCH / NOT REQUIRED FOR INITIAL PRODUCTION GO`. PLU-05 does not need live product-provider latency/spend alerting for v1, but should preserve the provider alerting path for future rollout.

## Managed Auth Decision

Decision: use Auth0 as the production managed OIDC/JWT authentication provider.

Tenant/project strategy:

- Separate Auth0 staging and production tenants.
- Keep staging and production applications, users, callbacks, secrets, and configuration isolated.

Backend integration strategy:

- Use the existing provider-neutral backend issuer/audience/JWKS architecture.
- Do not redesign backend authorization around Auth0-specific identity logic.
- Use claim mapping through existing settings such as `AUTH_USER_ID_CLAIM`, `AUTH_ROLES_CLAIM`, `AUTH_SUBSCRIPTION_CLAIM`, `AUTH_EMAIL_CLAIM`, and `AUTH_DISPLAY_NAME_CLAIM`.

Rationale: Auth0 fits the existing OIDC/JWT/JWKS backend boundary and has SPA login/session support suitable for PLU-02.

Downstream PLU units affected: PLU-02, PLU-03, PLU-05, PLU-06, PLU-07.

## Hosting Decision

Decision:

- Backend hosting: Render.
- Frontend hosting: Render.

Rationale: Render has the strongest repository-specific rehearsal evidence and runbook history. The decision is based on existing Litinerary rehearsal evidence, not on Render being inherently required.

Downstream PLU units affected: PLU-03, PLU-04, PLU-05, PLU-06, PLU-07.

## Managed Database Decision

Decision: use managed PostgreSQL.

Preference: use Render Postgres for the initial deployment so hosting and database operations remain within the already-rehearsed platform, unless PLU-03 discovers a concrete blocker.

Production requirements:

- Explicit deployed database URL.
- SQLAlchemy-compatible connection.
- Alembic migration support.
- Staging and production database separation.
- Backups/snapshots and restore capability.

Rationale: S1-05 intentionally does not hard-code a database vendor, but managed PostgreSQL is the natural production target for the selected Render platform and current SQLAlchemy/Alembic architecture.

Downstream PLU units affected: PLU-03, PLU-06, PLU-07.

## Secrets Strategy

Decision: use Render-managed environment variables, secrets, or environment groups for v1.

Requirements:

- Keep staging and production secrets isolated.
- Never store actual credentials in Git or documentation.
- Use Render configuration for Auth0, database, CORS, usage limits, and provider flags.
- Evaluate a dedicated external secret manager post-launch only if operational requirements justify it.

Responsible owner: Project Owner.

Rotation expectation: rotation must be possible through Render-managed configuration without source-code changes; exact rotation cadence can be revisited post-launch.

Downstream PLU units affected: PLU-03, PLU-04, PLU-05, PLU-06.

## Domain / DNS / TLS

Decision:

- Production base domain: `[YOUR_DOMAIN]`
- Production frontend: `https://app.[YOUR_DOMAIN]`
- Production API: `https://api.[YOUR_DOMAIN]`
- Staging frontend: `https://staging.[YOUR_DOMAIN]`
- Staging API: `https://api-staging.[YOUR_DOMAIN]`
- DNS provider: `[YOUR_DNS_PROVIDER]`
- TLS: Render-managed TLS certificates and HTTPS enforcement.

Provisioning note: the literal production domain and DNS provider values must be resolved before Production GO. Until custom domains are configured, Render-provided service domains may be used for staging and integration work.

Rationale: the hostname pattern gives PLU-02 and PLU-03 stable callback/CORS/TLS targets while preserving the unresolved literal domain as a provisioning detail.

Downstream PLU units affected: PLU-02, PLU-03, PLU-05, PLU-07.

## Staging Strategy

Decision: production-like staging for v1 must use:

- Real Auth0 staging tenant.
- Managed PostgreSQL staging database.
- Render-hosted frontend and backend.
- Staging secrets.
- Real startup/readiness configuration.
- Mock/curated product providers.

Do not enable live LLM, vector, POI, routing, ticketing, TTS, or affiliate providers in the v1 staging path.

Rationale: staging must prove auth, database, deployment, readiness, observability, backup, and rollback behavior without adding live product-provider complexity.

Downstream PLU units affected: PLU-02, PLU-03, PLU-05, PLU-06, PLU-07.

## CI/CD Policy

Decision: use GitHub Actions.

Policy:

- PR checks required before merge.
- Protect `main`.
- Automate backend full pytest.
- Automate frontend typecheck.
- Automate frontend full tests.
- Automate frontend production build.
- Automate migration/config validation.
- Add dependency/security scanning.
- Add secret scanning.
- Staging deployments may be automated after required checks pass.
- Production deployment requires manual approval.
- Production migration execution is a controlled release step, not automatic request/startup behavior.

Rationale: the repository currently lacks checked-in GitHub workflows; this policy creates repeatable gates while keeping production deployment controlled.

Downstream PLU units affected: PLU-04, PLU-07.

## Observability

Decision: use a minimal hosted production observability architecture.

Required before Production GO:

- Retained backend/platform logs.
- Frontend application error reporting.
- Backend application error reporting.
- External frontend/backend uptime monitoring.
- `/api/health` monitoring.
- `/api/readiness` monitoring.
- Alerts for startup/readiness failures.
- Alerts for database connectivity/migration failures.
- Alerts for Auth0/JWKS/auth failures.
- Alerts for abnormal 5xx rates.
- Alerts for rate/quota exhaustion.
- Alerts for usage-control failures.

Live-provider latency/spend alerting can remain disabled until PLU-08 because live product providers are out of v1.

Rationale: this meets the launch safety requirement without forcing an enterprise observability stack.

Downstream PLU units affected: PLU-05, PLU-07.

## Backup / Restore / Rollback Policy

Decision: use the approved custom policy.

Policy:

- Use paid managed PostgreSQL with provider point-in-time recovery where available.
- Run daily logical database backup/export.
- Retain an external copy for 30 days.
- Create and verify a backup or snapshot before every production migration.
- Complete at least one restore rehearsal to a disposable database before Production GO.
- Document migration rollback and application rollback procedures.
- Launch RPO target: 24 hours maximum for the logical-backup layer, with provider PITR used for finer recovery where available.
- Launch RTO target: 4 hours.
- More advanced disaster recovery is post-launch.

Rationale: this gives launch-level recovery proof without overbuilding mature disaster recovery before v1.

Downstream PLU units affected: PLU-03, PLU-06, PLU-07.

## Usage Quotas / Budgets

Decision: approve the existing production-template limits as initial starting values unless validation reveals an unsafe setting.

Approved initial values from `.env.production.example`:

- `ANONYMOUS_ITINERARY_GENERATIONS_PER_MINUTE=3`
- `ANONYMOUS_ITINERARY_GENERATIONS_PER_DAY=20`
- `REGISTERED_USER_ITINERARY_GENERATIONS_PER_MINUTE=10`
- `REGISTERED_USER_ITINERARY_GENERATIONS_PER_DAY=50`
- `SUBSCRIBER_CHAT_MESSAGES_PER_MINUTE=20`
- `SUBSCRIBER_CHAT_MESSAGES_PER_DAY=100`
- `PROVIDER_DAILY_REQUEST_CEILING=100`
- `PROVIDER_DAILY_COST_CEILING_USD=0`
- `LLM_DAILY_LIVE_REQUEST_CEILING=0`
- `LLM_DAILY_ESTIMATED_SPEND_CEILING_USD=0`
- `USAGE_COUNTER_RETENTION_DAYS=90`

Because v1 has no live product providers:

- Live product-provider cost budget is `$0`.
- Live LLM/vector/POI/routing/ticketing/TTS/affiliate calls remain disabled.
- Durable abuse/rate limits remain enabled for public and authenticated application operations.
- Any later live-provider rollout requires an explicit new budget decision.

Downstream PLU units affected: PLU-03, PLU-05, PLU-07, PLU-08 post-launch.

## Usage Cleanup

Decision: run expired usage-counter cleanup daily using a Render scheduled/cron job.

Rationale: S1-04 implemented cleanup logic, and daily cleanup is sufficient for initial traffic while preventing unbounded growth of expired counter rows.

Downstream PLU units affected: PLU-05.

## Seed / Reference Data

Decision: use reviewed curated seed/reference data for the initial production release.

Before production seeding:

- Explicitly identify approved production destinations, books, POIs, and public itineraries.
- Exclude test/demo-only records.
- Use a controlled migration/release operation.
- Do not automatically treat all development seed content as production-approved.

Rationale: current seed/reference data supports the mock/curated-provider v1, but production content approval must be explicit.

Downstream PLU units affected: PLU-03, PLU-06, PLU-07.

## Privacy / Data Handling

Decision: initial v1 privacy/data-handling posture:

- Account deletion: documented manual support process for v1.
- User-data deletion: documented manual support process for v1.
- Users must have a documented way to request deletion.
- Support must have an operational deletion procedure.
- Deletion behavior must respect relational ownership and applicable retained operational data.
- Self-service deletion may be implemented post-launch unless later product/legal review makes it a launch requirement.
- Production application/error logs: retain 30 days.
- Usage-counter operational data: maximum 90 days, with expired window cleanup daily.
- Subscriber chat: not part of v1; do not create a new v1 chat-retention policy.
- Account/profile/preferences/bookmarks/reviews/private records: retain while the account is active unless deletion is requested or a later approved policy says otherwise.
- Analytics: no product analytics in initial v1.
- Use only operational logging/error/uptime monitoring required to run the service safely.
- Product analytics may be added post-launch after an explicit privacy/product decision.
- Privacy/legal review remains required before public user-data collection.

Rationale: this keeps v1 privacy scope minimal and operationally clear while avoiding legal conclusions in engineering docs.

Downstream PLU units affected: PLU-06, PLU-07.

## Security Launch Requirements

Decision: require before Production GO:

- Exact production CORS allowlist.
- CSP/security headers.
- Dependency vulnerability scanning.
- Secret scanning.
- Production debug-route verification.
- Production admin-route verification.
- Production exception-leakage review.
- Sensitive-log review.
- HTTPS-only public endpoints.
- Existing backend authorization remains the source of truth.

Rationale: these are launch safety requirements and belong to PLU-04/PLU-06 rather than PLU-01.

Downstream PLU units affected: PLU-04, PLU-06, PLU-07.

## Support / Incident Ownership

Decision: use role-based ownership for now:

- Incident owner: `Project Owner`
- Security contact: `Project Owner`
- DB/backup owner: `Project Owner`
- Auth owner: `Project Owner`
- Support contact: `Project Owner`
- Final GO/NO-GO authority: `Project Owner`

These roles may be delegated to named people before Production GO, but they must never remain unowned.

Downstream PLU units affected: PLU-05, PLU-06, PLU-07.

## Git Checkpoint Decision

Decision: create a clean Git checkpoint containing the completed S1-01 through S1-05 production-foundation work before PLU-02 begins.

Constraints:

- Do not discard or rewrite existing work.
- Do not commit or push unless the owner separately authorizes the Git operation.

Rationale: S1-01 through S1-05 remain uncommitted in the current working tree. PLU-02 should begin from a clean checkpoint so auth implementation does not mix with the foundation backlog.

Downstream PLU units affected: precondition for PLU-02 and recommended before other downstream PLU work.

## Conditional / Deferred Decisions

- PLU-08 is post-launch and not required for initial Production GO.
- Live-provider budgets, credentials, monitoring, rollback, and privacy disclosures are deferred until a later explicit live-provider decision.
- Subscriber chat/refinement is excluded from public v1 and should be revisited post-launch.
- Private itinerary CRUD/share/unlisted scope is post-launch.
- Product analytics are post-launch.
- Self-service account/data deletion is post-launch unless later product/legal review makes it launch-required.
- Dedicated external secret manager is post-launch unless Render-managed secrets prove insufficient.

## Decisions Requiring Revisit

- Replace `[YOUR_DOMAIN]` and `[YOUR_DNS_PROVIDER]` with literal production values before Production GO.
- Delegate role-based owners to named people before Production GO if the Project Owner chooses.
- Confirm Render Postgres does not present a concrete blocker during PLU-03.
- Confirm production seed/reference content list before seeding production.
- Revisit quotas if staging validation shows unsafe limits.
- Revisit live-provider scope and budgets before any PLU-08 work.
