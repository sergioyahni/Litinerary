# Live LLM Operational Controls

## Purpose

This document defines the minimum operational controls required before
Litinerary can move beyond controlled local smoke tests toward staged internal
live LLM testing.

It does not approve staged internal testing, beta testing, public testing, or production live LLM itinerary generation.

## Current Scope

Allowed now:

- Offline local/demo mode.
- Controlled non-production live LLM smoke tests after the smoke preflight reports `liveLlmSmokeReady=True`.
- Review of sanitized smoke-test evidence and operational readiness artifacts.

Not allowed now:

- Staged internal user-facing live LLM itinerary generation.
- Public or beta live LLM itinerary generation.
- Live vector DB, POI, routing, ticketing, affiliate, TTS, or managed-auth provider behavior unless separately approved by existing gates.

Current smoke evidence status:

- Successful controlled smoke tests with sanitized in-repo evidence: `3 of 3`.
- Generated-itinerary quality reviews: `3 of 3`.
- Smoke evidence threshold: complete.
- Staged internal testing: still no-go until a separate go/no-go review closes the operational blockers.
- Public/beta live LLM generation: no-go.

## Environment Modes

- `APP_ENV=development`: local development and controlled live LLM smoke testing when all smoke gates are explicitly set.
- `APP_ENV=test`: standard tests. Live calls remain blocked unless an explicit integration-test profile is created.
- `APP_ENV=internal`: reserved staged-internal label. Live LLM calls also require `ENABLE_STAGED_INTERNAL_LLM_TESTING=true` and `ENABLE_INTERNAL_ACCESS_GATE=true`, plus the normal live LLM and external-call gates. These flags are not approval by themselves.
- `APP_ENV=beta` or `APP_ENV=staging`: mock-only templates for now. Public/beta live LLM traffic is not approved.
- `APP_ENV=production`: production template remains live-LLM off by default and is no-go for live LLM generation.

## Required Metrics

Before staged internal testing, the environment must provide a way to review:

- Live LLM request count.
- Live LLM success and failure count.
- Provider error type count.
- Provider latency, including p50, p95, and maximum latency.
- Estimated token usage when available.
- Estimated or provider-reported cost when available.
- Number of blocked requests by gate or usage policy.
- Unexpected live-provider enablement for non-LLM providers.
- Rollback execution and readiness confirmation.

Current code provides structured logs and local in-memory usage telemetry. These
are sufficient for smoke evidence, not durable staged monitoring. Before staged
internal testing, the team must define either durable usage/cost storage and
dashboards or an explicitly approved equivalent operational control for the
limited staged window.

## Non-Secret Configuration Placeholders

Use environment or deployment configuration, not source-controlled secrets:

```text
ENABLE_STAGED_INTERNAL_LLM_TESTING=false
ENABLE_INTERNAL_ACCESS_GATE=false
ITINERARY_GENERATION_MAX_DAYS=7
LLM_MAX_INPUT_CHARS=12000
LLM_MAX_OUTPUT_TOKENS=1200
LLM_MAX_LIVE_CALLS_PER_REQUEST=4
LLM_DAILY_LIVE_REQUEST_CEILING=4
LLM_DAILY_ESTIMATED_SPEND_CEILING_USD=0
LLM_LATENCY_ALERT_THRESHOLD_MS=5000
LLM_ERROR_RATE_ALERT_THRESHOLD_PERCENT=10
PROVIDER_DAILY_COST_CEILING_USD=0
```

`LLM_DAILY_LIVE_REQUEST_CEILING` and `LLM_MAX_LIVE_CALLS_PER_REQUEST` are wired to local in-memory usage guards. They are useful as smoke-test controls but are not durable distributed rate limits. Future staged internal testing must record approved exact request ceilings and an accountable monitoring owner before any live tester traffic is allowed.

`LLM_DAILY_ESTIMATED_SPEND_CEILING_USD` and `PROVIDER_DAILY_COST_CEILING_USD` are operational placeholders until provider spend accounting is connected to a durable store and reviewed. A staged internal go-with-gates decision requires an approved spend ceiling, an owner, and a stop condition for any spend above the approved amount.

## Proposed Internal Staged Ceilings

These values are proposed, not approved. They are intentionally conservative and
do not authorize staged internal testing.

| Control | Proposed value | Status |
| --- | --- | --- |
| Max live LLM requests per test session | 3 itinerary-generation requests | Proposed, not approved |
| Max live LLM requests per day | 6 itinerary-generation requests | Proposed, not approved |
| Max live LLM completion calls per request | 4 completion calls | Existing local guard value; staged use still pending approval |
| Max estimated daily spend | USD 1.00 | Proposed, not approved; requires durable tracking or approved equivalent |
| Max total spend for first staged window | USD 5.00 | Proposed, not approved |
| Max itinerary duration | 1 day for first staged window | Proposed, not approved |
| Retry policy | 0 automatic retries | Proposed, not approved |

Suggested environment values for a future approved staged window:

```text
LLM_MAX_LIVE_CALLS_PER_REQUEST=4
LLM_DAILY_LIVE_REQUEST_CEILING=6
LLM_DAILY_ESTIMATED_SPEND_CEILING_USD=1
PROVIDER_DAILY_COST_CEILING_USD=1
LLM_MAX_RETRIES=0
ITINERARY_GENERATION_MAX_DAYS=1
```

These values must remain unset or mock-safe until a later go-with-gates decision
explicitly approves the staged environment.

## Alert Thresholds

Placeholder thresholds for staged-readiness planning:

- Cost anomaly: any non-zero spend outside an approved smoke window, or spend above the approved daily ceiling.
- Latency: provider latency above `LLM_LATENCY_ALERT_THRESHOLD_MS`.
- Error rate: provider errors above `LLM_ERROR_RATE_ALERT_THRESHOLD_PERCENT` over the approved observation window.
- Unexpected provider enablement: any non-LLM provider readiness row with `realEnabled=True`.
- Gate bypass: any live LLM call without all readiness gates satisfied.
- Secret exposure: any log or evidence artifact containing an API key, bearer token, raw credential, or raw provider payload.

These thresholds are not final staged approval. Before staged internal testing,
record the exact observation window, notification path, and owner response
expectation for each alert. Unexpected provider enablement must include any
non-LLM provider readiness row with `realEnabled=True` and any live managed-auth
provider behavior not separately approved.

Proposed staged alert thresholds, pending approval:

| Alert | Proposed threshold | Observation window | Expected response |
| --- | --- | --- | --- |
| Cost anomaly | Any spend above USD 1.00/day or any spend outside the approved staged window | Daily and per-session review | Stop testing, roll back to mock/offline, notify operations and cost owners |
| Provider latency | Any single request above 5000 ms, or p95 above 5000 ms if multiple requests are approved | Per session | Stop or pause testing, review provider health and logs |
| Provider error rate | Any provider error in a 3-request session, or more than 10% if a larger approved window exists | Per session | Stop testing after the first provider error until reviewed |
| Unexpected provider enablement | Any non-LLM provider `realEnabled=True` or managed-auth live behavior without separate approval | Every readiness check | Immediate rollback and security/engineering review |
| Gate bypass | Any live LLM call without all required gates satisfied | Continuous log/readiness review | Immediate stop, rollback, and incident review |
| Secret exposure | Any API key, bearer token, Authorization header, proxy credential, raw prompt, or raw provider payload in logs/evidence | Every artifact review | Stop testing, remove artifact, rotate/revoke exposed key if real, and security review |

## Owner Placeholders

Use role placeholders until named owners are assigned in an approved internal testing plan:

- Product owner: `<product-owner>`
- Engineering owner: `<engineering-owner>`
- Operations owner: `<operations-owner>`
- Security owner: `<security-owner>`
- QA owner: `<qa-owner>`
- Test operator: `<test-operator>`
- Rollback owner: `<rollback-owner>`
- Cost owner: `<cost-owner>`

Do not add personal contact details or private escalation targets to this repository unless already approved for source control.

Owner placeholders are a staged-readiness blocker. A go-with-gates decision
requires named owners or an approved internal owner mapping for product,
engineering, operations, security, QA, test operation, rollback, and cost.

Proposed role mapping, pending approval:

| Responsibility | Placeholder owner | Required approval before staged testing |
| --- | --- | --- |
| Internal scope and participant approval | `<product-owner>` | Yes |
| Provider gates and deployment configuration | `<engineering-owner>` | Yes |
| Monitoring, log access, and escalation flow | `<operations-owner>` | Yes |
| Secret hygiene and access-boundary review | `<security-owner>` | Yes |
| Test cases and quality review | `<qa-owner>` | Yes |
| Execution and evidence capture | `<test-operator>` | Yes |
| Mock/offline rollback execution | `<rollback-owner>` | Yes |
| Budget and spend stop condition | `<cost-owner>` | Yes |

## Escalation Flow

1. Stop the current smoke or staged test immediately.
2. Reset LLM and external-call flags to mock/offline mode.
3. Remove local LLM secrets from the shell/session.
4. Restart the backend.
5. Confirm readiness is back to mock/offline mode.
6. Capture sanitized evidence and notify the assigned owners outside this repository.
7. Do not resume live testing until the issue is reviewed and the owner checklist is complete.

## Rollback Trigger Criteria

Rollback is required when:

- Readiness exposes a secret or unexpected provider detail.
- Any non-LLM provider is live-enabled unexpectedly.
- A provider call occurs outside the approved smoke window.
- Provider errors repeat or exceed the approved threshold.
- Provider latency exceeds the approved threshold.
- Estimated or observed spend exceeds the approved ceiling.
- Generated output is unsafe, ungrounded, or unsuitable for internal review.
- Mock/offline reset cannot be confirmed after a test.

Rollback confirmation is incomplete for smoke tests #2 and #3 in the current
sanitized evidence set, where rollback fields are marked as pending explicit
confirmation. A no-live rollback drill was attempted and recorded in
`docs/live-llm-rollback-drill-record.md`, but it is fail/incomplete for
staged-readiness purposes because live-configured readiness was not captured.
Before staged internal testing, either add the missing rollback confirmation or
record an explicit approver waiver, and execute a passing rollback drill.

## Rollback Drill

Without making live provider calls, rehearse the reset procedure:

```powershell
$env:ENABLE_REAL_LLM="false"
$env:ALLOW_EXTERNAL_CALLS="false"
$env:ENABLE_STAGED_INTERNAL_LLM_TESTING="false"
$env:LITINERARY_AI_PROVIDER="fake"
$env:LLM_PROVIDER="fake"
Remove-Item Env:\LLM_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:\LLM_MODEL_NAME -ErrorAction SilentlyContinue
```

Restart the backend and verify:

- `checks.externalCalls.allowed=False`.
- LLM provider mode is `mock`.
- LLM `realEnabled=False`.
- All other provider rows have `realEnabled=False`.
- No secrets are visible in readiness or logs.

## Rollback Evidence Checklist

- Date/time.
- Operator.
- Git revision or working tree identifier.
- Reset commands executed, with secrets redacted.
- Readiness summary after restart.
- Confirmation that non-LLM providers remained disabled.
- Confirmation that secrets were removed from the shell/session.
- Reviewer sign-off placeholder.

## Evidence Required For Staged Readiness

Before staged internal testing can be reconsidered:

- Three controlled smoke-test evidence files or records using the sanitized evidence template. Current status: complete.
- A completed rollback drill record using `docs/live-llm-rollback-drill-record.md`. Current status: attempted/incomplete; blocking gap.
- Generated-itinerary quality reviews using `docs/generated-itinerary-quality-review-template.md`. Current status: complete for smoke scope.
- An approved staged internal test plan based on `docs/internal-live-llm-test-plan.md`.
- No secret exposure in logs, readiness, terminal output, or evidence.
- No unexpected non-LLM live provider enablement.
- Approved internal-only access boundary.
- Approved request, latency, error-rate, and spend thresholds.
- Durable monitoring plan or approved equivalent operational control.
- Recorded rollback drill.
- Quality review of generated itineraries and known POI/routing limitations.
- Completed staged log-sink review using `docs/staged-log-sink-redaction-review-plan.md`.

Minimum blockers before staged internal testing can move to go-with-gates:

1. Record rollback confirmation for smoke tests #2 and #3 or an explicit waiver, then execute and record a passing rollback drill.
2. Define and enforce the internal-only access boundary for the staged environment.
3. Approve exact hard request ceilings and spend ceilings with accountable owners.
4. Configure durable usage/cost monitoring or an approved equivalent for the staged window.
5. Finalize alert thresholds, observation windows, notification path, and response owners.
6. Assign named or approved role owners for product, engineering, operations, security, QA, and test operation.
7. Confirm actual staged log-sink retention and redaction behavior.
8. Keep live vector DB, POI verification, routing, ticketing, affiliate, TTS, and managed auth disabled/mock unless separately approved.
