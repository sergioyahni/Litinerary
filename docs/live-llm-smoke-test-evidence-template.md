# Live LLM Smoke-Test Evidence Template

Use this template for controlled non-production smoke tests only. Do not include secrets, raw provider payloads, bearer tokens, API keys, personal data, or unredacted logs.

## Test Metadata

- Smoke test number:
- Date/time:
- Operator:
- Reviewer:
- Git revision or working tree identifier:
- Environment:
- Backend command:
- Frontend command, if relevant:

## Credential Presence

- `LLM_API_KEY` present: true/false
- `LLM_MODEL_NAME` present: true/false
- Model name value recorded: no, unless approved as non-secret
- Confirmation that no secret value was captured:

## Gate Summary

- `APP_ENV`:
- `ENABLE_REAL_LLM`:
- `ALLOW_EXTERNAL_CALLS`:
- `ENABLE_STAGED_INTERNAL_LLM_TESTING`, if `APP_ENV=internal`:
- `EXTERNAL_CALL_ALLOWED_ENVIRONMENTS` includes `APP_ENV`:
- `LLM_ALLOWED_ENVIRONMENTS` includes `APP_ENV`:
- `LITINERARY_AI_PROVIDER`:
- `LLM_PROVIDER`:
- Other live providers disabled:
- Preflight `liveLlmSmokeReady`:

## Validation Results

- Backend pytest summary:
- Frontend test summary:
- Frontend typecheck summary:
- Frontend build summary:
- Network calls before live smoke: none/describe safe exception

## Readiness Before Live Mode

- `status`:
- `externalCalls.allowed`:
- LLM provider:
- LLM mode:
- LLM real enabled:
- LLM required config present:
- Other live provider count:
- Secret values absent from readiness:

## Readiness During Live Mode

- `status`:
- `externalCalls.allowed`:
- LLM provider:
- LLM mode:
- LLM real enabled:
- LLM required config present:
- LLM environment allowed:
- Max live calls per request:
- Daily live request ceiling:
- Latency alert threshold:
- Error-rate alert threshold:
- Other live provider count:
- Secret values absent from readiness:

## Request Summary

- Endpoint:
- Destination:
- Book:
- Duration days:
- Transportation mode:
- Sensitive personal data included: no
- Request count: 1

## Sanitized Result Summary

- Request succeeded: true/false
- Safe failure code, if any:
- Itinerary ID:
- Itinerary title:
- Provider name:
- Provider type:
- Day count:
- Stop count:
- Latency observed:
- Estimated cost, if available:
- Provider console cost checked: true/false/not available

## Log Review

- Logs reviewed:
- API key absent:
- Bearer token absent:
- Raw provider payload absent:
- Raw prompt/private user data absent:
- Provider error details safe:

## Rollback Confirmation

- `ENABLE_REAL_LLM=false`:
- `ALLOW_EXTERNAL_CALLS=false`:
- `ENABLE_STAGED_INTERNAL_LLM_TESTING=false`:
- `LITINERARY_AI_PROVIDER=fake`:
- `LLM_PROVIDER=fake`:
- `LLM_API_KEY` removed from shell/session:
- `LLM_MODEL_NAME` removed or reset:
- Backend restarted:
- Readiness returned to mock/offline:
- Other providers remained disabled:

## Errors Or Anomalies

- Errors encountered:
- Unexpected provider enablement:
- Unexpected cost:
- Unexpected latency:
- Unsafe output:
- Follow-up required:

## Sign-Off

- Test operator sign-off:
- Reviewer sign-off:
- Decision for next smoke test:
- Decision for staged internal testing: no-go unless all staged blockers are satisfied
