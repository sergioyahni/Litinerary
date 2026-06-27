# Cloud Offline Checklist: Render

## Account And Project Setup

- [ ] Render account/team selected.
- [ ] Non-production Render project/environment selected.
- [ ] Operator approved.
- [ ] Access restricted to approved operators.
- [ ] No public/beta route enabled.
- [ ] No cloud deployment performed before approval to execute the rehearsal.
- [ ] No cloud resources created during asset preparation.

## Non-Production Environment

- [ ] Environment name recorded.
- [ ] Backend service name recorded.
- [ ] Frontend static site name recorded.
- [ ] Database name recorded.
- [ ] Region recorded.
- [ ] Runtime is non-production.
- [ ] Rollback/shutdown method exists.
- [ ] Render logs are available.

## Managed Database Or Safe Test DB

- [ ] Render Postgres or approved safe test DB selected.
- [ ] Database is non-production and disposable/resettable.
- [ ] Database URL stored only in Render config.
- [ ] Internal database URL preferred for backend service.
- [ ] Migration command recorded.
- [ ] Seed command recorded.
- [ ] Reset/delete approach documented.

## Backend Service Config

- [ ] Render Web Service selected.
- [ ] Root directory: `backend`.
- [ ] Build command: `pip install -r requirements.txt`.
- [ ] Start command:
      `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- [ ] Backend binds to Render-provided `PORT`.
- [ ] Health URL recorded.
- [ ] Readiness URL recorded.
- [ ] Backend artifact contains no live provider credentials.

## Frontend Service Or Static Hosting Config

- [ ] Render Static Site selected.
- [ ] Root directory: `frontend`.
- [ ] Build command: `npm ci && npm run build`.
- [ ] Publish directory: `dist`.
- [ ] `VITE_API_BASE_URL` points only to non-production backend.
- [ ] Frontend origin added exactly to backend CORS.
- [ ] Frontend preview URL recorded.

## Environment Variables

- [ ] `APP_ENV=<non-production-offline-env>`.
- [ ] `ENABLE_REAL_LLM=false`.
- [ ] `ALLOW_EXTERNAL_CALLS=false`.
- [ ] `ENABLE_STAGED_INTERNAL_LLM_TESTING=false`.
- [ ] `ENABLE_INTERNAL_ACCESS_GATE=false`.
- [ ] `ENABLE_MOCK_SERVICES=true`.
- [ ] `LITINERARY_AI_PROVIDER=fake`.
- [ ] `LLM_PROVIDER=fake`.
- [ ] `LITINERARY_VECTOR_PROVIDER=fake`.
- [ ] `VECTOR_DB_PROVIDER=fake`.
- [ ] `LITINERARY_POI_VERIFICATION_PROVIDER=mock`.
- [ ] `POI_VERIFICATION_PROVIDER=mock`.
- [ ] `POI_PROVIDER=mock`.
- [ ] `ROUTING_PROVIDER=mock`.
- [ ] `TICKETING_PROVIDER=mock`.
- [ ] `AFFILIATE_PROVIDER=mock`.
- [ ] `TTS_PROVIDER=mock`.
- [ ] `PROVIDER_DAILY_COST_CEILING_USD=0`.
- [ ] `ENABLE_AUTH=false`.
- [ ] `AUTH_PROVIDER=dev`.
- [ ] `AUTH_ALLOW_DEV_USER_FALLBACK=false`.

## Secret Posture

- [ ] No `LLM_API_KEY` configured.
- [ ] No `OPENAI_API_KEY` configured.
- [ ] No vector DB credential configured.
- [ ] No POI/Google Places credential configured.
- [ ] No routing credential configured.
- [ ] No ticketing, affiliate, or TTS credential configured.
- [ ] No managed auth issuer/audience/JWKS/provider metadata configured.
- [ ] Runtime config reviewed without printing secret values.
- [ ] Evidence contains config key names only, not values.

## Migration And Seed

- [ ] Database target confirmed non-production.
- [ ] `python -m alembic upgrade head` passed.
- [ ] `python -m scripts.seed_database` passed.
- [ ] `python -m scripts.validate_seed_data` or
      `GET /api/admin/seed/validate` passed.
- [ ] London seed exists.
- [ ] Sherlock Holmes seed exists.
- [ ] Baker Street seed exists.
- [ ] Baker Street provenance and verification notes exist.

## Health And Readiness

- [ ] `GET /api/health` returned `status=ok`.
- [ ] `GET /api/readiness` returned `status=ready`.
- [ ] Database readiness is `ok`.
- [ ] External calls are disabled.
- [ ] All providers are mock/offline.
- [ ] No secrets or raw provider payload fields appear.

## Mock Itinerary Generation

- [ ] Scenario: `london / sherlock-holmes / 1 day / walking`.
- [ ] Result passed.
- [ ] Generated title recorded.
- [ ] Provider is `mock_ai`.
- [ ] Provider is not `openai_compatible`.
- [ ] Routing provider is `mock_routing`.
- [ ] Baker Street appears.
- [ ] No `/v1/chat/completions` request occurred.
- [ ] No live provider request occurred.

## Log Redaction And Retention

- [ ] Render deploy logs reviewed.
- [ ] Render backend startup logs reviewed.
- [ ] Health/readiness logs reviewed.
- [ ] Migration/seed logs reviewed.
- [ ] Mock generation logs reviewed.
- [ ] Rollback/redeploy or shutdown logs reviewed.
- [ ] Retention window recorded.
- [ ] No API keys found.
- [ ] No Authorization headers found.
- [ ] No raw provider payloads found.
- [ ] No database URL values found.

## Rollback

- [ ] Backend rollback target recorded before rehearsal.
- [ ] Frontend rollback target recorded before rehearsal.
- [ ] Render rollback/redeploy method recorded.
- [ ] Shutdown method recorded if no prior deploy exists.
- [ ] Database reset/delete path recorded.
- [ ] Backend health unavailable or points to intended rollback revision.
- [ ] Frontend no longer points at unintended backend.
- [ ] No public/beta route remains.
- [ ] No live provider config remains.
- [ ] Env posture reviewed after rollback because deploy rollback does not prove
      env var rollback.

## Evidence Recording

- [ ] `docs/cloud-offline-rehearsal-record-render.md` completed.
- [ ] Sanitized summaries only.
- [ ] No full raw response dumps.
- [ ] No secrets.
- [ ] No raw provider payloads.
- [ ] Blockers listed.
- [ ] Next action listed.

## Go/No-Go Decision

- [ ] Cloud offline rehearsal pass/fail verdict recorded.
- [ ] Local live deployment remains blocked.
- [ ] Staged internal testing remains `No-go`.
- [ ] Public/beta live generation remains `No-go`.
- [ ] Next exact action recorded.
