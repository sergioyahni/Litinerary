# Live LLM Rollback Drill

## Purpose

This drill verifies that a Litinerary operator can return a local or approved non-production live LLM smoke-test environment to mock/offline mode quickly and prove that readiness reflects the reset.

This is a drill and runbook. It does not approve staged internal, beta, public, or production live LLM usage.

## Scope

In scope:

- Resetting live LLM and external-call environment flags.
- Removing local LLM secrets from the active shell/session.
- Restarting the backend.
- Verifying readiness returns to mock/offline mode.
- Confirming non-LLM live providers remain disabled.

Out of scope:

- Running a live LLM call.
- Connecting vector DB, POI, routing, ticketing, affiliate, TTS, managed auth, or other live providers.
- Production incident response.
- Public/beta traffic.

## Prerequisites

- Standard backend and frontend checks have passed.
- The operator has access to the local backend shell.
- No real secrets are written to tracked files.
- Any local secret file, such as `.env.local`, is confirmed ignored by Git.
- The live LLM smoke-test runbook and operational controls docs have been reviewed.

## Immediate Reset Steps

Stop the backend process used for the smoke test, then reset the current shell:

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

Keep all other live providers disabled:

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

## Backend Restart And Checks

From the repository root:

```powershell
cd backend
..\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

In another shell:

```powershell
$readiness = Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/readiness"
$readiness.status
$readiness.checks.externalCalls
$readiness.checks.providers | Select-Object providerType,providerName,mode,realEnabled,externalCallsAllowed,requiredConfigPresent,environmentAllowed
```

## Expected Mock/Offline Readiness

- `status=ready`.
- `checks.externalCalls.allowed=False`.
- `checks.externalCalls.stagedInternalLlmTestingEnabled=False`.
- `checks.externalCalls.internalAccessGateEnabled=False`.
- LLM `mode=mock`.
- LLM `realEnabled=False`.
- All non-LLM providers have `realEnabled=False`.
- No secret values appear in readiness output.

## Failure Modes

- Backend cannot restart: stop the process and inspect local config before retrying.
- Readiness remains `degraded`: inspect database status and startup notes.
- `externalCalls.allowed=True`: reset `ALLOW_EXTERNAL_CALLS=false` and restart.
- LLM remains real-enabled: reset `ENABLE_REAL_LLM=false`, fake providers, and restart.
- Any non-LLM provider is real-enabled: reset the matching feature flag and provider name before proceeding.
- A secret appears in readiness or logs: stop testing, remove the artifact, and escalate to the security owner placeholder.

## Evidence Checklist

- Drill date/time:
- Operator:
- Git revision or working tree identifier:
- Reset commands executed, with secrets redacted:
- Backend restarted:
- Readiness status:
- `externalCalls.allowed=False`:
- `stagedInternalLlmTestingEnabled=False`:
- `internalAccessGateEnabled=False`:
- LLM mock/offline:
- Other providers disabled:
- Secrets absent from readiness/log output:
- Anomalies:

Use `docs/live-llm-rollback-drill-record.md` to record a completed drill. Until
that artifact is completed and reviewed, the rollback drill remains
planned/not yet recorded and staged internal testing remains no-go.

## Sign-Off

- Test operator:
- Engineering reviewer:
- Security reviewer:
- Decision: pass/fail
- Follow-up required:
