# Litinerary Stage 1 S1-02 Managed Auth Report

Date: 2026-08-15

## Executive Summary

S1-02 is complete. Deployed environments now have an enforceable managed
JWT/OIDC authentication boundary. `internal`, `beta`, `staging`, and
`production` fail startup unless auth is enabled, dev auth/fallback is disabled,
managed JWT validation settings are present, and managed-auth metadata calls are
allowed for the deployed environment.

Local development and standard tests retain the existing dev-token workflow.
Public catalog and itinerary endpoints remain intentionally anonymous.
User-owned and subscriber endpoints remain backend-authorized.

## Starting State

The repository already contained a backend JWT/JWKS validation foundation,
`/api/me` user synchronization, dev bearer-token support, and Stage 1 route
fail-closed work for user-owned endpoints. It did not yet enforce complete
managed-auth configuration for every deployed environment at startup.

Required context reviewed before implementation:

- `docs/stage-0-stage-1-full-closeout-report.md`
- `docs/production-development-progress.md`
- `docs/re-onboarding-production-readiness-review.md`

Current branch/status were inspected before and after the work. Current commit
at inspection time was `86a40dc90ff7dcfd4497ef1da190dc2da35e73ca`. Existing
Stage 0 artifact-hygiene changes and untracked reports were preserved.

## Authentication Architecture Before Changes

Before S1-02, the backend had these pieces:

- `backend/app/core/auth.py` supported optional dev tokens and managed JWT
  validation through issuer, audience, algorithms, JWKS URL, or provider
  metadata URL.
- `/api/me` mapped a verified `CurrentUser` into the local `UserModel` through
  `sync_user_from_current_user()`.
- `frontend/src/services/apiClient.ts` could send an `Authorization: Bearer`
  header when a session token existed.
- `frontend/src/services/authService.ts` and `frontend/src/stores/authStore.ts`
  had in-memory session handling and dev-login support.
- No concrete frontend managed-auth SDK or provider-specific login callback was
  present.

The gap was startup enforcement: deployed profiles could still be configured in
ways that contradicted production auth expectations.

## Provider Decision

Provider-neutral contract retained because no specific managed-auth provider is
established in the repository.

Evidence:

- No provider-specific frontend SDK dependency is present.
- Existing backend code and docs already use generic JWT/JWKS settings.
- Environment examples use provider labels/placeholders rather than a vendor
  tenant.

I did not arbitrarily choose Auth0, Clerk, Firebase, Cognito, Supabase Auth, or
another vendor. That decision remains operational/product work.

## Environment Authentication Matrix

| Environment | Auth behavior | Dev tokens allowed? | Managed JWT configuration required? | Startup behavior if incomplete |
| --- | --- | ---: | ---: | --- |
| `development` | Auth optional by default; dev provider supported for local work. | Yes, only for local/dev-provider paths. | No, unless a non-dev provider is selected. | Passes with local defaults. |
| `test` | Auth optional by default; deterministic mock/offline testing. | Yes, only for explicit test/dev-provider paths. | No, unless a managed-auth test config is selected. | Passes with test/dev defaults. |
| `internal` | Managed auth required. | No. | Yes. | Fails fast with missing variable names. |
| `beta` | Managed auth required. | No. | Yes. | Fails fast with missing variable names. |
| `staging` | Managed auth required. | No. | Yes. | Fails fast with missing variable names. |
| `production` | Managed auth required. | No. | Yes. | Fails fast with missing variable names. |

Required deployed settings:

- `ENABLE_AUTH=true`
- `AUTH_PROVIDER` set to a managed provider label, not `dev`
- `AUTH_REQUIRED_FOR_USER_FEATURES=true`
- `AUTH_ALLOW_DEV_USER_FALLBACK=false`
- `AUTH_JWT_ISSUER`
- `AUTH_JWT_AUDIENCE`
- `AUTH_JWT_ALGORITHMS`, using production algorithms such as `RS256`
- `AUTH_JWKS_URL` or `AUTH_PROVIDER_METADATA_URL`
- `ALLOW_EXTERNAL_CALLS=true`
- `EXTERNAL_CALL_ALLOWED_ENVIRONMENTS` includes the active deployed `APP_ENV`

## Implementation

- Added `Settings.deployed_auth_validation_errors()`.
- Changed `validate_auth_startup()` to reject incomplete deployed auth for
  `internal`, `beta`, `staging`, and `production`.
- Kept development/test dev-provider startup behavior intact.
- Kept public catalog and itinerary endpoints anonymous.
- Verified `/api/me` anonymous, managed-token, repeated-sync, malformed-token,
  invalid-token, and deployed behavior.
- Preserved owner/admin checks and deployed fail-closed behavior even when
  `AUTH_REQUIRED_FOR_USER_FEATURES=false`.
- Made readiness provider entries provider-scoped for `externalCallsAllowed`.
- Updated beta/deployment readiness scripts to use placeholder managed auth for
  deployed profiles while leaving product providers fake/mock.
- Updated env templates and authentication/deployment docs.
- Updated `docs/production-development-progress.md`.

## Files Changed

Primary S1-02 files:

- `backend/app/core/config.py`
- `backend/app/core/auth.py`
- `backend/app/core/readiness.py`
- `backend/scripts/validate_beta_config.py`
- `backend/tests/test_auth_foundation.py`
- `scripts/deployment_readiness_check.ps1`
- `scripts/beta_dry_run.ps1`
- `.env.example`
- `.env.test.example`
- `.env.beta.example`
- `.env.production.example`
- `frontend/.env.beta.example`
- `frontend/.env.production.example`
- `README.md`
- `backend/README.md`
- `docs/api-contract.md`
- `docs/production-readiness.md`
- `docs/beta-deployment-runbook.md`
- `docs/deployment-readiness-harness.md`
- `docs/cloud-target-readiness-checklist.md`
- `docs/production-development-progress.md`

Pre-existing Stage 0/progress files remain untracked in this workspace and were
not overwritten.

## Security Properties Now Enforced

- Deployed environments cannot start with auth disabled.
- Deployed environments cannot use `AUTH_PROVIDER=dev`.
- Deployed environments cannot allow dev-user fallback.
- Deployed environments require user-feature auth.
- Deployed environments require managed JWT issuer, audience, algorithms, and
  JWKS/provider metadata.
- Deployed environments require managed-auth metadata external-call allowance.
- `dev:` tokens are rejected in production managed-auth configuration.
- Anonymous user-owned access is denied.
- Malformed, invalid issuer, invalid audience, expired, and unsupported
  algorithm tokens are denied.
- Owner/admin route behavior remains enforced.
- Product providers remain fake/mock in beta/deployment dry-run profiles.

## Frontend Authentication State

Classification: backend ready, but frontend integration incomplete and provider
decision required.

The frontend can attach bearer tokens, accept a managed token into auth state,
and hydrate `/api/me`. It does not yet have a production provider SDK, hosted
login/callback flow, persistent refresh/session handling, or production logout
integration. This should not be claimed as production-complete authentication
until a provider is selected and integrated.

## Validation Commands and Exact Outcomes

| Command | Outcome |
| --- | --- |
| `.\venv\Scripts\python.exe -m pytest backend\tests\test_auth_foundation.py::test_deployed_auth_startup_validation_fails_when_config_incomplete backend\tests\test_auth_foundation.py::test_deployed_auth_startup_validation_fails_when_env_not_allowlisted backend\tests\test_auth_foundation.py::test_valid_deployed_auth_startup_validation_passes_without_network backend\tests\test_auth_foundation.py::test_development_auth_startup_allows_dev_provider backend\tests\test_auth_foundation.py::test_test_auth_startup_allows_dev_provider_without_external_services -q` | 8 passed, 1 warning |
| `.\venv\Scripts\python.exe -m pytest backend\tests\test_auth_foundation.py backend\tests\test_environment_guards.py backend\tests\test_external_call_policy.py backend\tests\test_observability.py backend\tests\test_offline_integration_readiness.py -q` | 80 passed, 3 warnings |
| `.\venv\Scripts\python.exe -m pytest -q` | 305 passed, 3 skipped, 10 warnings |
| `..\venv\Scripts\python.exe -m scripts.validate_beta_config --profile beta` with representative beta managed-auth placeholders | Passed; `errors: []`, auth configured, product guard blocked |
| `npm.cmd run typecheck` from `frontend/` | Passed |
| `npm.cmd test` from `frontend/` | 13 files passed, 65 tests passed |
| `npm.cmd run build` from `frontend/` | Passed; `vue-tsc --noEmit && vite build` completed |
| Temporary backend startup with safe local config | `/api/health=ok`, `/api/readiness=ready`, `APP_ENV=development`, `externalCalls=false` |
| `git diff --check` | Passed; Git emitted line-ending warnings only |
| `git status --short --branch` | Reviewed; branch `main...origin/main`, expected modified/untracked files present |

Warnings observed:

- FastAPI/Starlette TestClient `httpx` deprecation.
- `HTTP_413_REQUEST_ENTITY_TOO_LARGE` deprecation in observability paths.

## Remaining Production Authentication Gaps

- Choose the real managed-auth provider, tenant, client IDs, callback URLs, and
  logout URLs.
- Integrate the provider-specific frontend login/session/logout flow.
- Store real deployment auth config in the target platform secret/config store.
- Run provider-specific end-to-end authentication smoke tests after the provider
  is selected.

## Newly Discovered Issues

- The beta/deployment readiness scripts had stale deployed profiles that used
  `ENABLE_AUTH=false` and `AUTH_PROVIDER=dev`. These were updated because they
  contradicted the new S1-02 deployed-auth contract.
- Readiness previously reported global external-call allowance on every provider.
  This became misleading once managed auth needed metadata calls while product
  providers stayed disabled. Readiness now reports provider-scoped external-call
  allowance.

## Production Impact

S1-02 materially improves production safety: a misconfigured deployed app now
fails at startup instead of serving protected user features with dev or
anonymous identity behavior. It does not enable public production launch by
itself because frontend provider integration and real provider selection remain.

## Next Recommended Task

S1-03: define itinerary ownership/private/public semantics before real
user-saved itineraries launch.

## Prompt Compliance Matrix

| Mandatory requirement | Status | Evidence |
| --- | --- | --- |
| 1. Read current project state | DONE | Required reports, auth docs/code, frontend session code, env templates, branch/status, and working tree inspected. |
| 2. Preserve Stage 0 decisions | DONE | No Codex-only frontend harness workaround added; auth-only script updates made. |
| 3. Reconstruct existing auth architecture | DONE | Backend auth, users, models, schemas, config, startup, `/api/me`, frontend auth/API client, tests, and search terms inspected. |
| 4. Determine managed-auth provider status | DONE | No concrete provider found; provider-neutral JWT/JWKS contract retained. |
| 5. Define production auth contract | DONE | Environment matrix and required deployed settings documented. |
| 6. Implement deployed fail-fast config | DONE | `Settings.deployed_auth_validation_errors()` and `validate_auth_startup()` enforce deployed config. |
| 7. Preserve explicit public functionality | DONE | Public endpoints left anonymous; existing full test suite and auth tests passed. |
| 8. Verify development/test isolation | DONE | Dev/test startup and production dev-token rejection tests pass. |
| 9. Verify `/api/me` behavior | DONE | Anonymous, valid managed, repeated sync, malformed, invalid, and deployed tests added/passed. |
| 10. Verify owner/admin authorization | DONE | Owner, cross-user, admin, anonymous deployed, invalid auth, and disabled-flag deployed tests pass. |
| 11. Update environment templates | DONE | Backend/frontend beta/production examples and local/test guidance updated with placeholders only. |
| 12. Add configuration-validation tests | DONE | Development, test, internal, beta, staging, production incomplete and valid deployed cases covered. |
| 13. Add authentication-boundary tests | DONE | Managed identity, anonymous, malformed, invalid issuer/audience/algorithm, production dev-token, and ownership tests pass. |
| 14. Frontend impact analysis | DONE | Frontend classified as backend ready but provider decision/frontend integration incomplete. |
| 15. Run complete validation suite | DONE | Full backend, frontend typecheck/test/build, startup, auth config validation, git checks completed. |
| 16. Do not skip frontend validation | DONE | `npm.cmd run typecheck`, `npm.cmd test`, and `npm.cmd run build` all passed from `frontend/`. |
| 17. Update project documentation | DONE | `docs/production-development-progress.md` and contradicted auth/deployment docs updated. |
| 18. Create S1-02 session report | DONE | This file created: `docs/stage-1-s1-02-managed-auth-report.md`. |
| 19. Include Prompt Compliance Matrix | DONE | Matrix included here and mirrored in final response. |
| 20. Completion gate | DONE | S1-02 was implemented, tested, documented, and validated; not merely analyzed. |
