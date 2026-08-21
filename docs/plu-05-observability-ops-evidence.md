# PLU-05 Observability And Operations Evidence

## Scope

PLU-05 completed the repository-owned observability, alerting, incident ownership, and stale usage-counter cleanup unit. No production deployment, external monitoring SaaS, PR merge, or PLU-06/07/08 work was performed.

## Existing Foundation Retained

The existing backend observability foundation was preserved:

- Structured JSON log events through `app.core.observability.log_event`.
- `X-Request-ID` request correlation.
- API request started/completed/failed events.
- Provider telemetry events with provider type/name, operation, success, latency, estimated cost, warning count, and error classification.
- Readiness telemetry through `readiness_checked`.
- Usage-policy events for allowed and blocked rate/cost guard decisions.
- Sensitive-key redaction for token, secret, password, authorization, prompt, raw, text, JWT, credential, and API-key fields.

## Changes Made

- Added `app_env` to structured log events so production log pipelines can filter by environment without parsing deployment metadata.
- Added failure `status_code` and `success=false` fields to API exception telemetry and provider error telemetry.
- Added explicit usage-counter cleanup completion/failure events.
- Added `backend/scripts/cleanup_usage_counters.py` as an explicit maintenance command.
- Added deterministic tests for the synthetic incident signal and usage cleanup command behavior.
- Added `docs/production-alerting.md`.
- Added `docs/production-operations-runbook.md`.

## Telemetry Contract Covered

The application now exposes or preserves operational evidence for:

- application liveness through `/api/health`;
- environment and dependency readiness through `/api/readiness`;
- request correlation through `request_id` and `X-Request-ID`;
- HTTP 5xx failures through `api_request_failed`;
- request latency through `api_request_completed.latency_ms`;
- provider availability/failure through `provider_call_succeeded` and `provider_call_failed`;
- provider estimated cost through `estimated_cost_usd`;
- usage and rate-limit blocks through `rate_limit_blocked`;
- limiter failures through `usage_limiter_failed`;
- cleanup completion/failure through `usage_counter_cleanup_completed` and `usage_counter_cleanup_failed`;
- itinerary-generation and provider-operation failures through existing provider and API events.

## Redaction Evidence

Existing tests continue to prove structured log redaction for top-level and nested sensitive fields. PLU-05 added a synthetic API exception test that verifies request correlation and confirms a sentinel token inside an exception message is not emitted into structured log output.

Readiness tests continue to prove provider credentials are exposed only as booleans and secret values are not returned.

## Alert Policy Summary

`docs/production-alerting.md` defines alerts for:

- availability: repeated `/api/health` failures;
- readiness: unhealthy readiness beyond a short transient period;
- server errors: sustained or repeated HTTP 5xx;
- latency: initial 2000 ms general API threshold and 10000 ms itinerary-generation threshold;
- provider failures: sustained failures, with user-caused bad input separated from infrastructure incidents;
- usage limiter and cleanup failures;
- cost/budget signals based on estimated provider cost and configured ceilings.

External alert delivery is intentionally deferred.

## Incident Ownership

`docs/production-operations-runbook.md` defines:

- Primary production incident owner: repository/application owner.
- Current responsible owner: `sergioyahni`.
- Severity model:
  - SEV-1: service unavailable, major data/security risk, or production cost controls failing open.
  - SEV-2: major degraded functionality, critical provider unavailable, readiness unhealthy, or durable limiter unavailable.
  - SEV-3: limited degradation or non-critical operational issue.

The runbook documents confirmation steps, logs/request IDs to inspect, dependency checks, safe first response, escalation criteria, rollback handoff to PLU-06, and evidence to preserve.

## Synthetic Incident Drill

Deterministic test evidence:

- `test_api_exception_produces_correlated_failure_event` injects a test-only FastAPI route that raises a synthetic exception.
- The response is a 500.
- The structured `api_request_failed` event contains `request_id=req-incident-drill`, `status_code=500`, `success=false`, and `error_type=RuntimeError`.
- The sentinel secret in the exception message is not present in structured log output.

This demonstrates: signal -> structured evidence -> documented operator action.

## Usage Cleanup

Command:

```powershell
cd backend
python -m scripts.cleanup_usage_counters
```

Behavior:

- Uses the configured database.
- Deletes rows from `usage_limit_counters` only when `window_end` is older than `now - USAGE_COUNTER_RETENTION_DAYS`.
- Preserves active/current counters.
- Is idempotent.
- Reports `rowsRemoved`.
- Logs `usage_counter_cleanup_completed` on success.
- Logs `usage_counter_cleanup_failed` and exits non-zero on failure.
- Does not expose database URLs or secrets.
- Does not run implicitly on application startup.

Disposable verification:

- First cleanup pass removed 1 expired row.
- Second cleanup pass removed 0 rows.
- Active usage counter remained.
- Unrelated `destinations` row remained.
- Failure path raised and logged `SQLAlchemyError` without leaking the sentinel secret.

## Commands Executed

```powershell
git status --short
git branch --show-current
git fetch origin
git rev-parse origin/plu-04-github-actions-cicd
git rev-parse HEAD
git switch -c plu-05-observability-ops
venv\Scripts\python.exe -m pytest backend\tests\test_observability.py backend\tests\test_usage_cleanup_command.py -q
venv\Scripts\python.exe -m py_compile backend\app\core\observability.py backend\app\main.py backend\app\services\usage_policy.py backend\scripts\cleanup_usage_counters.py backend\tests\test_observability.py backend\tests\test_usage_cleanup_command.py
cd backend
..\venv\Scripts\python.exe -m scripts.cleanup_usage_counters --help
$env:PYTHONPATH='.'; ..\venv\Scripts\python.exe ..\scripts\ci\validate_config_profiles.py
cd ..
venv\Scripts\python.exe -m pytest backend\tests -q
```

Results:

- Focused observability/cleanup tests: 14 passed, 7 warnings.
- Python compile check: passed.
- Cleanup command help/import check: passed.
- Config profile validation: passed with `errors: []`.
- Full backend suite: 355 passed, 3 skipped, 114 warnings.

## External Monitoring And Deployment Deferred

The following are intentionally deferred because real staging/production infrastructure is not provisioned in PLU-05:

- Render log routing and dashboard setup.
- External alert delivery through email, Slack, PagerDuty, or another service.
- Hosted uptime checks.
- Real provider billing reconciliation.
- Production log retention policy enforcement in a hosted platform.

## Production-GO Blockers Carried Forward

- Auth0 staging/production provisioning.
- Render backend/frontend/PostgreSQL provisioning.
- PLU-06 data integrity, backup/restore, and rollback.
- PLU-07 real staging integration/deployment.
- Final PLU-08 GO/NO-GO.
- Python dependency locking/constraints if still unresolved.
