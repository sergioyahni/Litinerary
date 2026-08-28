# Cloud Offline Environment Template: Render

This template contains safe placeholders and mock/offline values only. It is
for a future manual Render cloud offline rehearsal. Do not store real secrets in
this file.

No `LLM_API_KEY` is required. No real provider credentials are allowed. If any
live provider credential is present in Render config, the rehearsal fails.

## Backend Web Service Values

```text
APP_ENV=development
PORT=<render-provided-port>
LOG_LEVEL=<render-log-level-placeholder>
CORS_ALLOWED_ORIGINS=<render-frontend-preview-origin-placeholder>
LITINERARY_DATABASE_URL=<render-postgres-internal-url-config-reference-only>

ENABLE_REAL_LLM=false
ALLOW_EXTERNAL_CALLS=false
ENABLE_STAGED_INTERNAL_LLM_TESTING=false
ENABLE_INTERNAL_ACCESS_GATE=false
ENABLE_MOCK_SERVICES=true
ENABLE_INTEGRATION_TESTS=false

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

ENABLE_REAL_VECTOR_DB=false
ENABLE_REAL_POI_PROVIDER=false
ENABLE_REAL_ROUTING=false
ENABLE_REAL_TICKETING=false
ENABLE_REAL_TTS=false
ENABLE_AFFILIATE_LINKS=false

ENABLE_AUTH=false
AUTH_PROVIDER=dev
AUTH_REQUIRED_FOR_USER_FEATURES=false
AUTH_ALLOW_DEV_USER_FALLBACK=false

BACKEND_URL=<render-backend-preview-url-placeholder>
FRONTEND_URL=<render-frontend-preview-url-placeholder>
```

## Frontend Static Site Values

```text
VITE_API_BASE_URL=<render-backend-preview-url-placeholder>
FRONTEND_URL=<render-frontend-preview-url-placeholder>
BACKEND_URL=<render-backend-preview-url-placeholder>
```

## Database Placeholder

Use a Render Postgres internal connection string or approved safe test database
URL only in Render service config:

```text
LITINERARY_DATABASE_URL=<render-postgres-internal-url-config-reference-only>
```

Do not paste the real database URL into docs, evidence, logs, screenshots, or
tracked files.

## Forbidden For This Rehearsal

This offline template intentionally uses `APP_ENV=development` because deployed
environment names (`internal`, `beta`, `staging`, and `production`) now fail
startup unless managed auth is configured. For any deployed-profile rehearsal,
replace the auth block with placeholder-only managed JWT settings in deployment
config, not in this tracked file.

Do not configure these keys with real values in this offline template:

```text
LLM_API_KEY
OPENAI_API_KEY
VECTOR_DB_API_KEY
VECTOR_DB_URL
QDRANT_API_KEY
QDRANT_URL
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

Forbidden values:

```text
ENABLE_REAL_LLM=true
ALLOW_EXTERNAL_CALLS=true
ENABLE_STAGED_INTERNAL_LLM_TESTING=true
ENABLE_INTERNAL_ACCESS_GATE=true
LLM_PROVIDER=openai_compatible
LITINERARY_AI_PROVIDER=openai_compatible
VECTOR_DB_PROVIDER=qdrant
POI_PROVIDER=google_places
ROUTING_PROVIDER=openrouteservice
AUTH_PROVIDER=oidc
```

If readiness shows any provider with `realEnabled=true`,
`externalCallsAllowed=true`, or a non-mock mode, the rehearsal fails.
