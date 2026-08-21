# PLU-04 GitHub Actions CI/CD Closeout Report

Date: 2026-08-21

Repository: `C:\Users\syahn\source\litinerary`

PLU-04 STATUS: PARTIAL - LOCAL HARDENING COMPLETE, REMOTE EVIDENCE PENDING

## 1. Verdict

PLU-04 is locally hardened and ready for remote validation, but it is not fully complete until the feature branch is pushed, GitHub Actions run on GitHub, and owner/admin repository settings are enabled and verified.

## 2. Previous Report Corrections

Earlier PLU-04 notes said the GitHub repository was inaccessible and returned `404`. That was incorrect for public metadata inspection.

Verified remote facts on 2026-08-21:

- Remote: `https://github.com/sergioyahni/Litinerary.git`
- Repository: `sergioyahni/Litinerary`
- Visibility: public
- Default branch: `main`
- Remote `main` SHA: `86a40dc90ff7dcfd4497ef1da190dc2da35e73ca`
- Local `main` HEAD before PLU-04 closeout commit: `8263cf1bca8a3125a039bb0388325b03cd4ec9ee`
- Local `main` was ahead of `origin/main` by two prior commits:
  - `e9fc587 Complete production foundation through PLU-01`
  - `8263cf1 Add Auth0 integration and Render staging foundation`
- Remote `main` branch protection: disabled
- Required status checks on remote `main`: disabled
- Remote workflows before PLU-04 push: `0`

## 3. Files Changed

PLU-04 adds or updates:

- `.github/workflows/ci.yml`
- `.github/workflows/deploy-staging.yml`
- `.github/workflows/deploy-production.yml`
- `scripts/ci/validate_workflows.py`
- `scripts/ci/secret_hygiene.py`
- `scripts/ci/frontend_audit_policy.py`
- `scripts/ci/validate_config_profiles.py`
- `scripts/ci/migration_seed_check.py`
- `scripts/ci/post_deploy_smoke.py`
- `backend/requirements.txt`
- `backend/requirements-runtime.txt`
- `backend/requirements-ci.txt`
- `backend/runtime.txt`
- `frontend/.nvmrc`
- `frontend/package.json`
- `frontend/package-lock.json`
- `render.yaml`
- `docs/plu-04-github-actions-cicd-report.md`
- `docs/production-development-progress.md`
- `docs/production-launch-plan.md`

## 4. Workflow Security Audit

Implemented workflow posture:

- Workflows default to `permissions: contents: read`.
- No workflow uses `pull_request_target`.
- No workflow grants `contents: write`, `actions: write`, `packages: write`, or `id-token: write`.
- Official GitHub actions are pinned to full-length SHAs with version comments.
- `actions/checkout` uses `persist-credentials: false`.
- Every job has `timeout-minutes`.
- CI runs on pull requests to `main`, pushes to `main`, pushes to `plu-04-*` feature branches, and manual dispatch.
- Staging deploy runs only after successful CI on `main` or manual dispatch.
- Production deploy is manual dispatch only.
- Deployment secrets are referenced only inside `staging` and `production` environment jobs.

The workflow validator enforces these policies and also verifies GitHub Actions YAML parsing treats `on` as a string key.

## 5. Secret Security

Added `scripts/ci/secret_hygiene.py`.

Coverage:

- Current tracked files.
- Reachable committed Git history via `--history`.
- High-confidence private keys, API tokens, bearer tokens, Auth0 client secrets, cloud credentials, and non-placeholder database URLs.
- Findings print category/path/blob metadata only, not secret values.

Local results:

- Current tree secret hygiene: passed.
- Reachable Git history secret hygiene: passed.

Owner/admin actions still required:

- Enable GitHub secret scanning where available.
- Enable push protection where available.
- Store real Auth0, Render, database, and deploy-hook secrets only in external secret stores or GitHub Environments.

## 6. Dependency Security

Frontend before remediation:

- `npm audit --json` found 5 dev-tooling vulnerabilities:
  - `vitest` critical, GHSA-5xrq-8626-4rwp, affected `<3.2.6`.
  - `vite` high/moderate advisories including GHSA-fx2h-pf6j-xcff, GHSA-v6wh-96g9-6wx3, GHSA-4w7w-66w2-5vf9.
  - `esbuild` moderate, GHSA-67mh-4wv8-2f99.
  - Transitive `@vitest/mocker` and `vite-node` findings.

Remediation:

- Upgraded Vitest from `^2.1.8` to `^3.2.6`.
- Did not use the npm-suggested semver-major Vitest 4 forced fix.

Frontend after remediation:

- `npm audit --omit=dev --audit-level=high`: 0 vulnerabilities.
- `npm audit --json`: 0 vulnerabilities.
- `scripts/ci/frontend_audit_policy.py`: no high/critical frontend audit findings present.

Backend:

- Split runtime and CI requirements.
- `backend/requirements.txt` now points to runtime requirements.
- `backend/requirements-runtime.txt` excludes pytest.
- `backend/requirements-ci.txt` includes runtime plus pytest.
- `pip-audit` passed for both runtime and CI requirements.

## 7. Migration Safety

Current Alembic head: `20260815_0009`.

Upgrade-path review:

- Existing migrations are primarily create-table, add-column, index, and metadata additions.
- `20260815_0008` normalizes itinerary visibility, clears orphaned owner/creator references, adds an owner foreign key with `ON DELETE SET NULL`, and adds lookup indexes.
- `20260815_0009` creates durable usage counters.
- Downgrade paths contain destructive drops, but deployment workflows run upgrade only.

Deployment policy:

- Migrate-before-deploy is acceptable only for additive/backward-compatible migrations like the current upgrade path.
- Any future destructive, rename, non-null-without-default, or contract-style migration must be split into an expand/backfill/contract release and must not be silently added to this deploy pattern.

Local disposable migration/seed validation passed:

- Head: `20260815_0009`
- Counts: 5 destinations, 10 books, 13 POIs, 2 itineraries, 0 usage counters.

## 8. Runtime / Dependency Reproducibility

Added explicit runtime pins:

- Backend Render Python pin: `backend/runtime.txt` with `python-3.14.0`.
- CI Python version: `3.14`.
- Frontend Node pin: `frontend/.nvmrc` with `22.11.0`.
- Frontend package engines: Node `22.11.0`, npm `>=10`.
- Render static frontend env includes `NODE_VERSION=22.11.0`.

Important evidence note:

- Local validation ran under Node `v24.11.0`, so `npm ci` emitted an expected `EBADENGINE` warning against the newly declared Node `22.11.0` pin.
- GitHub Actions will run Node `22.11.0`.
- Render should be verified after provisioning to confirm it honors `backend/runtime.txt` and `NODE_VERSION`.

Remaining reproducibility risk:

- Python requirements still use lower-bound ranges rather than a fully locked constraints file. The runtime/CI split reduces deployment surface, but a lock/constraints strategy remains recommended before Production GO.

## 9. Local Validation

Passed on 2026-08-21:

- `venv\Scripts\python.exe scripts\ci\validate_workflows.py`
- `venv\Scripts\python.exe scripts\ci\secret_hygiene.py`
- `venv\Scripts\python.exe scripts\ci\secret_hygiene.py --history`
- `npm.cmd ci` from `frontend/` with expected local Node engine warning.
- `npm.cmd audit --omit=dev --audit-level=high`
- `npm.cmd audit --json`
- `venv\Scripts\python.exe scripts\ci\frontend_audit_policy.py tests\.artifacts\frontend-audit.json`
- `npm.cmd run typecheck`
- `npm.cmd test`: 15 files, 75 tests passed.
- `npm.cmd run build`
- `venv\Scripts\python.exe scripts\ci\migration_seed_check.py`
- `..\venv\Scripts\python.exe ..\scripts\ci\validate_config_profiles.py` from `backend/`: `errors: []`.
- `venv\Scripts\python.exe -m pip_audit -r backend\requirements-runtime.txt --strict`
- `venv\Scripts\python.exe -m pip_audit -r backend\requirements-ci.txt --strict`
- `venv\Scripts\python.exe -m pytest -q --basetemp=tests\.artifacts\tmp\pytest-plu-04-closeout-backend`: 351 passed, 3 skipped.
- `powershell.exe -ExecutionPolicy Bypass -File scripts\cloud_offline_render_preflight.ps1`
- `git diff --check`: no whitespace errors; line-ending warnings only.

## 10. Git / Remote State

At closeout before commit/push:

- Local branch: `main`
- Local HEAD: `8263cf1bca8a3125a039bb0388325b03cd4ec9ee`
- Remote `origin/main`: `86a40dc90ff7dcfd4497ef1da190dc2da35e73ca`
- Local branch has two prior commits not on remote before PLU-04.
- PLU-04 work is intended for a feature branch, not direct `main` push.

Required Git closeout action:

- Create a feature branch such as `plu-04-github-actions-cicd`.
- Commit only PLU-04 files.
- Push only the feature branch.
- Do not merge to `main`.
- Do not force-push.
- Do not push production deployment changes directly to `main`.

## 11. GitHub Actions Results

Remote GitHub Actions results are pending.

Expected after feature-branch push:

- CI should trigger for `plu-04-*` branch pushes.
- Deployment workflows should not deploy from the feature branch because staging `workflow_run` is restricted to `main`, and production is manual dispatch only.
- GitHub Dependency Review will run only in pull request context.

## 12. GitHub Owner Actions

Owner/admin actions required before PLU-04 can be marked complete:

- Enable/confirm GitHub Actions.
- Open a PR from the PLU-04 feature branch to `main`.
- Require CI status checks before merge.
- Protect `main` or configure an equivalent ruleset.
- Disable force-pushes and deletion on `main`.
- Configure `staging` and `production` GitHub Environments.
- Add production required reviewers.
- Add environment secrets and variables:
  - `STAGING_DATABASE_URL`
  - `RENDER_STAGING_DEPLOY_HOOK_URL`
  - `STAGING_BACKEND_BASE_URL`
  - `PRODUCTION_DATABASE_URL`
  - `RENDER_PRODUCTION_DEPLOY_HOOK_URL`
  - `PRODUCTION_BACKEND_BASE_URL`
- Enable GitHub secret scanning/push protection where available.
- Enable dependency graph and dependency review where available.
- Consider CodeQL/code scanning as launch hardening if available for the repository/account.

## 13. Remaining Production-GO Blockers

Production remains NO-GO.

Open blockers:

- PLU-04 remote workflow execution and GitHub protections are not yet proven.
- Real Auth0 staging/production resources are still unprovisioned.
- Real Render backend/frontend/PostgreSQL resources are still unprovisioned.
- Managed DB backup/restore/rollback evidence is missing.
- Observability, uptime checks, retained logs, error reporting, alert ownership, and usage cleanup are missing.
- Production-like staging E2E is missing.
- Persistence integrity issue for missing POI references remains open.
- Python dependency locking/constraints remain launch-hardening work.

## 14. Next Recommended Unit

Remain in PLU-04 closeout until the feature branch is pushed, GitHub Actions results are observed, and the owner/admin repository settings are verified.
