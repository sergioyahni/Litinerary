# Cloud Offline Environment Posture Template

Use this template to configure a non-production cloud offline rehearsal. Values
must remain mock/offline. Do not store real secrets in this file.

## Required Safe Values

```text
APP_ENV=development
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

LITINERARY_DATABASE_URL=<cloud-secret-or-config-reference-only>
CORS_ALLOWED_ORIGINS=<approved-non-production-origin-list>
LOG_LEVEL=<platform-log-level>
PORT=<platform-provided-port>
```

## Forbidden For Offline Rehearsal

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

No `LLM_API_KEY` is required for cloud offline rehearsal.

If any real provider credential is present, the rehearsal fails. If readiness
shows any provider with `realEnabled=true`, `externalCallsAllowed=true`, or a
non-mock mode, the rehearsal fails.

This offline template intentionally uses `APP_ENV=development` because deployed
environment names (`internal`, `beta`, `staging`, and `production`) now fail
startup unless managed auth is configured. For any deployed-profile rehearsal,
use placeholder-only managed JWT settings in deployment config.

## Notes

- Store the real database URL only in the selected cloud platform's secure
  configuration mechanism.
- Evidence must refer to config keys by name only, not values.
- Public/beta live generation remains blocked.
- Staged internal testing remains `No-go`.
