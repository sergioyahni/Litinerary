# Cloud Offline Checklist: `{{CLOUD_TARGET}}`

## Account And Project Setup

- [ ] `{{CLOUD_TARGET}}` replaced with an approved target.
- [ ] Non-production account/project selected.
- [ ] Operator approved.
- [ ] Access restricted to approved operators.
- [ ] No public/beta route enabled.

## Non-Production Environment

- [ ] Environment name recorded.
- [ ] Runtime is non-production.
- [ ] Database is non-production.
- [ ] Rollback/shutdown method exists.
- [ ] Durable logs are available.

## Database

- [ ] Managed database or safe test DB selected.
- [ ] Database URL stored only in secure platform config.
- [ ] Migration command recorded.
- [ ] Seed command recorded.
- [ ] Seed validation endpoint available.
- [ ] Reset/delete approach documented.

## Backend Service Config

- [ ] Backend runtime supports Python app startup.
- [ ] Start command recorded.
- [ ] Backend binds to platform port.
- [ ] Health URL recorded.
- [ ] Readiness URL recorded.
- [ ] Backend artifact contains no live provider credentials.

## Frontend Service Or Static Hosting

- [ ] Frontend build command recorded.
- [ ] Static hosting or preview runtime selected.
- [ ] Frontend URL recorded.
- [ ] Frontend points only to non-production backend.
- [ ] CORS origin configured for preview URL.

## Environment Variables

- [ ] `APP_ENV=<non-production-offline-env>`.
- [ ] `ENABLE_REAL_LLM=false`.
- [ ] `ALLOW_EXTERNAL_CALLS=false`.
- [ ] `ENABLE_STAGED_INTERNAL_LLM_TESTING=false`.
- [ ] `ENABLE_INTERNAL_ACCESS_GATE=false`.
- [ ] `LITINERARY_AI_PROVIDER=fake`.
- [ ] `LLM_PROVIDER=fake`.
- [ ] `LITINERARY_VECTOR_PROVIDER=fake`.
- [ ] `VECTOR_DB_PROVIDER=fake`.
- [ ] `POI_VERIFICATION_PROVIDER=mock`.
- [ ] `ROUTING_PROVIDER=mock`.
- [ ] `TICKETING_PROVIDER=mock`.
- [ ] `AFFILIATE_PROVIDER=mock`.
- [ ] `TTS_PROVIDER=mock`.
- [ ] `PROVIDER_DAILY_COST_CEILING_USD=0`.

## Secret Posture

- [ ] No `LLM_API_KEY` configured.
- [ ] No OpenAI-compatible key configured.
- [ ] No routing/POI/vector/ticketing/affiliate/TTS credentials configured.
- [ ] No managed auth secrets configured.
- [ ] Runtime config reviewed without printing secret values.

## Migration And Seed

- [ ] `python -m alembic upgrade head` passed.
- [ ] `python -m scripts.seed_database` passed.
- [ ] `GET /api/admin/seed/validate` passed.
- [ ] London seed exists.
- [ ] Sherlock Holmes seed exists.
- [ ] Baker Street seed exists with provenance/verification notes.

## Health And Readiness

- [ ] `GET /api/health` returned `status=ok`.
- [ ] `GET /api/readiness` returned `status=ready`.
- [ ] Database readiness is `ok`.
- [ ] External calls are disabled.
- [ ] No secrets or raw provider payload fields appear.

## Mock Itinerary Generation

- [ ] Scenario: `london / sherlock-holmes / 1 day / walking`.
- [ ] Generated title recorded.
- [ ] Provider is `mock_ai`.
- [ ] Provider is not `openai_compatible`.
- [ ] Routing provider is `mock_routing`.
- [ ] Baker Street appears.
- [ ] No live request occurred.

## Log Redaction And Retention

- [ ] Startup logs reviewed.
- [ ] Health/readiness logs reviewed.
- [ ] Migration/seed logs reviewed.
- [ ] Mock generation logs reviewed.
- [ ] Retention window recorded.
- [ ] No API keys found.
- [ ] No Authorization headers found.
- [ ] No raw provider payloads found.

## Rollback

- [ ] Rollback target recorded before rehearsal.
- [ ] Backend rollback/shutdown command recorded.
- [ ] Frontend rollback/shutdown command recorded.
- [ ] Database reset/delete path recorded.
- [ ] No public/beta route remains.
- [ ] No live provider config remains.

## Evidence Recording

- [ ] `docs/cloud-offline-rehearsal-record-cloud-target-placeholder.md` filled.
- [ ] Sanitized summaries only.
- [ ] No full raw response dumps.
- [ ] No secrets.
- [ ] Blockers listed.

## Go/No-Go Decision

- [ ] Cloud offline rehearsal pass/fail verdict recorded.
- [ ] Local live deployment remains blocked.
- [ ] Staged internal testing remains `No-go`.
- [ ] Public/beta live generation remains `No-go`.

