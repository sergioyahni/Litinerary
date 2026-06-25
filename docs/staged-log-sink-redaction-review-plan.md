# Staged Log-Sink Redaction And Retention Review Plan

## Status

- Review status: planned/not yet recorded
- Staged internal testing impact: blocking gap until the actual staged log sinks are identified, reviewed, and approved.
- Public/beta live generation: no-go.

## Purpose

Confirm that the environment used for any future staged internal live LLM test
does not retain secrets, raw provider payloads, bearer tokens, Authorization
headers, raw prompts, private user data, proxy credentials, or full raw response
dumps outside approved sinks.

## Log Sinks To Check

Complete this list for the staged environment before any go-with-gates decision:

- Backend application logs:
- Web/API gateway logs:
- Process manager or container logs:
- Hosting platform logs:
- Reverse proxy/load balancer logs:
- Error tracking system:
- Metrics/telemetry backend:
- CI/CD logs:
- Operator terminal transcript policy:
- Provider console usage/cost screens:
- Browser/frontend logs, if internal testers use a frontend:

If no staged log sink exists yet, this review remains blocked.

## Retention Expectations

- Retention duration: proposed 7 days for staged test logs, pending approval.
- Access scope: internal owner group only, pending approval.
- Export/sharing: sanitized summaries only.
- Deletion path: documented before staged testing.
- Long-term retention: no raw prompts, raw provider payloads, or secrets.

## Redaction Expectations

The following must be absent or redacted in every sink:

- API keys and provider credentials
- Bearer tokens and Authorization headers
- Proxy credentials
- Raw provider request and response payloads
- Raw prompts and private user notes
- Full raw itinerary-generation response dumps
- Personal data not required for the staged test

Allowed fields include provider name, provider type, safe error code, latency,
request count, boolean credential presence, non-secret readiness flags, and
sanitized cost/usage summaries.

## Sentinel Secret Test Approach

Use a fake sentinel value only, never a real credential. The sentinel must be
non-functional and clearly artificial.

1. Configure a local or staged dry-run path that does not make a live LLM request.
2. Use a fake sentinel string in a controlled request header or environment field
   that should be redacted by logs.
3. Exercise readiness or a mock-only endpoint.
4. Search every log sink for the sentinel.
5. Pass only if the sentinel is absent or replaced by an approved redaction marker.

Do not use a real API key for sentinel testing. Do not send sentinel values to a
live provider.

## Raw Provider Payload Exclusion

- Provider request bodies must not be logged.
- Provider response bodies must not be logged.
- Provider diagnostics must remain allow-listed and provider-neutral.
- Development-only diagnostics must not include prompts, raw provider bodies,
  proxy values, credentials, or private user data.

## Prompt And User-Data Handling

- Staged prompts must avoid sensitive personal data.
- Test cases must use seed-backed destination/book combinations.
- If user-entered free text is tested later, privacy review must approve the
  input category before live use.
- Logs must not retain raw prompt text or private user notes.

## Pass/Fail Criteria

Pass only if:

- Every actual staged log sink is listed and reviewed.
- Retention duration and access scope are approved.
- Sentinel secret test passes across every sink.
- Raw provider payloads are absent.
- Authorization headers and bearer tokens are absent.
- Raw prompts/private user data are absent or approved-redacted.
- Evidence is captured as sanitized summaries only.

Fail if any sink is unknown, inaccessible for review, retains unsafe fields, or
lacks an approved retention/access policy.

## Evidence Required

- Reviewed sink list with owner:
- Retention policy summary:
- Access-control summary:
- Sentinel test date and fake sentinel category, not value:
- Search result summary by sink:
- Raw provider payload exclusion confirmation:
- Prompt/user-data handling confirmation:
- Reviewer sign-off:

## Owner Placeholders

- Operations owner: `<operations-owner>`
- Security owner: `<security-owner>`
- Engineering owner: `<engineering-owner>`
- Test operator: `<test-operator>`
