# Internal Staged-Testing Readiness Report

## Current Status

Litinerary has completed the controlled live LLM smoke-test evidence threshold:
three successful non-production smoke tests are documented with sanitized
evidence and generated-itinerary quality reviews.

Litinerary is not ready for staged internal user-facing live LLM itinerary
generation. The OpenAI-compatible adapter is gated, readiness is non-secret,
standard tests stay offline, rollback to mock mode is documented, and
`APP_ENV=internal` has explicit `ENABLE_STAGED_INTERNAL_LLM_TESTING` and
`ENABLE_INTERNAL_ACCESS_GATE` gates. The remaining blockers are operational:
rollback confirmation for the latest smoke tests, durable rate and cost controls,
approved spend ceilings, a real internal-only access boundary, monitoring and
alerting, named owner assignments, and actual staged log-sink review.

Public or beta user-facing live LLM itinerary generation remains no-go.

## Go/No-Go Recommendation

- Controlled live LLM smoke tests: evidence threshold complete, with three successful sanitized smoke-test records.
- Staged internal testing: no-go until the minimum blockers below are resolved and reviewed.
- Public or beta live LLM generation: no-go until production auth, durable abuse/cost controls, monitoring, incident response, and POI/routing quality validation are approved in a later review.

## Architecture And Safety Review

The design document defines the backend as the orchestration layer. Frontend clients should call the backend API only; provider integration belongs behind backend adapter boundaries. The current implementation matches that direction for the LLM path: route handlers call backend generation services, and the real OpenAI-compatible path is isolated behind provider contracts and external-call guards.

Current readiness by area:

| Area | Status | Notes |
| --- | --- | --- |
| Live LLM gate enforcement | Ready for smoke | Requires real LLM flag, OpenAI-compatible provider selection, API key presence, model name, global external-call flag, global environment allow-list, and LLM-specific environment allow-list. |
| Vector DB, POI, routing, ticketing, affiliate, TTS live providers | Ready for smoke isolation | Default templates keep them fake/mock/off. Staged testing must continue to verify these remain disabled unless separately approved. |
| Managed auth live metadata/JWKS calls | Guarded | Managed auth lookup is governed by the external-call policy. Staged LLM testing should keep managed auth live calls disabled unless auth testing is separately approved. |
| Request size and output bounds | Adequate for smoke | LLM input and output bounds exist. Staged limits still need product-owner signoff against expected internal usage. |
| Rate limiting | Not staged-ready | Existing local usage guards are in-memory and process-local. Live LLM per-request completion and daily completion ceilings exist for smoke control, but they are not durable abuse controls. |
| Cost controls | Not staged-ready | Budget variables and local provider ceilings exist, but there is no durable spend ledger, approved staged spend ceiling, alerting, or enforced per-user/per-environment live LLM budget. |
| Prompt and output logging | Adequate for smoke | Structured log redaction covers prompt/text/raw/token/secret-like fields. Operators must still verify log sinks do not capture raw provider payloads. |
| Provider error handling | Adequate for smoke | Provider errors are normalized into application-level errors without secret exposure. |
| Retry and timeout behavior | Adequate for smoke | Timeouts are configurable. Keep retries disabled or bounded for smoke and staged testing until retry behavior is explicitly reviewed. |
| Readiness and health | Adequate for smoke | Readiness reports non-secret gate state and provider mode. It must remain the required checkpoint before each live request. |
| Auth and ownership | Not staged-ready | Anonymous generation is part of the product design. `ENABLE_INTERNAL_ACCESS_GATE` is a fail-closed placeholder for staged internal planning, not production-grade auth or allowlisting. |
| Abuse prevention | Not staged-ready | No durable quota, account reputation, IP-level throttling, moderation workflow, or incident escalation is approved for live user traffic. |
| Monitoring and observability | Not staged-ready | Structured logs exist. Staged testing needs defined dashboards or log queries, finalized alert thresholds, retention policy, and owner response expectations. |
| Rollback to mock mode | Not staged-ready | Runbook documents resetting LLM and external-call flags and confirming mock readiness. Smoke test #1 has stop/reset evidence, while smoke tests #2 and #3 mark rollback confirmation as requiring user confirmation. A recorded rollback drill is still required before staged internal testing. |
| Test isolation | Ready | Standard tests default to mock/fake providers and must not require network access. |

## Evidence Reviewed

- `docs/live-llm-smoke-test-evidence-index.md`: confirms `3 of 3` successful smoke tests with sanitized evidence and keeps staged internal testing blocked pending this review.
- `docs/live-llm-smoke-test-001.md`: success, one controlled request, OpenAI-compatible LLM path, raw provider payload not exposed, no secret captured in evidence, routing remained `mock_routing`; rollback evidence indicates the live backend was stopped and no listener remained on port `8765`.
- `docs/live-llm-smoke-test-001-quality-review.md`: pass for controlled smoke-test evidence, not sufficient for staged internal readiness by itself.
- `docs/live-llm-smoke-test-002.md`: success, one controlled request, OpenAI-compatible LLM path, raw provider payload not exposed, no secret captured in evidence, routing remained `mock_routing`; rollback confirmation is marked as requiring user confirmation.
- `docs/live-llm-smoke-test-002-quality-review.md`: pass for controlled smoke-test evidence only, not beta/public readiness.
- `docs/live-llm-smoke-test-003.md`: success, one controlled request, OpenAI-compatible LLM path, raw provider payload not exposed, no secret captured in evidence, routing remained `mock_routing`; rollback confirmation is marked as requiring user confirmation.
- `docs/live-llm-smoke-test-003-quality-review.md`: pass for controlled smoke-test evidence only, not beta/public readiness.

## Staged Blocker Review

| Requirement | Status | Review finding |
| --- | --- | --- |
| Three controlled smoke tests with sanitized evidence | Satisfied | Three evidence files and three quality reviews exist; index reports `3 of 3`. |
| Internal-only access boundary documented and enforced | Blocking gap | The config has `ENABLE_INTERNAL_ACCESS_GATE`, but docs and code describe it as a placeholder rather than a real enforced auth or network allowlist boundary for staged testers. |
| Staged internal live LLM requires explicit staged/internal gate | Satisfied as gate | `APP_ENV=internal` live LLM use requires staged/internal flags in configuration notes and startup validation. This is necessary but not sufficient approval. |
| Approved hard request ceilings | Blocking gap | Local in-memory request ceilings exist, but staged values and owner approval are not recorded. |
| Approved spend ceilings | Blocking gap | Spend ceiling placeholders exist with default `0`, but no approved staged budget/spend owner or durable spend accounting is recorded. |
| Durable usage/cost monitoring | Blocking gap | Current usage store is in-memory and process-local; no durable ledger, dashboard, or approved equivalent is recorded. |
| Alert thresholds finalized | Blocking gap | Proposed values and observation windows are documented, but they are not approved. |
| Named owners assigned | Blocking gap | Role placeholders and proposed mapping exist; no named or approved mapped owners are recorded. |
| Rollback drill documented and/or recorded | Blocking gap | Rollback drill runbook and planned record artifact exist, but no completed drill record is present and smoke tests #2/#3 remain pending explicit rollback confirmation. |
| Log/redaction review completed | Partially satisfied | Redaction code and sanitized evidence are present; a review plan exists, but actual staged log-sink retention/review is not recorded. |
| Generated-itinerary quality review completed | Satisfied for smoke scope | Three quality reviews pass for controlled smoke evidence only. |
| POI/routing limitations documented | Satisfied | Evidence and quality reviews document bundled seed/mock POI provenance and mock routing limitations. |
| Public/beta live LLM still blocked | Satisfied | Docs and templates keep public/beta live generation no-go. |

## Current Remediation Update

This pass clarified the next blocker set without enabling staged internal
testing:

- Smoke tests #2 and #3 now explicitly mark rollback evidence as `pending explicit confirmation`.
- `docs/live-llm-rollback-drill-record.md` records an attempted no-live rollback drill. It is fail/incomplete for staged-readiness purposes because live-configured readiness was not captured before rollback; mock/offline readiness after reset was verified.
- `docs/staged-log-sink-redaction-review-plan.md` was added for actual staged log-sink retention and redaction review.
- Proposed request/spend ceilings, alert thresholds, observation windows, and owner-response expectations were added to `docs/live-llm-operational-controls.md`.
- Role-based owner placeholders were expanded to include rollback and cost ownership.

No live request was made, no staged/internal flags were enabled, and no provider
code or gates were weakened.

## Internal Access-Boundary Decision

Decision: current boundary is insufficient; staged internal testing remains
blocked.

Minimum acceptable internal boundary for a future go-with-gates decision:

1. A fail-closed route/environment access restriction must limit staged testers to an approved internal participant group.
2. The restriction must be enforced before any live LLM request can reach the itinerary-generation path.
3. The restriction may be implemented with managed auth, VPN/network allowlisting, a trusted gateway, or another security-approved equivalent.
4. `ENABLE_INTERNAL_ACCESS_GATE=true` remains necessary for `APP_ENV=internal`, but it is not sufficient by itself.
5. Managed auth live behavior must remain disabled/mock unless auth testing is separately reviewed and approved.

Current code status:

- `APP_ENV=internal` live LLM startup requires `ENABLE_STAGED_INTERNAL_LLM_TESTING=true`.
- `APP_ENV=internal` live LLM startup requires `ENABLE_INTERNAL_ACCESS_GATE=true`.
- Existing tests cover these fail-closed startup requirements.
- No production-grade route-level internal tester authorization or network allowlist is implemented in this review.

Therefore this blocker is clarified, not resolved.

## Proposed Staged Controls Pending Approval

These values are proposed, not approved, and do not authorize staged internal
testing:

| Control | Proposed value | Approval status |
| --- | --- | --- |
| Max live LLM requests per test session | 3 itinerary-generation requests | Pending approval |
| Max live LLM requests per day | 6 itinerary-generation requests | Pending approval |
| Max live LLM completion calls per request | 4 completion calls | Existing local guard; staged use pending approval |
| Max estimated daily spend | USD 1.00 | Pending approval and durable tracking |
| Max total spend for first staged window | USD 5.00 | Pending approval |
| Max itinerary duration | 1 day | Pending approval |
| Automatic retries | 0 | Pending approval |
| Latency alert | Any single request over 5000 ms | Pending approval |
| Provider error-rate alert | Any provider error in a 3-request session, or more than 10% in a larger approved window | Pending approval |
| Unexpected provider enablement alert | Any non-LLM provider `realEnabled=True` or unapproved managed-auth live behavior | Pending approval |

Expected response for any threshold breach: stop testing, roll back to
mock/offline mode, capture sanitized evidence, and notify the mapped owners
outside this repository.

## Owner Mapping Pending Approval

No real owner names were found or added. The following role mapping is proposed
and remains pending approval:

| Responsibility | Placeholder owner | Status |
| --- | --- | --- |
| Product scope and participant approval | `<product-owner>` | Pending approval |
| Provider gates and deployment configuration | `<engineering-owner>` | Pending approval |
| Monitoring, log access, and escalation flow | `<operations-owner>` | Pending approval |
| Secret hygiene and access-boundary review | `<security-owner>` | Pending approval |
| Test cases and quality review | `<qa-owner>` | Pending approval |
| Execution and evidence capture | `<test-operator>` | Pending approval |
| Mock/offline rollback execution | `<rollback-owner>` | Pending approval |
| Budget and spend stop condition | `<cost-owner>` | Pending approval |

## Staged Internal-Testing Prerequisites

Before staged internal live LLM itinerary generation is allowed, all of the following must be true:

- At least three controlled live LLM smoke tests have passed or failed safely with sanitized evidence. This is now satisfied for the smoke-test threshold.
- Each smoke test confirms mock readiness before, live-gated readiness during, and mock readiness after reset.
- Each smoke test confirms vector DB, POI, routing, ticketing, affiliate, TTS, and managed auth live provider behavior remained disabled.
- An internal-only access boundary is defined and enforced for the environment used for staged testing.
- A hard cost limit is approved for the environment, with an owner responsible for monitoring usage.
- Rate limits and request-size limits are approved for anonymous, registered, and subscriber-style flows used in the test.
- Logs and metrics are reviewed to confirm no secrets, raw API keys, bearer tokens, raw provider payloads, or sensitive prompt content are stored.
- Timeout and retry settings are reviewed, with retries disabled or bounded to prevent retry amplification.
- A rollback drill has been executed and recorded.
- Operators have a documented stop condition for provider errors, unexpected costs, unexpected live provider enablement, or unsafe output.

## Blocker Status After This Pass

Resolved or reduced:

- Smoke-test evidence threshold: resolved, `3 of 3`.
- Smoke-test quality reviews: resolved for controlled smoke scope, `3 of 3`.
- Rollback documentation: reduced from missing record format to a planned rollback drill record at `docs/live-llm-rollback-drill-record.md`; still not executed.
- Log-sink review documentation: reduced from undefined to a concrete review plan at `docs/staged-log-sink-redaction-review-plan.md`; still not executed.
- Request/spend/alert expectations: reduced from placeholders only to proposed exact values in `docs/live-llm-operational-controls.md`; still not approved.
- Owner mapping: reduced from six basic placeholders to an expanded role map including rollback and cost; still not approved.

Still pending:

- Smoke test #2 rollback confirmation or explicit waiver.
- Smoke test #3 rollback confirmation or explicit waiver.
- Executed and passing rollback drill record; the current record is attempted/incomplete.
- Enforced internal-only access boundary for staged testers.
- Approved exact request ceilings and spend ceilings.
- Durable usage/cost monitoring or approved equivalent.
- Approved alert thresholds, observation windows, notification path, and response owners.
- Approved owner mapping.
- Actual staged log-sink redaction and retention review.

## Public/Beta Blockers

Public or beta user-facing live LLM generation must remain blocked until:

- Production auth and ownership checks are enabled and tested for user-specific features.
- Durable per-user, per-IP, and per-environment rate limits are implemented.
- Durable cost accounting, budget ceilings, alerting, and emergency shutoff are implemented.
- Provider monitoring, error-rate alerts, latency alerts, and budget alerts are operational.
- POI and routing quality validation is staged, including unsupported or low-confidence location handling.
- Prompt-injection and unsafe-output review is complete for realistic user inputs.
- Privacy and logging review confirms sensitive inputs and provider responses are not retained outside approved sinks.
- Incident response and rollback procedures are rehearsed.
- A later readiness review explicitly approves public/beta rollout.

## Risk Register

| Risk | Severity | Current Mitigation | Remaining Action |
| --- | --- | --- | --- |
| Accidental live provider call in tests | High | External-call policy and mock defaults block standard tests. | Keep CI/test environments without live allow-lists or secrets. |
| LLM cost overrun | High | Smoke runbook permits one request only, and local ceilings exist. | Approve staged spend ceiling, assign owner, add durable spend tracking, and configure alerts before staged internal testing. |
| Abuse or prompt flooding | High | Local request-size and generation count guards exist. | Add durable quotas and enforce internal-only access controls before staged internal testing. |
| Secret leakage through readiness or logs | High | Readiness uses booleans; structured logs redact secret-like fields; high-confidence repository secret scan found no key-like values. | Review actual staged log sinks and retention before staged testing; keep any previously exposed key revoked/rotated. |
| Unsafe or low-quality itinerary output | Medium | Grounding validation and judge checks exist; three smoke quality reviews passed for the seeded London/Sherlock scenario. | Expand internal test cases only after staged access, monitoring, and rollback blockers are closed; live POI/routing remain disabled. |
| Retry amplification | Medium | Smoke settings should keep retries at `0`. | Document and test any bounded retry policy before broader use. |
| Rollback uncertainty | Medium | Mock reset steps exist in the runbook; smoke #1 recorded stop/offline evidence; the no-live drill verified mock/offline readiness after reset. | Rerun the no-live rollback drill from the trusted PowerShell context and capture live-configured readiness before rollback; add user-confirmed rollback evidence for smoke #2 and #3 or an explicit waiver. |
| Auth posture insufficient for live users | High | Public/beta live LLM remains no-go. | Complete production auth and ownership validation before beta/public use. |

## Required Operational Gates

Staged internal testing requires:

- Standard backend and frontend checks passing.
- Smoke preflight output with `liveLlmSmokeReady=True`.
- Sanitized readiness evidence before, during, and after the test.
- Operator confirmation that no other live providers are enabled.
- Internal-only access restriction for any route used by internal testers.
- Approved daily request and spend ceilings for the environment.
- Alert owner and escalation path for provider errors, latency, and cost.
- Rollback command sequence tested in the same environment.
- Written approval that the staged test is internal-only and not beta/public traffic.

Because staged internal testing remains no-go, these gates are requirements for a
future go-with-gates decision rather than active approval.

## Required Environment Gates

For controlled smoke tests:

- `APP_ENV=development` or another explicitly approved non-production environment.
- `ENABLE_REAL_LLM=true`.
- `ALLOW_EXTERNAL_CALLS=true`.
- `EXTERNAL_CALL_ALLOWED_ENVIRONMENTS` includes the current `APP_ENV`.
- `LITINERARY_AI_PROVIDER=openai_compatible`.
- `LLM_PROVIDER=openai_compatible`.
- `LLM_API_KEY` is supplied from approved local environment or secret storage only.
- `LLM_MODEL_NAME` is set.
- `LLM_ALLOWED_ENVIRONMENTS` includes the current `APP_ENV`.
- Other live-provider enablement flags remain false.
- Mock/fake provider names remain selected for vector DB, POI, routing, ticketing, affiliate, TTS, and auth unless a separate review approves otherwise.

For staged internal testing, add:

- `APP_ENV=internal`.
- `ENABLE_STAGED_INTERNAL_LLM_TESTING=true`.
- `ENABLE_INTERNAL_ACCESS_GATE=true`.
- An explicit internal-only access boundary.
- Approved spend ceiling and rate-limit values.
- Monitoring and rollback owners.
- No production or public/beta traffic.

These environment gates must not be enabled until the staged internal go/no-go
review moves from no-go to go-with-gates.

## Evidence Required From Controlled Smoke Tests

Capture only sanitized evidence:

- Date, operator, and Git revision or working tree identifier.
- Backend and frontend validation summaries.
- Preflight output showing `liveLlmSmokeReady=True` without secret values.
- Mock readiness summary before live mode.
- Live readiness summary with secret values redacted.
- One request summary with destination, book, duration, and transportation mode only.
- Sanitized result summary with itinerary ID, provider name, day count, and stop count.
- Log review summary confirming no secrets or raw provider payloads.
- Cost or usage observation available from the provider console, redacted and summarized.
- Reset readiness summary proving mock/offline mode was restored.
- Confirmation that non-LLM live providers remained disabled.
- Completed `docs/live-llm-smoke-test-evidence-template.md` entry.
- Completed rollback drill record.
- Completed generated-itinerary quality review.

Current review result: the smoke-test evidence and quality-review threshold is
complete. Rollback confirmation is incomplete for smoke tests #2 and #3 and must
be resolved or explicitly waived by the staged-testing approvers before any
go-with-gates decision.

## Rollback Procedure

Stop the live-gated backend, then reset the shell or environment manager:

```powershell
$env:ENABLE_REAL_LLM="false"
$env:ALLOW_EXTERNAL_CALLS="false"
$env:LITINERARY_AI_PROVIDER="fake"
$env:LLM_PROVIDER="fake"
Remove-Item Env:\LLM_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:\LLM_MODEL_NAME -ErrorAction SilentlyContinue
```

Restart the backend and confirm:

- `externalCalls.allowed=False`.
- LLM provider mode is `mock`.
- LLM `realEnabled=False`.
- Other providers remain fake/mock/offline.
- No queued live test traffic remains.

If rollback cannot be confirmed, stop the backend process and treat the environment as unavailable until configuration is audited.

## Owner Checklist

- Product owner approves internal-only scope and test inputs.
- Engineering owner confirms provider gates and environment values.
- Operations owner confirms budget, logs, alerts, and rollback path.
- Security owner confirms no secret exposure and no public/beta access.
- QA owner confirms standard tests remain offline and pass.
- Test operator records sanitized evidence for each smoke test.

## Minimum Remediation List

Required before staged internal testing can move from no-go to go:

1. Record or explicitly approve rollback confirmation for smoke tests #2 and #3, and execute a passing rollback drill using `docs/live-llm-rollback-drill-record.md`.
2. Define and enforce the internal-only access boundary for the staged environment, such as managed auth, VPN/network allowlisting, or another approved fail-closed control.
3. Approve hard daily request ceilings for the staged environment, including the exact values and accountable owner.
4. Approve hard spend ceilings for live LLM usage, including the exact daily and total staged-test budget and accountable owner.
5. Add or configure durable usage/cost monitoring sufficient for the staged environment, or record an explicitly approved equivalent control.
6. Finalize alert thresholds, observation windows, and owner response expectations for cost, error rate, latency, unexpected provider enablement, gate bypass, and secret exposure.
7. Assign named or approved role owners for product, engineering, operations, security, QA, and test operation.
8. Confirm log retention and redaction behavior in the actual environment used for staged testing using `docs/staged-log-sink-redaction-review-plan.md`.
9. Keep live vector DB, POI verification, routing, ticketing, affiliate, TTS, and managed auth disabled/mock unless separately reviewed and approved.

Until these items are complete, staged internal live LLM itinerary generation remains no-go.

Related operational documents:

- `docs/live-llm-smoke-test-runbook.md`
- `docs/live-llm-operational-controls.md`
- `docs/live-llm-smoke-test-evidence-template.md`
- `docs/live-llm-rollback-drill.md`
- `docs/generated-itinerary-quality-review-template.md`
- `docs/internal-live-llm-test-plan.md`
