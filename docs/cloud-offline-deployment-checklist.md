# Cloud Offline Deployment Checklist

## Repository Cleanliness

- [ ] Working tree reviewed; unrelated dirty files understood.
- [ ] Commit SHA recorded.
- [ ] No local env file is tracked.
- [ ] No cloud secret is stored in the repository.

## Target Selection

- [ ] `docs/cloud-target-decision.md` reviewed.
- [ ] `{{CLOUD_TARGET}}` replaced with a concrete non-production cloud target.
- [ ] Final target choice approved by user.
- [ ] `docs/cloud-target-readiness-checklist.md` completed for target.
- [ ] `docs/cloud-offline-env-posture-template.md` mapped to platform config.
- [ ] Target-specific placeholder assets updated or copied for the concrete
      target:
      `docs/cloud-offline-deployment-cloud-target-placeholder.md`,
      `docs/cloud-offline-env-cloud-target-placeholder.template.md`,
      `docs/cloud-offline-checklist-cloud-target-placeholder.md`,
      and `docs/cloud-offline-rehearsal-record-cloud-target-placeholder.md`.
- [ ] Target supports health/readiness evidence.
- [ ] Target supports durable log/redaction evidence.
- [ ] Target supports rollback/shutdown evidence.
- [ ] Target rejected if any required evidence channel is unavailable.

## Tests And Harness Status

- [ ] Batch 4 deployment-readiness harness passed.
- [ ] Local offline deployment rehearsal passed.
- [ ] Backend tests status recorded.
- [ ] Frontend tests/typecheck/build status recorded.

## Build Artifacts

- [ ] Backend artifact prepared without live provider credentials.
- [ ] Frontend build artifact prepared.
- [ ] Artifact source commit recorded.

## Cloud Runtime Config

- [ ] Cloud target is non-production.
- [ ] `ENABLE_REAL_LLM=false`.
- [ ] `ALLOW_EXTERNAL_CALLS=false`.
- [ ] `ENABLE_STAGED_INTERNAL_LLM_TESTING=false`.
- [ ] LLM provider is fake/mock/offline.
- [ ] vector DB provider is fake/mock/offline.
- [ ] POI verification is seed/mock/offline.
- [ ] routing is mock/offline.
- [ ] ticketing is disabled/mock.
- [ ] affiliate is disabled/mock.
- [ ] TTS is disabled/mock.
- [ ] managed auth is disabled/mock unless separately approved.
- [ ] No `LLM_API_KEY` is configured.

## Database And Migrations

- [ ] Database target is non-production.
- [ ] Migration command recorded.
- [ ] Migration result passed.
- [ ] Rollback path for failed migration documented.

## Seed Data

- [ ] Seed command recorded.
- [ ] Seed validation passed.
- [ ] London seed data exists.
- [ ] Sherlock Holmes seed data exists.
- [ ] Baker Street seed data exists.
- [ ] Baker Street provenance and verification notes exist.

## Health And Readiness

- [ ] `/api/health` passed.
- [ ] `/api/readiness` passed.
- [ ] database readiness is `ok`.
- [ ] external calls are disabled.
- [ ] readiness output contains no secrets.
- [ ] readiness output contains no raw provider payload fields.

## Provider Posture

- [ ] all providers report `mode=mock`.
- [ ] all providers report `realEnabled=false`.
- [ ] all providers report `externalCallsAllowed=false`.
- [ ] no provider reports `openai_compatible`.
- [ ] no live non-LLM provider appears.

## Secret Hygiene

- [ ] repository/template scan passed.
- [ ] cloud runtime config checked without printing values.
- [ ] logs checked without printing values.
- [ ] no Authorization header captured.
- [ ] no raw provider payload captured.

## Logging And Redaction

- [ ] startup logs reviewed.
- [ ] health/readiness logs reviewed.
- [ ] seed/migration logs reviewed.
- [ ] mock generation logs reviewed.
- [ ] provider warning/diagnostic logs reviewed.
- [ ] retention setting recorded.
- [ ] redaction behavior passed.

## Rollback

- [ ] rollback target documented before rehearsal.
- [ ] rollback/shutdown command recorded.
- [ ] backend stopped or reverted.
- [ ] frontend preview stopped or reverted.
- [ ] no public/beta route left enabled.
- [ ] no live provider config left enabled.

## Evidence Capture

- [ ] evidence template completed.
- [ ] sanitized summaries only.
- [ ] no full raw response dumps.
- [ ] no secrets.
- [ ] blockers listed.
- [ ] next action listed.

## Go/No-Go Decision

- [ ] cloud offline rehearsal pass/fail verdict recorded.
- [ ] local live deployment remains blocked.
- [ ] staged internal testing remains `No-go`.
- [ ] public/beta live generation remains `No-go`.
