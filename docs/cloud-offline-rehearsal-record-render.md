# Cloud Offline Rehearsal Record: Render

## Metadata

- Date/time:
- Operator:
- Selected target: Render
- Render project/environment name:
- Backend service name:
- Frontend static site name:
- Commit SHA:
- Backend URL:
- Frontend URL:
- Database target:
- Database engine/version:

## Environment Posture Result

- `APP_ENV`:
- `ENABLE_REAL_LLM=false`:
- `ALLOW_EXTERNAL_CALLS=false`:
- `ENABLE_STAGED_INTERNAL_LLM_TESTING=false`:
- `ENABLE_INTERNAL_ACCESS_GATE=false`:
- `ENABLE_MOCK_SERVICES=true`:
- LLM provider fake/mock:
- non-LLM providers mock/offline:
- Auth disabled/mock:
- No `LLM_API_KEY` configured:
- No real provider credentials configured:
- Result:

## Migration Result

- Command:
- Result:
- Notes:

## Seed Result

- Command:
- Validation command or endpoint:
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
- Secret-like values exposed:
- Raw provider payload fields exposed:

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
- `/v1/chat/completions` called:
- Live provider request observed:
- Raw provider payload exposed:
- Secret-like values exposed:

## Logs And Redaction Result

- Render deploy logs reviewed:
- Backend startup logs reviewed:
- Health/readiness logs reviewed:
- Migration/seed logs reviewed:
- Mock generation logs reviewed:
- Rollback/redeploy or shutdown logs reviewed:
- Retention window:
- Authorization header present:
- Raw provider payload present:
- Secret-like value present:
- Database URL value present:
- Result:

## Rollback Result

- Backend rollback target:
- Frontend rollback target:
- Backend rollback/shutdown action:
- Frontend rollback/shutdown action:
- Database reset/delete action:
- Backend health after rollback:
- Frontend state after rollback:
- No public/beta route remains:
- No live provider config remains:
- Env posture reviewed after rollback:
- Result:

## Secret Hygiene Result

- Repository/template scan:
- Render runtime config review:
- Render log review:
- Evidence review:
- Result:

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
