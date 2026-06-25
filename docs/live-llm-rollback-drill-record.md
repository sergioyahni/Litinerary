# Live LLM Rollback Drill Record

## Status

- Drill status: attempted/incomplete; fail for staged-readiness purposes
- Staged internal testing impact: no-go until this drill is executed successfully, recorded, and reviewed, or an explicit approver waiver is recorded.
- Live LLM request required for this drill: no. This drill validates reset behavior and readiness without making a live provider request unless a later approved runbook explicitly expands the scope.
- Live LLM request made during this drill attempt: no
- `/v1/chat/completions` called during this drill attempt: no
- API key printed during this drill attempt: no
- Raw provider payload printed during this drill attempt: no

## Purpose

Verify that a Litinerary operator can return an approved non-production live LLM
test environment to mock/offline mode, remove local live credentials from the
active shell/session, and prove via readiness that live LLM and all other live
providers are disabled.

## Drill Metadata

- Drill date/time: 2026-06-20 10:00:36 +03:00
- Environment: local development / controlled smoke-test context
- Git revision or working tree identifier: dirty working tree; exact revision not recorded in sanitized evidence
- Test operator: Codex, using local safe commands only
- Rollback owner: `<rollback-owner>`
- Engineering reviewer: `<engineering-owner>`
- Security reviewer: `<security-owner>`
- Operations reviewer: `<operations-owner>`

## Exact Pre-Drill State

Record sanitized state only. Do not include secrets, raw provider payloads, proxy
credentials, bearer tokens, or Authorization headers.

- Backend process running: no backend was running before the helper start in this drill attempt
- `APP_ENV`: `development`, from safe smoke preflight
- `ENABLE_REAL_LLM`: true, from safe smoke preflight
- `ALLOW_EXTERNAL_CALLS`: true, from safe smoke preflight
- `ENABLE_STAGED_INTERNAL_LLM_TESTING`: `<pending>`
- `ENABLE_INTERNAL_ACCESS_GATE`: `<pending>`
- `LITINERARY_AI_PROVIDER`: `openai_compatible`, from safe smoke preflight
- `LLM_PROVIDER`: `openai_compatible`, from safe smoke preflight
- `LLM_API_KEY` present as boolean only: true
- `LLM_MODEL_NAME` present as boolean only: true
- Other live providers disabled: true
- Managed auth live disabled: true
- Safe preflight result: `liveLlmSmokeReady=True`
- Readiness captured before reset: not captured; live-configured readiness check failed before a response was obtained

## Executed No-Live Drill Attempt

Commands executed, summarized with secret values omitted:

1. Ran `scripts/live_llm_smoke_preflight.ps1 -RequireLiveReady`.
2. Started `scripts/live_llm_smoke_backend.ps1 -Background`.
3. Attempted local readiness check against `http://127.0.0.1:8765/api/readiness`.
4. Stopped drill-started backend Python processes.
5. Confirmed port `8765` was closed with a short local TCP probe.
6. Set mock/offline environment values in the active drill shell.
7. Started a mock/offline backend.
8. Captured mock/offline readiness.
9. Stopped the mock/offline backend.

Observed sanitized results:

- Safe preflight loaded `.env.development.local`.
- Safe preflight reported `liveLlmSmokeReady=True`.
- Safe preflight reported `llmApiKeyPresent=True` and `llmModelNamePresent=True` as booleans only.
- Safe preflight reported `otherLiveProvidersDisabled=True`.
- Safe preflight reported `managedAuthLiveDisabled=True`.
- Live backend helper reported `serverPid=20608` on the first attempt and `serverPid=22900` on the second attempt.
- Local live-readiness capture failed before a readiness response was obtained.
- After stopping drill-started backend processes, a short local TCP probe reported `tcp8765Open=False`.
- Mock-only readiness after reset reported `status=ready`.
- Mock-only readiness after reset reported `externalAllowed=False`.
- Mock-only readiness after reset reported `stagedInternal=False`.
- Mock-only readiness after reset reported `internalGate=False`.
- Mock-only readiness after reset reported `llmProvider=fake`.
- Mock-only readiness after reset reported `llmMode=mock`.
- Mock-only readiness after reset reported `llmRealEnabled=False`.
- Mock-only readiness after reset reported `otherLiveProviderCount=0`.

Result: fail/incomplete for staged-readiness purposes because live-configured
readiness before rollback was not captured. The mock/offline reset side was
verified, and no live provider request was made.

## Rollback Commands

Stop the live-gated backend process, then run these commands in the active
shell/session or equivalent environment manager. Do not print secret values.

```powershell
$env:ENABLE_REAL_LLM="false"
$env:ALLOW_EXTERNAL_CALLS="false"
$env:ENABLE_STAGED_INTERNAL_LLM_TESTING="false"
$env:ENABLE_INTERNAL_ACCESS_GATE="false"
$env:LITINERARY_AI_PROVIDER="fake"
$env:LLM_PROVIDER="fake"
Remove-Item Env:\LLM_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:\LLM_MODEL_NAME -ErrorAction SilentlyContinue
```

Keep all non-LLM providers disabled:

```powershell
$env:ENABLE_REAL_VECTOR_DB="false"
$env:ENABLE_REAL_POI_PROVIDER="false"
$env:ENABLE_REAL_ROUTING="false"
$env:ENABLE_REAL_TICKETING="false"
$env:ENABLE_AFFILIATE_LINKS="false"
$env:ENABLE_REAL_TTS="false"
$env:ENABLE_AUTH="false"
$env:AUTH_PROVIDER="dev"
$env:LITINERARY_VECTOR_PROVIDER="fake"
$env:VECTOR_DB_PROVIDER="fake"
$env:LITINERARY_POI_VERIFICATION_PROVIDER="mock"
$env:POI_PROVIDER="mock"
$env:ROUTING_PROVIDER="mock"
$env:TICKETING_PROVIDER="mock"
$env:AFFILIATE_PROVIDER="mock"
$env:TTS_PROVIDER="mock"
```

Restart the backend in mock/offline mode, then capture readiness:

```powershell
$readiness = Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/readiness"
$readiness.status
$readiness.checks.externalCalls
$readiness.checks.providers | Select-Object providerType,providerName,mode,realEnabled,externalCallsAllowed,requiredConfigPresent,environmentAllowed
```

## Expected Post-Drill Readiness

- `status=ready`
- `checks.externalCalls.allowed=False`
- `checks.externalCalls.stagedInternalLlmTestingEnabled=False`
- `checks.externalCalls.internalAccessGateEnabled=False`
- LLM provider mode is `mock`
- LLM `realEnabled=False`
- Vector DB `realEnabled=False`
- POI verification `realEnabled=False`
- Routing `realEnabled=False`
- Ticketing `realEnabled=False`
- Affiliate `realEnabled=False`
- TTS `realEnabled=False`
- Managed auth live behavior disabled unless separately approved
- No secret values appear in readiness or logs

## Evidence Checklist

- Sanitized pre-drill readiness summary captured: no; safe preflight captured instead
- Reset commands executed with secrets redacted: yes, in the drill shell
- Backend stopped: yes, drill-started backend processes were stopped
- Backend restarted: yes, mock/offline backend was started for readiness verification
- Sanitized post-drill readiness summary captured: yes, mock/offline readiness captured
- Non-LLM providers remained disabled: yes, mock/offline readiness reported `otherLiveProviderCount=0`
- `LLM_API_KEY` removed from shell/session: yes, in the drill shell; source env file status not changed
- `LLM_MODEL_NAME` removed or reset: yes, in the drill shell; source env file status not changed
- No raw provider payload captured: yes
- No Authorization header captured: yes
- No full raw response dump captured: yes
- Logs reviewed for secret/redaction expectations: limited local helper logs reviewed; no secret values were printed in reviewed output
- Anomalies recorded: live-configured readiness check failed before a response was obtained; PowerShell localhost readiness appeared to hang or fail in this process context

## Pass/Fail Criteria

Pass only if all are true:

- The backend returns to mock/offline readiness.
- External calls are disabled.
- Staged internal LLM testing is disabled.
- Internal access gate is disabled.
- LLM and all non-LLM providers have `realEnabled=False`.
- No secrets, raw provider payloads, bearer tokens, or Authorization headers appear in evidence.
- Reviewers sign off below.

Fail if any live provider remains enabled, readiness exposes secret values,
rollback cannot be confirmed, or the backend cannot be returned to a known
mock/offline state.

## Sign-Off

- Test operator: `<pending>`
- Rollback owner: `<pending>`
- Engineering reviewer: `<pending>`
- Security reviewer: `<pending>`
- Operations reviewer: `<pending>`
- Decision: fail/incomplete for staged-readiness purposes
- Follow-up required: rerun the no-live rollback drill manually from the trusted PowerShell context, capture live-configured readiness before rollback, then capture mock/offline readiness after rollback.
