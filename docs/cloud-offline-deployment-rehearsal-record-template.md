# Cloud Offline Deployment Rehearsal Record

## Metadata

- Date/time:
- Operator:
- Cloud provider:
- Cloud project/account:
- Cloud target/environment:
- Backend service:
- Frontend service:
- Database instance:
- Log sink:
- Commit SHA:

## Deployment-Readiness Harness

- Command:
- Result:
- Notes:

## Build Results

- Backend artifact result:
- Frontend build command:
- Frontend build result:
- Artifact source commit:

## Migration Result

- Database confirmed non-production:
- Migration command:
- Migration result:
- Notes:

## Seed Result

- Seed command:
- Seed result:
- Seed validation result:
- Destination count:
- Book count:
- POI count:
- Itinerary count:
- London/Sherlock Holmes/Baker Street confirmed:
- Baker Street provenance/verification notes confirmed:

## Health Result

- Health endpoint:
- Result:
- Observed status:

## Readiness Result

- Readiness endpoint:
- Result:
- Observed status:
- Database status:
- External calls allowed:
- Staged/internal live LLM enabled:

## Provider Posture

| Provider type | Expected | Observed provider | Observed mode | Real enabled | External calls allowed |
| --- | --- | --- | --- | --- | --- |
| auth | dev/mock or approved offline auth | | | | |
| llm | fake/mock | | | | |
| vector_db | fake/mock | | | | |
| poi_verification | mock | | | | |
| routing | mock | | | | |
| ticketing | mock/disabled | | | | |
| affiliate | mock/disabled | | | | |
| tts | mock/disabled | | | | |

## Mock Itinerary-Generation Result

- Request scenario: `london / sherlock-holmes / 1 day / walking`
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
- Seed/migration logs reviewed:
- Mock generation logs reviewed:
- Provider diagnostics reviewed:
- Retention setting:
- Redaction result:
- Raw provider payload present:
- Authorization header present:
- Secret-like value present:

## Rollback Result

- Rollback target documented before rehearsal:
- Rollback/shutdown command:
- Backend stopped or reverted:
- Frontend stopped or reverted:
- Public/beta route left enabled:
- Live provider config left enabled:
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

- Live LLM request made:
- `/v1/chat/completions` called:
- External providers enabled:
- Real `LLM_API_KEY` required:
- Staged internal testing approved:
- Public/beta live generation approved:
