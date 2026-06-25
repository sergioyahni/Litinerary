# Cloud Offline Environment Template: `{{CLOUD_TARGET}}`

This template contains safe placeholders and mock/offline values only. Replace
`{{CLOUD_TARGET}}` after the target is approved. Do not store real secrets in
this file.

## Required Offline Values

```text
APP_ENV=<non-production-offline-env>
PORT=<platform-port-placeholder>
LOG_LEVEL=<platform-log-level-placeholder>
CORS_ALLOWED_ORIGINS=<frontend-preview-origin-placeholder>
LITINERARY_DATABASE_URL=<cloud-secret-or-config-reference-only>

ENABLE_REAL_LLM=false
ALLOW_EXTERNAL_CALLS=false
ENABLE_STAGED_INTERNAL_LLM_TESTING=false
ENABLE_INTERNAL_ACCESS_GATE=false
ENABLE_MOCK_SERVICES=true

LITINERARY_AI_PROVIDER=fake
LLM_PROVIDER=fake
LITINERARY_VECTOR_PROVIDER=fake
VECTOR_DB_PROVIDER=fake
LITINERARY_POI_VERIFICATION_PROVIDER=mock
POI_VERIFICATION_PROVIDER=mock
POI_PROVIDER=mock
ROUTING_PROVIDER=mock
TICKETING_PROVIDER=mock
AFFILIATE_PROVIDER=mock
TTS_PROVIDER=mock
PROVIDER_DAILY_COST_CEILING_USD=0

ENABLE_AUTH=false
AUTH_PROVIDER=dev
AUTH_ALLOW_DEV_USER_FALLBACK=false

BACKEND_URL=<backend-preview-url-placeholder>
FRONTEND_URL=<frontend-preview-url-placeholder>
```

## Forbidden For This Rehearsal

No `LLM_API_KEY` is required.

Do not configure:

```text
LLM_API_KEY
OPENAI_API_KEY
VECTOR_DB_API_KEY
QDRANT_API_KEY
POI_PROVIDER_API_KEY
GOOGLE_PLACES_API_KEY
POI_VERIFICATION_API_KEY
ROUTING_API_KEY
OPENROUTESERVICE_API_KEY
TICKETING_API_KEY
AFFILIATE_API_KEY
TTS_API_KEY
TEXT_TO_SPEECH_API_KEY
AUTH_JWT_ISSUER
AUTH_JWT_AUDIENCE
AUTH_JWKS_URL
AUTH_PROVIDER_METADATA_URL
```

If any live provider credential is present, the rehearsal fails. If readiness
shows any provider with `realEnabled=true`, `externalCallsAllowed=true`, or a
non-mock mode, the rehearsal fails.

