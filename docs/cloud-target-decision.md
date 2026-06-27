# Cloud Target Decision

## Purpose

This document frames the choice of the first non-production cloud target for a
Litinerary cloud offline deployment rehearsal. The first target must support a
mock-only deployment, health/readiness evidence, logs/redaction review, rollback
evidence, and non-production database migration/seed rehearsal.

Render has been selected as the first target for target-specific cloud offline
rehearsal assets. This document still does not approve any cloud deployment or
cloud resource changes.

## Decision Criteria

The first target should optimize for:

- simple backend and frontend deployment
- explicit non-production isolation
- secure runtime configuration without tracked secrets
- durable logs with retention/redaction review
- straightforward rollback or shutdown
- non-production database migration and seed support
- low operational complexity
- no live provider credentials
- no external provider calls

## Options

| Option | Fit for current Litinerary state | Complexity | Cost/risk | Secret management | Logs/monitoring | Rollback | Database/migration support | Mock-only offline rehearsal | Later staged internal testing | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single VM/VPS | Can run backend, frontend preview/static server, and database tools directly. Simple mental model, but more manual ops. | Medium | Low cost, higher patching/ops risk | Usually env files or platform secrets; must avoid tracked files | Depends on OS/log agent setup | Manual process stop, image snapshot, or redeploy | Flexible; operator-managed DB or managed DB client | Good if locked down and non-public | Weak unless access boundary and monitoring are added | Acceptable fallback, not first choice unless user already has VPS workflow. |
| Container platform | Good fit for backend packaging and repeatable env posture; frontend can be static or containerized. | Medium | Moderate cost/risk; clearer artifact boundary | Strong if platform provides secret/config vars | Usually good built-in logs | Revision rollback often supported | Works with managed DB and migration job/container | Strong | Good foundation for staged internal once blockers close | Strong candidate if user is comfortable with containers. |
| PaaS/app platform | Good fit for current app: managed build/deploy, env vars, logs, rollback, simple services. | Low to medium | Often low initial cost, lower ops burden | Usually strong config/secret separation | Usually built-in logs and request views | Built-in rollback/redeploy common | Managed DB add-ons or external DB supported | Strong | Good if private/internal access controls are available | Conservative first recommendation, pending user approval. |
| Managed Kubernetes | Flexible and scalable, but heavy for current rehearsal stage. | High | Higher cost and operational risk | Strong via secrets, but more complex | Strong if configured, not automatic | Strong with deployments, but requires setup | Strong, but migration jobs need discipline | Possible, but overkill | Good later if scale/ops team require it | Not recommended for first offline rehearsal. |
| Static frontend + managed backend/API | Matches frontend/backend split; frontend static hosting plus managed API/runtime. | Low to medium | Low cost; cross-service config/CORS risk | Strong if platform supports env/secret config | Good if both services expose logs | Frontend/backend rollback separately | Managed DB typically supported for backend | Strong | Good if internal access boundary can cover both services | Recommended if platform has simple managed backend and static hosting. |
| Database hosting options | Required companion choice: managed Postgres-like service, managed SQLite-compatible service, or platform DB add-on. | Varies | Managed DB lowers ops risk; cost depends on provider | Must use cloud secret/config store | DB logs and audit vary | Snapshot/restore or disposable rehearsal DB | Must support migrations and seed reset/validate | Strong if disposable non-production DB | Required for later staged testing | Prefer disposable managed non-production DB with snapshot/restore or easy reset. |

## Conservative Recommendation

If no platform has already been selected, use the simplest safe non-production
PaaS/app platform or static-frontend-plus-managed-backend target that provides:

- managed runtime configuration without tracked secrets
- built-in service logs with retention settings
- revision rollback or one-command shutdown
- a non-production managed database
- private or restricted preview access
- health/readiness endpoint reachability

This recommendation is intentionally conservative: it minimizes operational
surface while producing the evidence needed for the mock-only cloud rehearsal.

## Required User Approval

Before execution on Render, the user must approve:

- selected cloud provider/platform
- cloud project/account
- non-production environment name
- database choice
- log sink
- rollback method
- access restrictions
- operator

Do not deploy or create cloud resources until that approval exists.

## Current Decision Status

- Recommended first target type: PaaS/app platform or static frontend plus
  managed backend/API, with managed non-production database.
- Selected target: Render.
- Target-specific Render assets:
  - `docs/cloud-offline-deployment-render.md`
  - `docs/cloud-offline-env-render.template.md`
  - `docs/cloud-offline-checklist-render.md`
  - `docs/cloud-offline-rehearsal-record-render.md`
- Placeholder assets retained for future target comparison:
  - `docs/cloud-offline-deployment-cloud-target-placeholder.md`
  - `docs/cloud-offline-env-cloud-target-placeholder.template.md`
  - `docs/cloud-offline-checklist-cloud-target-placeholder.md`
  - `docs/cloud-offline-rehearsal-record-cloud-target-placeholder.md`
- Cloud offline rehearsal status: not executed.
- Cloud deployment executed: no.
- Cloud resources created: no.
- Live providers enabled: no.
- Local live deployment: blocked.
- Staged internal testing: `No-go`.
- Public/beta live generation: `No-go`.
