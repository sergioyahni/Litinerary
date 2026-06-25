# Cloud Target Readiness Checklist

Use this template after the user approves a specific non-production cloud
target. Do not store real secrets in this file.

## Target Identity

- [ ] Selected platform:
- [ ] Cloud project/account:
- [ ] Environment name:
- [ ] Backend service name:
- [ ] Frontend service name:
- [ ] Database instance:
- [ ] Log sink:
- [ ] Operator:
- [ ] Commit SHA:

## Runtime Versions

- [ ] Python version:
- [ ] Node.js version:
- [ ] Package manager:
- [ ] Database engine/version:
- [ ] OS/runtime image:

## Build And Start

- [ ] Backend build/package command:
- [ ] Backend start command:
- [ ] Frontend build command: `npm.cmd run build`
- [ ] Frontend serving approach:
- [ ] Backend port/binding:
- [ ] Platform-specific port variable:

## Database And Seed

- [ ] Database choice:
- [ ] Database is non-production:
- [ ] Database URL stored only in platform config/secret store:
- [ ] Migration command:
- [ ] Seed command:
- [ ] Seed validation command or endpoint:
- [ ] Rollback/reset plan:

## Environment Variables

- [ ] `APP_ENV`:
- [ ] `ENABLE_REAL_LLM=false`
- [ ] `ALLOW_EXTERNAL_CALLS=false`
- [ ] `ENABLE_STAGED_INTERNAL_LLM_TESTING=false`
- [ ] `ENABLE_INTERNAL_ACCESS_GATE=false`
- [ ] `ENABLE_MOCK_SERVICES=true`
- [ ] `LITINERARY_AI_PROVIDER=fake`
- [ ] `LLM_PROVIDER=fake`
- [ ] `LITINERARY_VECTOR_PROVIDER=fake`
- [ ] `VECTOR_DB_PROVIDER=fake`
- [ ] `POI_VERIFICATION_PROVIDER=mock`
- [ ] `ROUTING_PROVIDER=mock`
- [ ] `TICKETING_PROVIDER=mock`
- [ ] `AFFILIATE_PROVIDER=mock`
- [ ] `TTS_PROVIDER=mock`
- [ ] `PROVIDER_DAILY_COST_CEILING_USD=0`
- [ ] No `LLM_API_KEY` configured.
- [ ] No real provider credentials configured.

## Secret Storage

- [ ] Platform secret/config store identified:
- [ ] Database URL stored outside tracked files:
- [ ] No cloud credentials in repository:
- [ ] No API keys in environment templates:
- [ ] Runtime config can be reviewed without printing secret values:

## Health And Readiness

- [ ] Health endpoint URL:
- [ ] Readiness endpoint URL:
- [ ] Health expected result: `status=ok`
- [ ] Readiness expected result: `status=ready`
- [ ] Readiness must show external calls disabled:
- [ ] Readiness must show all providers mock/offline:

## Domain And CORS

- [ ] Backend preview URL:
- [ ] Frontend preview URL:
- [ ] CORS allowed origins configured:
- [ ] No public/beta domain enabled:
- [ ] Access restricted to approved operators:

## Logs And Monitoring

- [ ] Startup logs available:
- [ ] Request logs available:
- [ ] Provider diagnostics available:
- [ ] Retention window:
- [ ] Redaction behavior:
- [ ] Sentinel review approach:
- [ ] Evidence capture path:

## Rollback

- [ ] Rollback method:
- [ ] Previous revision/image:
- [ ] Shutdown command:
- [ ] Database rollback/reset method:
- [ ] Rollback owner:
- [ ] Rollback verification endpoint:

## Expected Offline Provider Posture

| Provider type | Expected provider | Expected mode | Real enabled | External calls allowed |
| --- | --- | --- | --- | --- |
| auth | dev/mock or approved offline auth | mock | false | false |
| llm | fake | mock | false | false |
| vector_db | fake | mock | false | false |
| poi_verification | mock | mock | false | false |
| routing | mock | mock | false | false |
| ticketing | mock | mock | false | false |
| affiliate | mock | mock | false | false |
| tts | mock | mock | false | false |

## Evidence Files To Fill After Rehearsal

- [ ] `docs/cloud-offline-deployment-rehearsal-record-template.md` copied or
      completed as a dated record.
- [ ] `docs/cloud-offline-deployment-checklist.md` completed.
- [ ] Sanitized logs summary added.
- [ ] No secrets, Authorization headers, or raw provider payloads included.

## Decision

- [ ] Target ready for mock-only cloud offline rehearsal.
- [ ] Target blocked; blockers listed:
- [ ] User approval recorded before execution:

