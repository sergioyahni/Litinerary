# Cloud Offline Rehearsal Record: `{{CLOUD_TARGET}}`

## Metadata

- Date/time:
- Operator:
- Selected target: `{{CLOUD_TARGET}}`
- Project/environment name:
- Commit SHA:
- Backend URL:
- Frontend URL:
- Database target:

## Environment Posture Result

- `ENABLE_REAL_LLM=false`:
- `ALLOW_EXTERNAL_CALLS=false`:
- `ENABLE_STAGED_INTERNAL_LLM_TESTING=false`:
- LLM provider fake/mock:
- non-LLM providers mock/offline:
- No `LLM_API_KEY` configured:
- Result:

## Migration Result

- Command:
- Result:
- Notes:

## Seed Result

- Command:
- Validation endpoint:
- Result:
- Counts:
- London/Sherlock Holmes/Baker Street confirmed:
- Baker Street provenance/verification notes confirmed:

## Health Result

- Endpoint:
- Result:
- Observed status:

## Readiness Result

- Endpoint:
- Result:
- Observed status:
- Database status:
- External calls allowed:

## Provider Posture Result

| Provider type | Observed provider | Observed mode | Real enabled | External calls allowed |
| --- | --- | --- | --- | --- |
| auth | | | | |
| llm | | | | |
| vector_db | | | | |
| poi_verification | | | | |
| routing | | | | |
| ticketing | | | | |
| affiliate | | | | |
| tts | | | | |

## Mock Itinerary Generation Result

- Scenario: `london / sherlock-holmes / 1 day / walking`
- Result:
- Generated title:
- LLM provider:
- Routing provider:
- Baker Street present:
- Raw provider payload exposed:
- Secret-like values exposed:

## Logs And Redaction Result

- Startup logs reviewed:
- Health/readiness logs reviewed:
- Migration/seed logs reviewed:
- Mock generation logs reviewed:
- Retention window:
- Authorization header present:
- Raw provider payload present:
- Secret-like value present:
- Result:

## Rollback Result

- Rollback target:
- Backend rollback/shutdown command:
- Frontend rollback/shutdown command:
- Database reset/delete action:
- No public/beta route remains:
- No live provider config remains:
- Result:

## Secret Hygiene Result

- Repository/template scan:
- Cloud runtime config review:
- Log review:
- Evidence review:

## Verdict

- Pass/fail verdict:
- Blockers:
- Limitations:
- Next action:

## Safety Confirmation

- Cloud deployment performed:
- Cloud resources created:
- Live LLM request made:
- `/v1/chat/completions` called:
- External providers enabled:
- Secrets/raw provider payloads added:
- Staged internal testing approved:
- Public/beta live generation approved:

