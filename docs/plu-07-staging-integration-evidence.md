# PLU-07 Staging Integration Evidence

Status: local repository preparation only. External owner-controlled activation is not authorized in this session.

## Local Commit

- Local PLU-07 commit: pending local commit.
- Starting SHA: `f2b22b91c978137ebe4f1291e73218fc67b1c0c5`.
- Branch: `plu-07-staging-integration`.
- Pushed: no.
- PR #1 modified: no.
- Merged to `main`: no.

## Code-Level Readiness

- Backend release identity: `/api/version` returns `releaseSha` and `environment` only.
- Backend release source: `RENDER_GIT_COMMIT`, with safe local fallbacks to `APP_RELEASE_SHA`, `GITHUB_SHA`, then `unknown`.
- Frontend release identity: `/release.json` generated during build from `RENDER_GIT_COMMIT`, with safe fallbacks.
- Runtime dependency constraints: `backend/constraints-runtime.txt`.
- Regeneration command:

```powershell
python -m venv tests\.artifacts\tmp\runtime-lock
tests\.artifacts\tmp\runtime-lock\Scripts\python.exe -m pip install -r backend\requirements-runtime.txt
tests\.artifacts\tmp\runtime-lock\Scripts\python.exe -m pip freeze --exclude-editable
```

- Render backend install: `pip install -r requirements.txt -c constraints-runtime.txt`.
- CI backend install: `pip install -r backend/requirements-ci.txt -c backend/constraints-runtime.txt`.
- CI runtime audit: `pip-audit -r backend/constraints-runtime.txt --strict`.

## Staging Deployment Pipeline

- Backend hook secret name: `RENDER_STAGING_BACKEND_DEPLOY_HOOK_URL`.
- Frontend hook secret name: `RENDER_STAGING_FRONTEND_DEPLOY_HOOK_URL`.
- Backend URL variable name: `STAGING_BACKEND_BASE_URL`.
- Frontend URL variable name: `STAGING_FRONTEND_BASE_URL`.
- Database secret name: `STAGING_DATABASE_URL`.
- Exact release ref: `github.event.workflow_run.head_sha` for CI-triggered deploys; `github.sha` for manual dispatch.
- Deploy selector: Render deploy hook `ref` query parameter.
- Release verification: bounded polling of backend `/api/version` and frontend `/release.json` before public smoke.

## Staging Seed Data

Seed source: bundled public/reference data only.

Expected reference counts:

- Destinations: 5.
- Books: 10.
- POIs: 13.
- Seed itineraries: 2.

The staging workflow runs `python -m scripts.seed_database` after migrations and before deploy. The seed is rerunnable and does not truncate user tables. It updates fixed reference IDs and replaces only fixed bundled seed itinerary IDs, avoiding duplicate reference rows.

## Owner Activation Required

No real hosted resources were configured in this local session. The owner must complete and record:

- Auth0 staging API and SPA, using a dedicated staging tenant/application configuration.
- Auth0 exact staging callback, logout, and web origin URLs after Render frontend exists.
- Render staging PostgreSQL, backend, and frontend only.
- Render backend CORS origin set to the exact staging frontend origin.
- GitHub `staging` environment secrets and variables by name only:
  - `STAGING_DATABASE_URL`
  - `RENDER_STAGING_BACKEND_DEPLOY_HOOK_URL`
  - `RENDER_STAGING_FRONTEND_DEPLOY_HOOK_URL`
  - `STAGING_BACKEND_BASE_URL`
  - `STAGING_FRONTEND_BASE_URL`
- Existing PR #1 fast-forward only after verifying remote head and owner approval.
- Main merge only after owner approval and all checks are green.
- Real staging deployment from the exact merged `main` SHA.
- Real Auth0 interactive browser/API flow.
- CORS validation from approved and unapproved origins.
- Render health and notification activation.
- Hosted PostgreSQL backup creation and verification.
- Managed recovery capability inspection from the actual Render database.
- Isolated PostgreSQL recovery rehearsal.
- Application rollback and redeploy rehearsal.

## External Evidence Placeholders

- PR CI run: not available; branch not pushed.
- Staging deploy workflow run: not available.
- Render backend URL: not configured.
- Render frontend URL: not configured.
- Backend release SHA: not deployed.
- Frontend release SHA: not deployed.
- PostgreSQL major version and plan label: not configured.
- Migration revision: not verified on hosted staging.
- Auth0 tenant/domain label: not configured.
- API audience: not configured.
- Auth0 E2E result: not executed.
- CORS result: not executed.
- Monitoring/notification result: not executed.
- Backup result: not executed.
- Managed recovery capability: not inspected.
- Recovery rehearsal result: not executed.
- Rollback target SHA: not selected for hosted rollback.
- Rollback result: not executed.
- Redeploy result: not executed.
- Final integrity result: not executed on hosted staging.

No credentials, deploy-hook URLs, database URLs, bearer tokens, JWTs, cookies, or passwords belong in this document.
