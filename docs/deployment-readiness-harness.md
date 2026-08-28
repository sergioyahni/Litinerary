# Deployment Readiness Harness

## Purpose

`scripts/deployment_readiness_check.ps1` is the offline/mock pre-deployment gate
for Litinerary. It validates that the repository is safe to rehearse a local
offline deployment posture before any local/cloud deployment work.

This harness does not approve staged internal live LLM testing, public/beta live
generation, production deployment, or any live non-LLM provider.

## How To Run

From the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\deployment_readiness_check.ps1
```

Full mode runs the complete backend and frontend test suites:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\deployment_readiness_check.ps1 -Full
```

The frontend build can be skipped only for a narrow local diagnostic pass:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\deployment_readiness_check.ps1 -SkipFrontendBuild
```

## Default Offline Mode

Default mode is deterministic and CI-safe. It sets its own environment before
each check:

- local/test profiles use `ALLOW_EXTERNAL_CALLS=false`
- deployed profiles use `ALLOW_EXTERNAL_CALLS=true` only for managed-auth
  JWKS/provider metadata
- `ENABLE_REAL_LLM=false`
- all non-LLM live provider flags disabled
- `ENABLE_STAGED_INTERNAL_LLM_TESTING=false`
- `ENABLE_INTERNAL_ACCESS_GATE=false`
- local/test auth provider set to local/dev mode
- deployed auth provider set to a placeholder managed OIDC/JWT provider
- deployed profiles use an explicit disposable database URL instead of the
  local SQLite fallback
- deployed profiles set `ENABLE_DURABLE_USAGE_CONTROLS=true`
- AI/vector/POI/routing/ticketing/affiliate/TTS providers set to fake/mock

It does not read or require real API keys. The managed-auth values are
non-secret placeholders used to verify deployed startup enforcement.

## Checks Covered

The default harness checks:

- high-confidence secret-like patterns across tracked and changed docs, scripts,
  backend/frontend source, README files, and environment templates
- local env files such as `.env.development.local` are ignored and untracked
- environment templates exist and keep secret-bearing fields as placeholders
- offline profile validation for `development`, `test`, `internal`, `staging`,
  and `production`
- product provider readiness stays mock/offline and fail-closed for every
  profile
- deployed auth readiness shows a configured managed auth provider instead of
  development auth
- deployed database configuration is explicit and passes startup validation
- a disposable server database is migrated to Alembic head and seeded before
  backend boot
- readiness reports database connectivity `ok` and migrations `current`
- durable usage controls are enabled for deployed profiles and disabled for
  local/test profiles
- staged/internal live LLM gates remain disabled
- Alembic can upgrade a temporary SQLite DB
- seed loading and seed validation pass
- London/Sherlock Holmes/Baker Street seed provenance remains present
- temporary backend `/api/health` and `/api/readiness` work in mock-only staging
  posture
- readiness output does not expose secrets or raw provider payload fields
- focused backend deployment tests pass
- focused frontend/API integration tests pass
- frontend typecheck passes
- frontend build passes unless explicitly skipped

Full mode additionally runs the full backend pytest suite and full frontend
Vitest suite before typecheck/build.

## Intentionally Not Checked

The harness intentionally does not:

- make live LLM requests
- call `/v1/chat/completions`
- call live vector DB, POI verification, routing, ticketing, affiliate, TTS, or
  managed auth providers
- validate real cloud infrastructure
- validate production secrets or secret-manager access
- approve staged internal live LLM testing
- approve public/beta live generation
- execute Batch 5 provider-gated tests

## Pass/Fail Criteria

The harness passes only if all default checks complete successfully. Any
high-confidence secret pattern, tracked local env file, live product-provider
readiness, missing deployed managed-auth readiness, missing deployed database
configuration, non-current migration state, disabled deployed durable usage
controls, failed seed/migration check, failed health/readiness check, failed
focused tests, typecheck failure, or build failure is a blocker.

If default mode passes, local offline deployment rehearsal is reasonable as a
next step. It remains mock-only and does not imply readiness for staged internal
or public/beta live provider usage.

## Local Offline Deployment Rehearsal

After the default harness passes, run the local offline deployment rehearsal:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\local_offline_deployment_rehearsal.ps1
```

The rehearsal runs this harness first, then starts a temporary mock-only backend
on `127.0.0.1:8765`, checks `/api/health` and `/api/readiness`, resets and
validates bundled seed data, performs one London/Sherlock Holmes/Baker Street
mock itinerary-generation request, shuts the backend down, and records sanitized
evidence in `docs/local-offline-deployment-rehearsal-record.md`.

The rehearsal does not require or read real API keys and does not approve live
provider usage.

The local offline rehearsal passed on the recorded run in
`docs/local-offline-deployment-rehearsal-record.md`. The next deployment gate is
the cloud offline deployment rehearsal described in
`docs/cloud-offline-deployment-rehearsal.md`; it remains mock-only and does not
approve local live, staged internal, or public/beta live deployment.

## Remaining Gaps

Remaining deployment-readiness work after S1-05:

- a cloud-specific deployment rehearsal
- durable log-sink redaction/retention evidence
- production-grade internal access boundary
- approved request/spend ceilings and owners
- Batch 5 optional provider-gated tests, disabled by default until separately
  approved
