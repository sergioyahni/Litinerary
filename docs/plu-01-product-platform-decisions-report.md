# PLU-01 Product / Platform Decisions Report

Date: 2026-08-15

## Executive Summary

PLU-01 is complete. The Product / Vendor / Platform Decisions gate is locked well enough to begin downstream production implementation without Codex inventing vendor, product, privacy, hosting, database, budget, or operations policy.

Owner-approved decisions are recorded in `docs/production-decisions.md`. The approved initial v1 is a narrow mock/curated-provider production launch with Auth0 managed authentication, Render frontend/backend hosting, managed PostgreSQL with Render Postgres preferred, Render-managed secrets, GitHub Actions CI/CD, daily usage-counter cleanup, minimal hosted observability, documented manual deletion support, and no live product providers in v1.

No PLU-02 through PLU-08 implementation work was performed. No Git checkpoint was created because the owner explicitly required a checkpoint before PLU-02 but did not authorize a commit or push in this session.

## Starting Repository State

| Item | Evidence |
|---|---|
| Repository | `C:\Users\syahn\source\litinerary` |
| Branch | `main...origin/main` |
| Commit | `86a40dc90ff7dcfd4497ef1da190dc2da35e73ca` |
| Migration head | `20260815_0009 (head)` |
| Working tree | Dirty with S1-01 through S1-05 modified tracked files and untracked reports/migrations/tests. |
| S1 checkpoint state | Required before PLU-02, not yet created. |

## Decisions Reviewed

- S1 production-foundation Git checkpoint.
- Initial v1 launch scope.
- Live product-provider stance.
- Private itinerary CRUD/share scope.
- Subscriber chat/refinement scope.
- Managed auth provider and tenant strategy.
- Backend/frontend hosting.
- Managed database platform.
- Secrets/configuration strategy.
- Domain/DNS/TLS plan.
- Observability architecture.
- Backup/restore/rollback policy.
- Quotas, budgets, and usage cleanup.
- Production seed/reference-data strategy.
- Privacy/data-handling posture.
- Security launch posture.
- CI/CD policy.
- Production-like staging strategy.
- Support and incident ownership.

## Approved Litinerary v1 Scope

Approved v1 includes:

- Real Auth0 managed authentication.
- Real Render production infrastructure.
- Managed PostgreSQL persistence.
- Durable usage controls.
- Public browsing/generation.
- Existing authenticated profile, preferences, bookmarks, and reviews functionality.
- Curated/seeded/mock product-provider behavior.

## Deferred Scope

Deferred until post-launch:

- Live LLM, vector, POI, routing, ticketing, TTS, affiliate, payment, and commerce integrations.
- Private itinerary list, save, edit, delete, publish, unpublish, sharing links, and true unlisted sharing.
- Subscriber chat/refinement as a public v1 journey.
- Product analytics.
- Self-service account/data deletion unless later product/legal review makes it launch-required.
- Mature disaster-recovery drills beyond the launch minimum.

## Managed Auth Decision

Decision: Auth0.

Approved strategy:

- Separate Auth0 staging and production tenants.
- Separate staging and production apps, users, callbacks, secrets, and configuration.
- Integrate Auth0 with the existing provider-neutral backend issuer/audience/JWKS architecture.
- Do not redesign backend authorization around vendor-specific identity logic.

PLU-02 must provision/configure tenant/app details, then implement frontend login, callback, token acquisition, session persistence, refresh, logout, `/api/me` hydration, protected-feature UX, and staging auth smoke/E2E validation.

## Infrastructure Decisions

Decision:

- Backend hosting: Render.
- Frontend hosting: Render.
- TLS: Render-managed TLS and HTTPS enforcement.
- Staging and production environments must be separated.

Rationale: Render has repository-specific rehearsal and runbook evidence.

## Database Decision

Decision: managed PostgreSQL.

Preference: Render Postgres for the initial deployment unless PLU-03 discovers a concrete blocker.

Requirements:

- Explicit deployed DB URL in secrets.
- Staging and production database separation.
- Alembic migration support.
- Backups/snapshots and restore capability.

## Secrets Strategy

Decision: Render-managed environment variables, secrets, or environment groups for v1.

Requirements:

- Separate staging and production secrets.
- No real secrets in Git, docs, templates, test fixtures, logs, or shell history intended for sharing.
- Dedicated external secret manager is deferred unless Render-managed secrets prove insufficient.

## Domain / DNS / TLS

Approved pattern:

- Production base domain: `[YOUR_DOMAIN]`
- Production frontend: `https://app.[YOUR_DOMAIN]`
- Production API: `https://api.[YOUR_DOMAIN]`
- Staging frontend: `https://staging.[YOUR_DOMAIN]`
- Staging API: `https://api-staging.[YOUR_DOMAIN]`
- DNS provider: `[YOUR_DNS_PROVIDER]`
- TLS: Render-managed certificates and HTTPS enforcement.

Remaining provisioning detail: replace `[YOUR_DOMAIN]` and `[YOUR_DNS_PROVIDER]` with literal values before Production GO. Render-provided service domains may be used for staging and integration work until custom domains are configured.

## Observability Decision

Decision: minimal hosted production observability.

Required:

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

Live-product-provider latency/spend alerting is deferred until PLU-08 because live product providers are out of v1.

## Backup / Recovery Decision

Decision: approved custom backup/recovery policy.

Policy:

- Paid managed PostgreSQL with provider point-in-time recovery where available.
- Daily logical database backup/export.
- External backup copy retained for 30 days.
- Backup or snapshot before every production migration.
- At least one restore rehearsal to a disposable database before Production GO.
- Documented migration rollback and application rollback procedures.
- Launch RPO: 24 hours maximum for the logical-backup layer, with provider PITR used for finer recovery where available.
- Launch RTO: 4 hours.

## Usage / Budget Decision

Decision: approve existing production-template limits as initial values unless validation reveals an unsafe setting.

Initial v1 stance:

- Live product-provider cost budget: `$0`.
- Live LLM/vector/POI/routing/ticketing/TTS/affiliate calls disabled.
- Durable abuse/rate limits enabled for public and authenticated operations.
- Any later live-provider rollout requires a new explicit budget decision.

## Privacy / Data Handling Decision

Decision:

- Manual support process for account deletion and user-data deletion in v1.
- Users must have a documented way to request deletion.
- Support must have an operational deletion procedure.
- Deletion behavior must respect relational ownership and applicable retained operational data.
- Logs retained 30 days.
- Usage counters retained maximum 90 days, with daily cleanup.
- Subscriber chat is not part of v1, so no new v1 chat-retention policy is created.
- Account/profile/preferences/bookmarks/reviews/private records retained while active unless deletion is requested or a later approved policy says otherwise.
- No product analytics in initial v1.
- Privacy/legal review remains required before public user-data collection.

No legal conclusion is provided.

## CI/CD Policy

Decision: GitHub Actions.

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
- Production migrations are controlled release steps, not automatic request/startup actions.

## Staging Strategy

Decision: production-like staging using:

- Real Auth0 staging tenant.
- Managed PostgreSQL staging database.
- Render-hosted frontend/backend.
- Staging secrets.
- Real startup/readiness configuration.
- Mock/curated product providers.

Do not enable live LLM/vector/POI/routing/ticketing/TTS/affiliate providers in the v1 staging path.

## Support / Incident Ownership

Role-based ownership:

- Incident owner: `Project Owner`
- Security contact: `Project Owner`
- DB/backup owner: `Project Owner`
- Auth owner: `Project Owner`
- Support contact: `Project Owner`
- Final GO/NO-GO authority: `Project Owner`

These roles may be delegated to named people before Production GO, but they must never remain unowned.

## Git Checkpoint Decision

Decision: create a clean Git checkpoint containing completed S1-01 through S1-05 production-foundation work before PLU-02 begins.

Constraint: do not commit or push unless the owner separately authorizes the Git operation.

Status: approved as a required pre-PLU-02 action, not performed in this session.

## External Resources To Provision

| Resource | Purpose | Required For |
|---|---|---|
| Auth0 staging tenant/app | Staging login/JWKS/callback/logout. | PLU-02 |
| Auth0 production tenant/app | Production login/JWKS/callback/logout. | PLU-02 |
| Render backend service | Production and staging API hosting. | PLU-03 |
| Render frontend service | Production and staging frontend hosting. | PLU-03 |
| Render Postgres or approved managed PostgreSQL | Staging and production persistence. | PLU-03 |
| Render environment/secrets/groups | Auth0, DB, CORS, quotas, provider flags. | PLU-03 |
| Domain and DNS records | Public/staging hostnames and Auth0 callbacks. | PLU-03 / before GO |
| Monitoring/error reporting/uptime tooling | Logs, errors, uptime, health/readiness, alerting. | PLU-05 |
| Backup/export storage | 30-day external logical backup copy. | PLU-06 |
| GitHub Actions configuration | CI/CD gates and deployment policy. | PLU-04 |

## Gate A Status

Gate A: COMPLETE.

Reason: v1 scope, live-provider stance, private itinerary scope, subscriber chat scope, Auth0, Render, managed PostgreSQL, Render secrets, domain pattern, staging strategy, CI/CD policy, observability, backup/recovery, quotas/budgets, usage cleanup, seed strategy, privacy/data handling, security posture, support/incident ownership, and Git checkpoint strategy are explicitly recorded.

Remaining literal domain/DNS values and optional named-person delegation are provisioning/finalization items, not unresolved Gate A decisions.

## Next Implementation Unit

PLU-02: Managed Auth0 provider and frontend session integration.

Prerequisite: create the owner-approved S1-01 through S1-05 Git checkpoint before PLU-02 begins, after separate owner authorization to commit/push.

Why PLU-02 next:

- Auth0 is now selected.
- Real frontend auth is the direct blocker for public authenticated v1 journeys.
- Backend managed-JWT validation already exists and should be integrated rather than redesigned.

Why PLU-03 follows:

- Render/DB/secrets decisions are locked, but Auth0 callback/session behavior shapes deployed frontend/backend configuration and staging smoke requirements.

## Remaining Owner Decisions

No Gate A blocking decisions remain.

Provisioning/finalization items before Production GO:

- Replace `[YOUR_DOMAIN]` with the literal production domain.
- Replace `[YOUR_DNS_PROVIDER]` with the literal DNS provider.
- Optionally delegate Project Owner role-based responsibilities to named people.
- Authorize the Git checkpoint commit/push before PLU-02.

## Prompt Compliance Matrix

| # | Requirement | Status | Evidence |
| - | ----------- | ------ | -------- |
| 1 | Read authoritative production planning documents. | DONE | Read production launch plan, production progress, and S1-02 through S1-05 reports before recording decisions. |
| 2 | Inspect current Git/repository state. | DONE | Branch, commit, status, untracked/modified state, migration head, and recent history inspected. |
| 3 | Create repository checkpoint decision. | DONE | Checkpoint decision recorded; no commit/push performed. |
| 4 | Verify recommended v1 scope. | DONE | Owner approved narrow mock/curated-provider v1. |
| 5 | Lock v1 live-provider stance. | DONE | No live product providers in v1; PLU-08 post-launch. |
| 6 | Lock private itinerary product scope. | DONE | Private CRUD/share/unlisted deferred post-launch. |
| 7 | Lock subscriber chat/refinement scope. | DONE | Subscriber chat/refinement excluded from initial public v1. |
| 8 | Managed authentication provider decision. | DONE | Auth0 selected with separate staging/prod tenants. |
| 9 | Lock frontend/backend hosting target. | DONE | Render selected for frontend and backend. |
| 10 | Lock managed database target. | DONE | Managed PostgreSQL selected, Render Postgres preferred. |
| 11 | Lock secrets/configuration strategy. | DONE | Render-managed environment/secrets/groups selected. |
| 12 | Lock domain/DNS/TLS plan. | DONE | Hostname pattern and Render-managed TLS approved; literal values remain provisioning details. |
| 13 | Lock production observability approach. | DONE | Minimal hosted observability architecture approved. |
| 14 | Lock backup and recovery policy. | DONE | Custom backup/RPO/RTO/restore/rollback policy approved. |
| 15 | Lock launch usage quotas and budgets. | DONE | Production-template limits and `$0` live-provider cost budget approved. |
| 16 | Lock usage-counter cleanup operations. | DONE | Daily Render scheduled/cron cleanup approved. |
| 17 | Lock production seed/reference-data strategy. | DONE | Reviewed curated seed/reference data approved with explicit content review. |
| 18 | Lock privacy/data-handling posture. | DONE | Manual deletion process, retention, no analytics, and legal/privacy review requirement recorded. |
| 19 | Lock security-launch posture. | DONE | CORS, CSP/headers, dependency scan, secret scan, debug/admin, exception, log, HTTPS requirements approved. |
| 20 | Lock CI/CD policy decisions. | DONE | GitHub Actions policy approved. |
| 21 | Lock staging strategy. | DONE | Render/Auth0/PostgreSQL staging with mock product providers approved. |
| 22 | Lock support and incident ownership. | DONE | Role-based Project Owner ownership recorded. |
| 23 | Present one consolidated decision worksheet. | DONE | Worksheet was presented in the prior PLU-01 response and owner supplied answers. |
| 24 | Do not proceed past unresolved blocking decisions. | DONE | Stopped previously; continued only after owner-approved decisions were supplied. |
| 25 | Create approved decision record. | DONE | `docs/production-decisions.md` created. |
| 26 | Update production launch plan. | DONE | `docs/production-launch-plan.md` updated. |
| 27 | Update production development progress. | DONE | `docs/production-development-progress.md` updated. |
| 28 | Determine Gate A status. | DONE | Gate A marked complete. |
| 29 | Determine exact next implementation unit. | DONE | PLU-02 selected, with checkpoint precondition. |
| 30 | Create PLU-01 closeout report. | DONE | This report is `docs/plu-01-product-platform-decisions-report.md`. |
| 31 | Prompt compliance matrix. | DONE | This matrix includes rows 1 through 31 individually. |
