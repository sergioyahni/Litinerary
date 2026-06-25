# Live LLM Smoke-Test Evidence Index

This index tracks sanitized evidence for controlled non-production live LLM smoke
tests. Do not include API keys, bearer tokens, raw provider payloads, raw prompts,
proxy credentials, personal data, or unredacted logs.

## Current Status

- Required successful smoke tests before staged internal testing review: 3.
- Successful smoke tests with sanitized evidence in this repository: 3 of 3.
- Remaining successful smoke tests required before Prompt 3/staged-readiness evidence: 0.
- Operator-reported successful smoke tests outside this repository: 0 not yet documented.
- Codex-executed smoke tests in this pass: 0.
- Controlled live LLM smoke-test evidence threshold: complete.
- Staged internal testing: no-go until a separate go/no-go review is completed.
- Public/beta live LLM generation: no-go.

## Evidence Entries

| Smoke test | Status | Evidence location | Quality review | Notes |
| --- | --- | --- | --- | --- |
| Manual smoke test #1 | Successful; documented from sanitized operator-supplied evidence | `docs/live-llm-smoke-test-001.md` | `docs/live-llm-smoke-test-001-quality-review.md` | Counts as 1 of 3 controlled smoke tests. |
| Manual smoke test #2 | Successful; documented from sanitized operator-supplied evidence | `docs/live-llm-smoke-test-002.md` | `docs/live-llm-smoke-test-002-quality-review.md` | Counts as 2 of 3 controlled smoke tests; rollback confirmation is pending explicit confirmation or waiver. |
| Manual smoke test #3 | Successful; documented from sanitized operator-supplied evidence | `docs/live-llm-smoke-test-003.md` | `docs/live-llm-smoke-test-003-quality-review.md` | Counts as 3 of 3 controlled smoke tests; rollback confirmation is pending explicit confirmation or waiver. |

## Blocked Attempt Log

| Attempt | Executor | Result | Reason |
| --- | --- | --- | --- |
| Codex repeat attempt | Codex process | Blocked before live request | `scripts/live_llm_network_preflight.ps1` reported `networkPreflightReady=False`, with `tcp443Ok=False`, `httpsOk=False`, and `backendPythonHttpsOk=False` in the Codex process context. |

## Required Evidence For Each Successful Smoke Test

- Completed `docs/live-llm-smoke-test-evidence-template.md`.
- Completed `docs/generated-itinerary-quality-review-template.md`.
- Preflight summary showing `liveLlmSmokeReady=True`.
- Readiness before/during/after summaries with secrets absent.
- Request summary only: destination, book, duration, transportation mode.
- Sanitized result summary: itinerary ID/title/provider/day count/stop count.
- Latency and estimated cost if available.
- Rollback confirmation showing mock/offline mode restored.
- Confirmation that other live providers remained disabled.
- Confirmation that no secrets, raw provider payloads, or private user data were captured.

## Next Review Step

The controlled live LLM smoke-test evidence threshold is complete: three
successful smoke tests are documented with sanitized in-repo evidence and quality
reviews. This does not automatically approve staged internal testing, and it
does not approve public/beta live LLM generation.

Next recommended prompt: perform the separate internal staged-testing go/no-go
review, including operational readiness, rollback confirmation, monitoring,
usage limits, and any remaining staged-readiness blockers.

## Counting Rule

A smoke test counts toward the three-test requirement only when the sanitized
evidence and quality review are captured. Operator-reported success without a
sanitized evidence artifact should be treated as useful operational context, not
as staged-readiness evidence.

Prompt 3 smoke-test evidence is complete because three successful smoke tests are
documented with sanitized evidence and quality reviews. Staged internal testing
remains blocked until a separate go/no-go review confirms that operational
readiness blockers are satisfied.

Rollback note: a no-live rollback drill was attempted from the Codex process and
recorded in `docs/live-llm-rollback-drill-record.md`, but it is incomplete for
staged-readiness purposes because live-configured readiness was not captured.
Smoke tests #2 and #3 still require rollback confirmation or an explicit waiver.
