# PLU-04 GitHub Actions CI/CD Closeout Report

Date: 2026-08-21

Repository: `C:\Users\syahn\source\litinerary`

PLU-04 STATUS: CODE COMPLETE - OWNER ACTIVATION REQUIRED

## 1. Verdict

PLU-04 code is implemented, committed, pushed to a feature branch, and validated by a real GitHub Actions branch run at the current branch head. It is code-complete, but owner/admin activation remains required because no pull request exists, Dependency Review has not run in PR context, and `main` has no branch protection or required checks.

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
- `backend/tests/test_live_llm_preflight.py`
- `frontend/.nvmrc`
- `frontend/package.json`
- `frontend/package-lock.json`
- `render.yaml`
- `docs/plu-04-github-actions-cicd-report.md`
- `docs/production-development-progress.md`
- `docs/production-launch-plan.md`

Commits pushed to `origin/plu-04-github-actions-cicd`:

- `77e859c92064582b05f8b7af5a3ec8906ed6a64c` - `Add PLU-04 GitHub Actions CI/CD gates`
- `c0fed4fd63b26c24b4d38e15e615af31f90d221a` - `Fix PowerShell preflight tests on CI runners`
- `3f00857c5a1e6f5a0864281545b801574e09f5d4` - `Update PLU-04 closeout evidence`

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
- `venv\Scripts\python.exe -m pytest backend\tests\test_live_llm_preflight.py -q --basetemp=tests\.artifacts\tmp\pytest-plu-04-live-llm-preflight`: 5 passed.
- `venv\Scripts\python.exe -m pytest -q --basetemp=tests\.artifacts\tmp\pytest-plu-04-closeout-backend-after-ci-fix`: 351 passed, 3 skipped.
- Fresh local CI-repro venv using `backend/requirements-ci.txt`: 351 passed, 3 skipped.
- `powershell.exe -ExecutionPolicy Bypass -File scripts\cloud_offline_render_preflight.ps1`
- `git diff --check`: no whitespace errors; line-ending warnings only.

## 10. Git / Remote State

At closeout after push:

- Local branch: `plu-04-github-actions-cicd`
- Local HEAD / remote branch HEAD: `3f00857c5a1e6f5a0864281545b801574e09f5d4`
- Remote `origin/main`: `86a40dc90ff7dcfd4497ef1da190dc2da35e73ca`
- The feature branch contains the two prior local commits plus the PLU-04 commits.
- `main` was not pushed.

Remote branch:

- `origin/plu-04-github-actions-cicd`
- PR URL offered by GitHub: `https://github.com/sergioyahni/Litinerary/pull/new/plu-04-github-actions-cicd`

Cumulative commits proposed by the branch:

- `e9fc587 Complete production foundation through PLU-01`
- `8263cf1 Add Auth0 integration and Render staging foundation`
- `77e859c Add PLU-04 GitHub Actions CI/CD gates`
- `c0fed4f Fix PowerShell preflight tests on CI runners`
- `3f00857 Update PLU-04 closeout evidence`

## 10a. Cumulative Diff Audit

The cumulative proposed merge from `origin/main` to `origin/plu-04-github-actions-cicd` is intentional and semantically coherent.

Earlier commits predate PLU-04:

- `e9fc587` belongs to PLU-01 and Stage 1 production foundation work: production decisions, durable usage controls, ownership/security, database readiness, environment templates, migration/test/report foundations.
- `8263cf1` belongs to PLU-02/PLU-03 local production-hardening: Auth0 frontend/session integration, Render blueprint/staging foundation, provider-disablement regression, and associated docs/tests.

Those earlier commits are intentionally part of this cumulative production-hardening branch because PLU-04 validates the repository state produced by those foundations: Auth0 config posture, Render config, migrations, seed/readiness checks, dependency manifests, and test suites. PLU-04 depends on them for meaningful CI coverage.

Audit results:

- `git diff --stat origin/main...origin/plu-04-github-actions-cicd`: 118 files, 11,738 insertions, 1,634 deletions.
- No generated database, SQLite, log, PID, temp, `node_modules`, `dist`, or build artifacts are present in the cumulative diff.
- Filename review flagged only placeholder env templates and `scripts/ci/secret_hygiene.py`.
- Current-tree and reachable-history secret scans passed.
- No unrelated, accidental, credential-bearing, local-only debug, generated, or temporary content was found.

## 10b. Pull Request State

No pull request exists from `sergioyahni:plu-04-github-actions-cicd` to `main`.

Attempted supported draft PR creation through the authenticated GitHub connector failed:

- Result: `403 Resource not accessible by integration`

OWNER ACTION REQUIRED - open draft PR from `plu-04-github-actions-cicd` to `main`.

Compare/PR URL:

- `https://github.com/sergioyahni/Litinerary/pull/new/plu-04-github-actions-cicd`

## 11. GitHub Actions Results

Remote GitHub Actions results:

- First branch run: `32502699119`, commit `77e859c92064582b05f8b7af5a3ec8906ed6a64c`, conclusion `failure`.
  - Failed job: `Backend pytest`.
  - API log download was blocked with `403 Must have admin rights to Repository`; check-run annotations only exposed `Process completed with exit code 1`.
  - Likely cause was a Windows-only `powershell.exe` assumption in `backend/tests/test_live_llm_preflight.py`.
- Follow-up fix: `c0fed4fd63b26c24b4d38e15e615af31f90d221a` made PowerShell test helpers use `powershell.exe` on Windows and `pwsh` on non-Windows runners.
- Second branch run: `32504034854`, commit `c0fed4fd63b26c24b4d38e15e615af31f90d221a`, conclusion `success`.
- Current-head branch run: `32504478112`, commit `3f00857c5a1e6f5a0864281545b801574e09f5d4`, conclusion `success`.
- Current-head successful run URL: `https://github.com/sergioyahni/Litinerary/actions/runs/32504478112`

Successful jobs:

- `Workflow policy`
- `Secret hygiene`
- `Backend pytest`
- `Migration and seed`
- `Config profile validation`
- `Render offline preflight`
- `Frontend typecheck, tests, build`
- `Dependency security`

Skipped as expected on branch push:

- `GitHub dependency review`, because it is intentionally gated to `pull_request` events.

PR-context CI:

- Not available because no PR exists.
- Dependency Review status: `SKIPPED` on branch push; must run after owner opens the draft PR.

Job-level evidence for current-head branch run `32504478112`:

| Check/job | Status | Conclusion | Head SHA | URL |
|---|---|---|---|---|
| Workflow policy | completed | success | `3f00857c5a1e6f5a0864281545b801574e09f5d4` | `https://github.com/sergioyahni/Litinerary/actions/runs/32504478112/job/96841441416` |
| Secret hygiene | completed | success | `3f00857c5a1e6f5a0864281545b801574e09f5d4` | `https://github.com/sergioyahni/Litinerary/actions/runs/32504478112/job/96841441576` |
| Backend pytest | completed | success | `3f00857c5a1e6f5a0864281545b801574e09f5d4` | `https://github.com/sergioyahni/Litinerary/actions/runs/32504478112/job/96841441579` |
| Migration and seed | completed | success | `3f00857c5a1e6f5a0864281545b801574e09f5d4` | `https://github.com/sergioyahni/Litinerary/actions/runs/32504478112/job/96841441756` |
| Config profile validation | completed | success | `3f00857c5a1e6f5a0864281545b801574e09f5d4` | `https://github.com/sergioyahni/Litinerary/actions/runs/32504478112/job/96841441702` |
| Render offline preflight | completed | success | `3f00857c5a1e6f5a0864281545b801574e09f5d4` | `https://github.com/sergioyahni/Litinerary/actions/runs/32504478112/job/96841441700` |
| Frontend typecheck, tests, build | completed | success | `3f00857c5a1e6f5a0864281545b801574e09f5d4` | `https://github.com/sergioyahni/Litinerary/actions/runs/32504478112/job/96841441566` |
| Dependency security | completed | success | `3f00857c5a1e6f5a0864281545b801574e09f5d4` | `https://github.com/sergioyahni/Litinerary/actions/runs/32504478112/job/96841441508` |
| GitHub dependency review | completed | skipped | `3f00857c5a1e6f5a0864281545b801574e09f5d4` | `https://github.com/sergioyahni/Litinerary/actions/runs/32504478112/job/96841442602` |

## 12. GitHub Owner Actions

Owner/admin action matrix:

| Area | State | Evidence / required action |
|---|---|---|
| GitHub Actions | VERIFIED | Hosted Actions runs exist and current-head CI run `32504478112` passed. |
| Pull request existence | OWNER ACTION REQUIRED | No PR exists. Connector PR creation failed with `403 Resource not accessible by integration`. Open draft PR from `plu-04-github-actions-cicd` to `main`. |
| PR-context CI | OWNER ACTION REQUIRED | No PR exists; run all required checks after draft PR is opened. |
| Dependency Review | OWNER ACTION REQUIRED | Branch-push job skipped as designed. Must run in PR context. |
| Dependency graph / Dependabot alerts | OWNER ACTION REQUIRED | Public API check returned `401 Requires authentication`; owner must verify dependency graph/alerts are enabled where available. |
| `main` branch protection/ruleset | NOT CONFIGURED | Public branch API reports `protected: false`. |
| Required status checks | NOT CONFIGURED | Public branch API reports required checks enforcement `off` with empty checks/contexts. |
| Staging Environment | NOT CONFIGURED | Public environments API returned `total_count: 0`. |
| Production Environment | NOT CONFIGURED | Public environments API returned `total_count: 0`. |
| Production required reviewer | NOT CONFIGURED | No production environment exists. |
| Environment-scoped secrets | OWNER ACTION REQUIRED | Configure only after environments exist; values must remain out of source control. |
| Secret-scanning alert review | OWNER ACTION REQUIRED | API requires authentication; owner must verify alert review. |
| Push protection | OWNER ACTION REQUIRED | Not publicly determinable; owner must enable/verify where available. |
| CodeQL/code scanning posture | OWNER ACTION REQUIRED | API requires authentication; CodeQL is launch hardening, not a new PLU-04 blocker unless owner policy requires it. |

Required target `main` policy:

- Pull request required before merge.
- Required CI checks enabled using the observed check names:
  - `Workflow policy`
  - `Secret hygiene`
  - `Backend pytest`
  - `Migration and seed`
  - `Config profile validation`
  - `Render offline preflight`
  - `Frontend typecheck, tests, build`
  - `Dependency security`
  - `GitHub dependency review`
- Force-push disabled.
- Branch deletion disabled.
- Stale approval handling documented if configured.
- Administrator bypass posture explicitly recorded.

## 13. Remaining Production-GO Blockers

Production remains NO-GO.

Open blockers:

- PLU-04 branch CI is proven green at current head, but no PR exists, PR dependency review has not run, and GitHub branch/environment/security protections are not yet configured.
- Real Auth0 staging/production resources are still unprovisioned.
- Real Render backend/frontend/PostgreSQL resources are still unprovisioned.
- Managed DB backup/restore/rollback evidence is missing.
- Observability, uptime checks, retained logs, error reporting, alert ownership, and usage cleanup are missing.
- Production-like staging E2E is missing.
- Persistence integrity issue for missing POI references remains open.
- Python dependency locking/constraints remain launch-hardening work.

## 14. Next Recommended Unit

Remain in PLU-04 closeout until a PR is opened, dependency review runs in PR context, and the owner/admin repository settings are verified.
