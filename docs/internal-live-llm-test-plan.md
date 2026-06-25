# Internal Live LLM Test Plan

## Status

This is a planning document only. Staged internal live LLM itinerary generation remains no-go until every entry criterion is satisfied and a later readiness review approves the test.

## Entry Criteria

- At least three controlled live LLM smoke tests are complete using `docs/live-llm-smoke-test-evidence-template.md`.
- Each smoke test confirms mock readiness before, live-gated readiness during, and mock readiness after reset.
- `docs/live-llm-rollback-drill.md` has a completed passing drill record.
- `docs/generated-itinerary-quality-review-template.md` has been completed for smoke outputs.
- Log/redaction review confirms no secrets, bearer tokens, raw provider payloads, or private prompt data were retained.
- Internal-only access boundary is approved outside this repository.
- Cost, request, latency, and error-rate thresholds are approved.
- Monitoring or an approved equivalent operational control is ready.

## Participant Roles

Use placeholders until named owners are assigned outside source control:

- Product owner: `<product-owner>`
- Engineering owner: `<engineering-owner>`
- Operations owner: `<operations-owner>`
- Security owner: `<security-owner>`
- QA owner: `<qa-owner>`
- Test operator: `<test-operator>`
- Internal participant group: `<internal-participant-group>`

## Permitted Test Scenarios

- Seed-backed destination/book combinations only.
- Short itinerary generation, preferably one day.
- General sightseeing traveler profile without sensitive personal data.
- Review of output quality, latency, safe failure behavior, and rollback.
- Mock/fake vector DB, POI, routing, ticketing, affiliate, TTS, and managed auth.

## Prohibited Scenarios

- Public, beta, or production traffic.
- Sensitive personal data in prompts or notes.
- Live vector DB, POI, routing, ticketing, affiliate, TTS, or managed auth unless separately approved.
- Payment, booking, ticket purchase, affiliate conversion, or e-commerce flows.
- Attempts to bypass environment gates, usage limits, auth guards, or external-call policy.
- Stress testing or load testing against a live LLM provider.

## Required Provider Gates

All of these must be true for staged internal live LLM testing, after later approval:

```text
APP_ENV=internal
ENABLE_REAL_LLM=true
ENABLE_STAGED_INTERNAL_LLM_TESTING=true
ENABLE_INTERNAL_ACCESS_GATE=true
ALLOW_EXTERNAL_CALLS=true
EXTERNAL_CALL_ALLOWED_ENVIRONMENTS includes internal
LITINERARY_AI_PROVIDER=openai_compatible
LLM_PROVIDER=openai_compatible
LLM_API_KEY present from approved secret storage
LLM_MODEL_NAME set
LLM_ALLOWED_ENVIRONMENTS includes internal
```

Other live providers must remain disabled unless separately approved.

## Cost And Request Ceilings

Proposed internal staged values, pending approval:

- `LLM_MAX_LIVE_CALLS_PER_REQUEST=4`
- `LLM_DAILY_LIVE_REQUEST_CEILING=6`
- `LLM_DAILY_ESTIMATED_SPEND_CEILING_USD=1`
- `PROVIDER_DAILY_COST_CEILING_USD=1`
- `LLM_LATENCY_ALERT_THRESHOLD_MS=5000`
- `LLM_ERROR_RATE_ALERT_THRESHOLD_PERCENT=10`
- `ITINERARY_GENERATION_MAX_DAYS=1`
- `LLM_MAX_RETRIES=0`

These values are proposed, not approved. Local in-memory guardrails are not
durable distributed controls. A durable monitor or approved operational
equivalent is required before staged internal testing.

## Monitoring Checklist

- Live LLM request count visible.
- Provider success/failure count visible.
- Provider latency visible.
- Provider error types visible.
- Estimated or provider-reported spend visible.
- Blocked gate/usage-policy events visible.
- Unexpected non-LLM provider enablement visible.
- Log redaction reviewed.
- Owner and escalation path confirmed.

## Rollback Criteria

Rollback immediately if:

- A secret appears in readiness, logs, screenshots, or evidence.
- Any non-LLM provider becomes live-enabled unexpectedly.
- Spend exceeds approved ceiling.
- Latency or error rate exceeds approved threshold.
- Output is unsafe, ungrounded, or unsuitable for internal review.
- Mock/offline reset cannot be confirmed.

## Evidence Requirements

- Completed smoke-test evidence template for each run.
- Completed quality review template for each generated itinerary.
- Completed rollback drill evidence.
- Sanitized readiness before/during/after.
- Sanitized log/redaction review.
- Provider console cost or usage summary if available, redacted.
- Reviewer sign-off placeholders completed.

## Exit Criteria

Staged internal testing can be considered complete only when:

- All planned internal scenarios are complete.
- No blocker severity issues remain open.
- Rollback was successful and repeatable.
- Cost/rate behavior stayed within approved ceilings.
- Output quality review passed for planned scenarios.
- A later readiness review decides whether to proceed, repeat, or stop.

## No-Go Criteria

No-go if any of these are true:

- Fewer than three controlled smoke tests are complete.
- Internal-only access boundary is not enforced.
- Durable monitoring or approved equivalent is missing.
- Secrets appear in any artifact.
- Public/beta/production traffic is involved.
- Any non-LLM provider is unexpectedly live-enabled.
- Rollback drill fails.
- Quality review identifies unresolved unsafe or hallucinated output.
