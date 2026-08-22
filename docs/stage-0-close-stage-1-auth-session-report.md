# Litinerary Stage 0 Closeout and Stage 1 Auth Report

Date: 2026-08-15

## 1. Repository State

- Branch: `main`
- Commit: `86a40dc`
- Remote tracking: aligned with `origin/main` at session start.
- Working tree after changes: tracked edits in `.gitignore`, `pytest.ini`, `backend/app/core/auth.py`, `backend/app/api/routes/users.py`, `backend/tests/test_auth_foundation.py`, plus untracked report/progress docs.

## 2. S0-02 Result

S0-02 is complete.

Root cause: old generated pytest artifact directories under `tests/.artifacts/tmp` had Windows ACL/ownership state that the Codex sandbox identity could not read. Pytest also reused that same subtree for cache/temp output, so backend tests could pass while still emitting cache warnings.

Changes made:

- `.gitignore` now ignores generated `tests/.artifacts` descendants recursively.
- `pytest.ini` now writes cache/temp artifacts to `tests/.artifacts/pytest-cache` and `tests/.artifacts/pytest-tmp`.
- Old generated locked artifact directories under `tests/.artifacts/tmp` were removed after approval.

Validation: `git status --short --branch --ignored` now emits no permission-denied warnings, and backend pytest no longer emits repo-config cache warnings.

## 3. Deployment Harness Result

The harness was not changed. It is replaced inside Codex with an equivalent split validation procedure.

Finding: `scripts/deployment_readiness_check.ps1` correctly changes to `frontend/` before npm. Earlier tests showed the failure persists through multiple cwd techniques inside Codex, while the same frontend focused tests pass when the process starts with `frontend/` as its working directory.

Codex-safe equivalent:

- Run the backend/profile/migration/startup portions of the harness from repo root.
- Run frontend focused integration tests from `frontend/`.
- Run frontend typecheck/build from `frontend/` when frontend code changes.

## 4. Stage 0 Decision

Stage 0: COMPLETE.

The baseline is trustworthy: backend tests pass, frontend focused integration tests pass, prior frontend typecheck/full tests/build passed, migrations/seed/startup were verified in the Stage 0 report, health/readiness pass, and artifact hygiene no longer interferes with validation.

## 5. Stage 1 Production Backlog

| ID | Priority | Area | Finding | Production Risk | Definition of Done |
| -- | -------- | ---- | ------- | --------------- | ------------------ |
| S1-01 | P1 | Auth/user authorization | Deployed user-owned routes must fail closed. | IDOR if path user IDs are trusted. | Completed this session. |
| S1-02 | P1 | Production auth config | Managed auth foundation exists but provider/config are not production-final. | Real users cannot be safely identified. | Deployed auth config fails loudly when incomplete. |
| S1-03 | P1 | Data ownership | Itinerary ownership/private/public semantics are incomplete. | Private saved user data could be exposed later. | Ownership model and tests are explicit. |
| S1-04 | P1 | Durable usage controls | Usage limits are in-memory. | Limits reset and do not scale. | Durable metering implemented and tested. |
| S1-05 | P1 | DB correctness | Deployed DB fallback can mask missing schema/data. | App can look healthy on wrong persistence. | Deployed readiness fails loudly. |
| S1-06 | P1 | Provider gates | Live-provider rollout remains no-go. | Cost/reliability/security risk. | One provider has staged rollout, budget, rollback, monitoring. |
| S1-07 | P2 | Observability | No external metrics/alerts/retention. | Incidents are hard to detect. | Monitoring and alerting wired. |
| S1-08 | P2 | Persistence integrity | Missing POI stops can be dropped silently. | Itinerary data loss. | Explicit validation/error behavior. |
| S1-09 | P2 | CI/CD | No checked-in workflow found. | Manual gates only. | CI runs backend/frontend gates. |

## 6. Stage 1 Task Selected

Selected task: fail closed for deployed user-owned routes.

Why first: it removes a verified production security risk without waiting on a final auth provider choice.

Current behavior: if `AUTH_REQUIRED_FOR_USER_FEATURES=false`, user routes could be public.

Required behavior: in deployed environments (`internal`, `beta`, `staging`, `production`), user-owned routes require a current authenticated user and owner/admin authorization.

## 7. Changes Made

- `backend/app/core/auth.py`: added `user_features_require_auth()` and used it in user-feature authorization.
- `backend/app/api/routes/users.py`: user profile creation now uses the same deployed fail-closed predicate.
- `backend/tests/test_auth_foundation.py`: added deployed-env negative tests for disabled auth flags.
- `pytest.ini`: moved pytest cache/temp artifacts out of the locked `tests/.artifacts/tmp` subtree.
- `.gitignore`: made `tests/.artifacts` generated-output ignoring recursive.
- `docs/production-development-progress.md`: updated Stage 0/Stage 1 status and backlog.

## 8. Tests and Validation

| Command | Result |
|---|---|
| `git status --short --branch --ignored` | Passed; no permission-denied warnings. |
| `python -m pytest backend\tests\test_auth_foundation.py -q` | Passed; 19 passed. |
| `python -m pytest backend\tests\test_database_seed.py -q` | Passed; 3 passed. |
| `python -m pytest -q` | Passed; 291 passed, 3 skipped. |
| `npm.cmd test -- src/test/frontendApiIntegration.test.ts src/services/apiContract.integration.test.ts` | Passed; 2 files, 9 tests. |
| Temporary backend startup and `/api/health`, `/api/readiness` | Passed; `health=ok readiness=ready`. |

## 9. Security/Production Impact

The project no longer depends only on `AUTH_REQUIRED_FOR_USER_FEATURES` to protect user-owned routes in deployed environments. A permissive deployed flag combination now returns 401 instead of exposing user profile/bookmark/preference/review data through path parameters.

## 10. Remaining Production Blockers

- P1: Production managed-auth provider/config selection and startup enforcement.
- P1: Itinerary ownership/private/public data model.
- P1: Durable usage/rate/cost controls.
- P1: Deployed DB fail-fast readiness.
- P1: Live-provider rollout gate with monitoring and rollback.

## 11. Next Recommended Task

S1-02: define and enforce production managed-auth configuration.
