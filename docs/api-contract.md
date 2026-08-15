# Litinerary API Contract

Current scope: Phase 1 MVP plus Phase 2 foundations. Public endpoints are user-facing. Admin endpoints are development-only scaffolding and are not production admin APIs.

Base URL in local development: `http://127.0.0.1:8000`

All API responses include an `X-Request-ID` response header. Clients may provide `X-Request-ID`; otherwise the backend generates one. Request IDs are safe correlation values and must not contain secrets.

## Naming Conventions

- Public JSON fields use camelCase.
- Query parameters currently use snake_case where already implemented: `city_id`, `book_id`, `transportation_mode`.
- `destinationId` is the canonical response/body field for city or destination IDs.
- IDs:
  - `bookId`
  - `destinationId`
  - `itineraryId`
  - `poiId`
  - `userId`
- `transportationMode`: `walking`, `public_transport`, `car_taxi`.
- `sourceType`: `exact_match`, `adapted_match`, `new_mock_generation`.
- `generatedFrom`: `mock`, `exact_match`, `adapted`, `new_generation`.
- `verificationStatus`: `mock`, `verified`, `unverified`, `mock_verified`, `provider_verified`, `needs_review`, `rejected`.

Common errors:

- `401`: `{"detail": "Authentication is required."}` or another auth-specific detail when auth is enabled.
- `403`: `{"detail": "You do not have access to this user's resources."}` or another authorization-specific detail.
- `404`: `{"detail": "Unknown <resource>: <id>"}`
- `400`: `{"detail": "<validation message>"}`
- `409`: `{"detail": "<conflict message>"}`
- `422`: FastAPI request validation error.
- `429`: provider-neutral limit failures such as `{"detail": {"code": "rate_limited", "message": "...", "metadata": {...}}}` or `quota_exceeded`. Responses include `Retry-After` when the failing minute/day window is known.
- `413`: provider-neutral input-size failures such as `{"detail": {"code": "input_too_large", "message": "...", "metadata": {...}}}`.
- `503`: provider dependency unavailable, including fail-closed durable usage limiter failures.
- `500`: judge rejection may return `{"detail": {"message": "...", "reasons": [...], "warnings": [...], "confidenceScore": 0.2, "requiredFixes": [...]}}`.

Limit-related provider errors use `detail.code` values including `rate_limited`, `quota_exceeded`, `input_too_large`, `unsupported_batch_size`, `too_many_stops`, and `cost_limit_exceeded`. Frontend clients should display `detail.message`; frontend `ApiError` also exposes `isRateLimited` and `retryAfterSeconds`.

## Core Schemas

`Destination`: `id`, `name`, `country`, `region`, `description`, `latitude`, `longitude`, `imageUrl`, `supported`.

`Book`: `id`, `destinationIds`, `title`, `author`, `description`, `publicationYear`, `publicDomain`, `themes`, `coverUrl`, and optional `affiliateLinks`.

`AffiliateLink`: `title`, `sourceUrl`, `providerName`, `providerType`, `affiliate`, `lastCheckedAt`, `relevanceScore`. Current local/mock responses default `affiliateLinks` to an empty list; no checkout, payment, cart, or e-commerce transaction is implemented.

`POI`: `id`, `destinationId`, `bookIds`, `name`, `description`, `latitude`, `longitude`, `address`, `estimatedDurationMinutes`, `ticketingNote`, `literaryRelevance`, `verificationStatus`, plus optional verification/provenance metadata: `verificationProvider`, `providerVersion`, `providerRequestId`, `verificationConfidence`, `verifiedName`, `verifiedAddress`, `verifiedLatitude`, `verifiedLongitude`, `openingHoursNote`, `ticketingUrl`, `verificationNotes`, `lastVerifiedAt`, `manualReviewStatus`, `reviewedByUserId`, `provenanceMetadata`. `ticketingUrl` is optional logistics information only and must not be treated as checkout.

`ItineraryDay`: `id`, `dayNumber`, `title`, `summary`, `stops`, `estimatedDistanceKm`, `estimatedDurationHours`, plus optional routing metadata: `routeGeometry` as `[latitude, longitude]` coordinate pairs, `routingProviderMetadata`, and `routingWarnings`.

`Itinerary`: `id`, `destinationId`, `bookId`, `title`, `summary`, `durationDays`, `transportationMode`, `days`, `isPublic`, `ownerUserId`, `visibility`, `generatedFrom`, `sourceType`, `sourceItineraryId`, `createdByMode`, `createdByUserId`, `subscriberOnly`, `adaptationNotes`, `createdAt`, `updatedAt`, plus optional provider provenance: `providerName`, `providerType`, `providerVersion`, `providerRequestId`, `generatedByService`, `confidenceScore`, `provenanceMetadata`.

`NarrationRequest`: optional `voiceStyle`, optional `includePlaceholderAudio`.

`ItineraryNarrationResponse`: `itineraryId`, `script`, `audio`, `format`.

`NarrationScriptResponse`: `itineraryId`, `title`, `text`, `estimatedDurationSeconds`, provider provenance fields, `provenanceMetadata`.

`AudioMetadataResponse`: `available`, `url`, `format`, `durationSeconds`, `providerName`, `providerType`, `providerVersion`, `placeholder`, `warnings`. Current mock responses never serve generated audio files; `url` remains null.

Public repository endpoints return only itineraries where `isPublic=true` and
`visibility="public"`. Private and unlisted itineraries are not listed publicly.
The shared itinerary detail/narration endpoints return private or unlisted
itineraries only to their verified owner or an admin. Missing IDs and
unauthorized private IDs both use `404` to avoid exposing private itinerary
existence. Until a dedicated sharing feature exists, `visibility="unlisted"` is
treated like private.

## Public Endpoints

### Health

`GET /api/health`

Purpose: service health check.

Response:

```json
{"status": "ok"}
```

Audience: user-facing/dev.

### Readiness

`GET /api/readiness`

Purpose: beta-readiness check for database configuration, connectivity,
Alembic migration state, provider configuration mode, external-call policy,
mock-service mode, and durable usage controls.

Response:

```json
{
  "status": "ready",
  "appEnv": "development",
  "checks": {
    "database": {
      "status": "ok",
      "required": false,
      "configured": true,
      "dialect": "sqlite",
      "connectivity": "ok",
      "configurationErrors": [],
      "migrations": {
        "status": "current",
        "currentRevisions": ["20260815_0009"],
        "expectedHeads": ["20260815_0009"]
      }
    },
    "providers": [
      {
        "providerType": "llm",
        "providerName": "fake",
        "mode": "mock",
        "realEnabled": false,
        "credentialsConfigured": false,
        "externalCallsAllowed": false,
        "status": "mock"
      }
    ],
    "externalCalls": {"allowed": false, "integrationTestsEnabled": false},
    "mockServices": {"enabled": true},
    "usageControls": {
      "durable": false,
      "anonymousItineraryGenerationsPerMinute": 10,
      "anonymousItineraryGenerationsPerDay": 100,
      "registeredUserItineraryGenerationsPerMinute": 30,
      "registeredUserItineraryGenerationsPerDay": 250,
      "subscriberChatMessagesPerMinute": 60,
      "subscriberChatMessagesPerDay": 250,
      "providerDailyRequestCeiling": 1000,
      "providerDailyCostCeilingUsd": 0,
      "counterRetentionDays": 90
    }
  }
}
```

`GET /api/health` remains a minimal liveness endpoint and does not assert
database migration readiness. In deployed environments (`internal`, `beta`,
`staging`, and `production`), `GET /api/readiness` reports `status="ready"` only
when `LITINERARY_DATABASE_URL` is explicitly configured, the database is
reachable, and the `alembic_version` table is at the repository migration head.
Missing migration metadata, old revisions, unknown revisions, or connectivity
failure return a non-ready status. Local development and standard tests may use
SQLite fallback databases; deployed profiles must not silently fall back to the
default local SQLite URL.

Readiness responses expose credential presence as booleans and database
metadata as safe labels only. They must not include API keys, tokens, database
URLs, raw provider config values, prompts, copyrighted input, or user payloads.

Audience: operational/dev.

### Destinations

`GET /api/destinations`

Purpose: list supported destinations.

Response: `Destination[]`.

Errors: none expected in normal operation.

Audience: user-facing.

### Books

`GET /api/books?city_id={destinationId}`

Purpose: list books, optionally filtered by destination.

Parameters:

- `city_id` optional destination ID. This is retained for current frontend compatibility; response fields use `destinationId`/`destinationIds`.

Response: `Book[]`.

Errors:

- `404` unknown destination when `city_id` is supplied.

Audience: user-facing.

### Generate Itinerary

`POST /api/itinerary/generate`

Purpose: find an exact public itinerary, adapt a partial public match, or generate a deterministic mock itinerary.

Authentication: anonymous/public.

Ownership and visibility: generated repository itineraries are public
(`isPublic=true`, `visibility="public"`) and ownerless. Ownership fields such as
`ownerUserId`, `user_id`, and `createdByUserId` are not part of the request
contract and do not assign ownership.

Request body:

```json
{
  "destinationId": "london",
  "bookId": "oliver-twist",
  "durationDays": 1,
  "transportationMode": "walking"
}
```

Response: `ItineraryGenerationResponse`

- `itinerary`: `Itinerary`
- `matchedExisting`: boolean
- `sourceItineraryId`: string or null
- `message`: string

Errors:

- `400` book is not available for destination.
- `404` unknown destination/book or no local POIs for generation.
- `422` invalid request body.
- `500` judge rejected a generated/adapted candidate. Rejection details include `reasons`, `warnings`, `confidenceScore`, and `requiredFixes`.

Audience: user-facing.

Generated and adapted itineraries may include day-level routing metadata. By default, route geometry is mock straight-line geometry. With `ENABLE_REAL_ROUTING=true` and `ROUTING_PROVIDER=openrouteservice`, walking and car/taxi routes can include normalized OpenRouteService geometry. Public transportation uses mock fallback or a clear routing provider error depending on `ROUTING_FALLBACK_BEHAVIOR`.

### List Public Itineraries

`GET /api/itineraries?city_id={destinationId}&book_id={bookId}&transportation_mode={mode}`

Purpose: search/browse public itinerary repository.

Authentication: anonymous/public.

Authorization and visibility: returns public repository itineraries only.
Private and unlisted rows are excluded.

Parameters:

- `city_id` optional destination ID.
- `book_id` optional book ID.
- `transportation_mode` optional `TransportationMode`.

Response: `Itinerary[]`.

Errors:

- `404` unknown destination or book filter.
- `422` invalid transportation mode.

Audience: user-facing.

### Itinerary Detail

`GET /api/itineraries/{itinerary_id}`

Purpose: fetch one public itinerary by ID, or fetch a private/unlisted itinerary
when the request carries a verified owner/admin identity.

Authentication: anonymous for public itineraries; bearer token required for
private or unlisted owner/admin access.

Authorization and visibility:

- public itinerary: anyone may read;
- private or unlisted itinerary: owner or admin only;
- unauthorized private/unlisted access returns `404`.

Response: `Itinerary`.

Errors:

- `404` unknown itinerary.
- `404` private or unlisted itinerary not accessible to the caller.
- `401` malformed/invalid bearer token when one is supplied.

Audience: user-facing.

### Itinerary Narration

`GET /api/itineraries/{itinerary_id}/narration`

Purpose: return provider-neutral narration for an itinerary. This is deterministic mock/local behavior and is safe to call without prior generation.

Authentication and authorization: same as itinerary detail. Public itinerary
narration remains anonymous. Private/unlisted narration is owner/admin only.

Response: `ItineraryNarrationResponse`.

`POST /api/itineraries/{itinerary_id}/narration`

Purpose: generate narration with request options. The current mock implementation supports text narration and placeholder audio metadata only.

Request body:

```json
{
  "voiceStyle": "warm_literary",
  "includePlaceholderAudio": false
}
```

Response:

```json
{
  "itineraryId": "it-london-oliver-twist-1-walking",
  "script": {
    "itineraryId": "it-london-oliver-twist-1-walking",
    "title": "Narration for Oliver Twist in London",
    "text": "Oliver Twist in London...",
    "estimatedDurationSeconds": 72,
    "providerName": "mock_tts",
    "providerType": "tts",
    "providerVersion": "local-mock",
    "providerRequestId": "mock-...",
    "provenanceMetadata": {}
  },
  "audio": {
    "available": false,
    "url": null,
    "format": null,
    "durationSeconds": 72,
    "providerName": "mock_tts",
    "providerType": "tts",
    "providerVersion": "local-mock",
    "placeholder": true,
    "warnings": ["Real text-to-speech is disabled; text narration is available."]
  },
  "format": "text_only"
}
```

Errors:

- `404` unknown itinerary.
- `404` private or unlisted itinerary not accessible to the caller.
- `401` malformed/invalid bearer token when one is supplied.
- `422` invalid request body.

Audience: user-facing. Text fallback should remain available even when audio is unavailable.

### Adapt Itinerary

`POST /api/itineraries/adapt`

Purpose: adapt an existing public itinerary to a requested duration and transportation mode.

Authentication: anonymous/public.

Authorization and visibility: only public repository source itineraries can be
adapted through this endpoint. Private and unlisted source IDs return `404`,
even for the owner, until a dedicated private edit/adaptation workflow exists.

Request body:

```json
{
  "sourceItineraryId": "it-london-oliver-twist-1-walking",
  "durationDays": 2,
  "transportationMode": "public_transport"
}
```

Response: `ItineraryGenerationResponse`.

Errors:

- `404` unknown source itinerary.
- `422` invalid request body.
- `500` judge rejection with structured reasons, warnings, confidence, and required fixes.

Audience: user-facing.

## User Endpoints

Auth mode: auth is disabled by default in local development/test, so public catalog, public repository, narration, adaptation, and basic generation remain anonymous. In deployed environments (`internal`, `beta`, `staging`, and `production`), startup requires managed JWT auth configuration and user endpoints require `Authorization: Bearer <token>`.

Local/test development can use the mock token format:

```text
dev:<user_id>:<comma-separated-roles>:<subscription_status>
```

Development tokens and missing-token fallback are rejected in internal/beta/staging/production. Managed providers use the same backend auth boundary and validate JWT issuer, audience, accepted algorithms, signature, expiration, and claims using `AUTH_JWKS_URL` or `AUTH_PROVIDER_METADATA_URL`. Claims map through `AUTH_USER_ID_CLAIM`, `AUTH_ROLES_CLAIM`, `AUTH_SUBSCRIPTION_CLAIM`, `AUTH_EMAIL_CLAIM`, and `AUTH_DISPLAY_NAME_CLAIM`.

Deployed startup requires `ENABLE_AUTH=true`, a non-`dev` `AUTH_PROVIDER`, issuer, audience, production algorithms, JWKS or provider metadata, `AUTH_REQUIRED_FOR_USER_FEATURES=true`, `AUTH_ALLOW_DEV_USER_FALLBACK=false`, `ALLOW_EXTERNAL_CALLS=true`, and the current `APP_ENV` in `EXTERNAL_CALL_ALLOWED_ENVIRONMENTS`.

### Current User

`GET /api/me`

Purpose: validate the bearer token and sync the provider subject to a local user profile.

Response: `UserProfile`, including `id`, optional `email`, optional `displayName`, `role`, `subscriptionStatus`, and optional `authProvider`.

Errors:

- `401` missing, expired, invalid issuer, invalid audience, invalid signature, or unsupported development token.

Audience: authenticated user-facing account foundation.

### Create User

`POST /api/users`

Request: `UserCreateRequest`

```json
{"id": "dev-reader", "email": "reader@example.test", "displayName": "Reader"}
```

Response: `UserProfile`, including `role`, `subscriptionStatus`, optional `authProvider`, and `updatedAt`.

Errors:

- `409` user already exists.

Audience: authenticated user-facing account foundation in deployed environments; development account foundation locally.

### Get User

`GET /api/users/{user_id}`

Response: `UserProfile`.

Errors:

- `404` unknown user.

Audience: development user-facing account foundation.

### Save Preference

`POST /api/users/{user_id}/preferences`

Purpose: upsert one preference and mirror it into fake vector storage.

Request:

```json
{"key": "travel", "value": {"pace": "slow", "cityId": "london"}}
```

Response: `UserPreference`.

Errors:

- `404` unknown user.
- `422` invalid body.

Audience: development user-facing account foundation.

### Bookmark Itinerary

`POST /api/users/{user_id}/bookmarks/{itinerary_id}`

Purpose: add itinerary bookmark.

Authorization: the `{user_id}` path is owner/admin guarded when auth is enabled
or in deployed environments. The target itinerary must be public or accessible
to the verified owner/admin. A client-controlled user ID or itinerary ID is not
sufficient to bookmark another user's private itinerary.

Response: `UserBookmarksResponse` with `userId` and `itineraries`.

Errors:

- `404` unknown user or itinerary.
- `404` private or unlisted itinerary not accessible to the caller.

Audience: development user-facing account foundation.

### Remove Bookmark

`DELETE /api/users/{user_id}/bookmarks/{itinerary_id}`

Purpose: remove itinerary bookmark.

Authorization: owner/admin guarded for the bookmark collection. Removing a
bookmark mutates only that user's bookmark collection and does not expose
private itinerary details.

Response: `UserBookmarksResponse`.

Authorization and visibility: owner/admin guarded for `{user_id}`. Returned
itineraries are filtered to public rows plus private/unlisted rows accessible to
the verified current user/admin, so stale cross-user private bookmarks are not
returned.

Errors:

- `404` unknown user.

Audience: development user-facing account foundation.

### List Bookmarks

`GET /api/users/{user_id}/bookmarks`

Response: `UserBookmarksResponse`.

Errors:

- `404` unknown user.

Audience: development user-facing account foundation.

### Save Review

`POST /api/users/{user_id}/reviews`

Purpose: save itinerary review and mirror it into fake vector/mock AI feedback layers.

Authorization: owner/admin guarded for `{user_id}`. The reviewed itinerary must
be public or accessible to the verified owner/admin. A caller cannot review
another user's private itinerary by supplying its ID.

Request:

```json
{"itineraryId": "it-london-oliver-twist-1-walking", "rating": 5, "comment": "Great route."}
```

Response: `UserReview`.

Errors:

- `404` unknown user or itinerary.
- `404` private or unlisted itinerary not accessible to the caller.
- `422` invalid rating/body.

Audience: development user-facing account foundation.

### List Reviews

`GET /api/users/{user_id}/reviews`

Response: `UserReview[]`.

Errors:

- `404` unknown user.

Audience: development user-facing account foundation.

### Mock Recommendations

`GET /api/users/{user_id}/recommendations/mock?limit=5`

Purpose: development-only fake vector recommendations from preferences and positive reviews.

Response:

```json
{
  "developmentOnly": true,
  "userId": "dev-reader",
  "itinerariesFromPreferences": [],
  "itinerariesFromPositiveReviews": [],
  "poisFromInterests": []
}
```

Errors:

- `404` unknown user.

Audience: development/admin-only.

## Subscriber Chat Endpoints

Subscriber chat uses mock AI only. No real LLM provider, payment, billing, or subscription purchase flow is implemented. Endpoints require `require_subscriber_user`; with development auth this means a token such as:

```text
dev:dev-subscriber:user,subscriber:active
```

Regular users receive `403`; unauthenticated requests receive `401` when development fallback is disabled.

`ChatSession`: `id`, `userId`, `title`, `status`, `createdAt`, `updatedAt`, provider provenance fields, `provenanceMetadata`, `messages`, and `itineraryReferences`.

`ChatMessage`: `id`, `sessionId`, `role` (`user`, `assistant`, `system`), `content`, `createdAt`, provider provenance fields, and `provenanceMetadata`.

`ChatItineraryReference`: `id`, `sessionId`, `itineraryId`, `sourceItineraryId`, `refinementPrompt`, `createdAt`, provider provenance fields, `confidenceScore`, and `provenanceMetadata`.

### Create Chat Session

`POST /api/subscribers/chat/sessions`

Request:

```json
{"title": "Dickens refinement"}
```

Response: `ChatSession` with an initial mock assistant welcome message.

### List Chat Sessions

`GET /api/subscribers/chat/sessions`

Response: `ChatSession[]` for the current subscriber only.

### Get Chat Session

`GET /api/subscribers/chat/sessions/{session_id}`

Response: `ChatSession`.

Errors:

- `404` unknown chat session or session owned by another user.

### Add Chat Message

`POST /api/subscribers/chat/sessions/{session_id}/messages`

Request:

```json
{"content": "Make this slower and add more context."}
```

Response: `ChatMessageResponse` with the updated session and the user/assistant messages added by this request.

### Refine Itinerary From Chat

`POST /api/subscribers/chat/sessions/{session_id}/refine-itinerary`

Request:

```json
{
  "sourceItineraryId": "it-london-oliver-twist-1-walking",
  "prompt": "Prefer a quieter afternoon route.",
  "durationDays": 1,
  "transportationMode": "walking"
}
```

Response: `ChatItineraryRefinementResponse` with the updated chat session, private subscriber-only itinerary, itinerary reference, and assistant message. Refined itineraries are saved with `isPublic=false`, `visibility="private"`, `createdByMode="subscriber"`, and `subscriberOnly=true`.

## Admin/Development Ingestion Endpoints

`BookSourceType`: `public_domain_text_reference`, `summary_document`, `manually_curated_location_list`, `metadata_only`.

Book sources also carry copyright-safety fields: `sourceLicense`, `copyrightStatus` (`public_domain`, `copyrighted`, `unknown`, `metadata_only`), `allowedProcessingMode` (`full_text`, `summary_only`, `metadata_only`, `manual_curation`), and `sourceNotes`.

`BookIngestionStatus`: `pending`, `processing`, `completed`, `failed`.

`BookLocationCandidateStatus`: `candidate`, `approved`, `promoted`, `rejected`.

### Create Ingestion Job

`POST /api/admin/ingestion/jobs`

Request: `BookIngestionJobCreate`

```json
{
  "bookId": "oliver-twist",
  "source": {
    "sourceType": "metadata_only",
    "title": "Safe source note",
    "referenceUrl": null,
    "metadata": {}
  }
}
```

Response: `BookIngestionJob`.

Processing artifacts include provider-neutral provenance fields: `providerName`, `providerType`, `providerVersion`, `providerRequestId`, `confidenceScore`, and `provenanceMetadata`. Current mock artifacts and future LLM artifacts must not include raw provider payloads, prompts, secrets, or full copyrighted text.

Errors:

- `400` unsafe full-text metadata or invalid metadata shape.
- `404` unknown book.
- `422` invalid body.

Audience: development/admin-only.

### List Ingestion Jobs

`GET /api/admin/ingestion/jobs`

Response: `BookIngestionJob[]`.

Audience: development/admin-only.

### Get Ingestion Job

`GET /api/admin/ingestion/jobs/{job_id}`

Response: `BookIngestionJob`.

Errors:

- `404` unknown ingestion job.

Audience: development/admin-only.

### Run Ingestion Job

`POST /api/admin/ingestion/jobs/{job_id}/run`

Purpose: deterministic mock extraction into location candidates and artifacts.

Response: completed `BookIngestionJob`.

Errors:

- `404` unknown ingestion job.

Audience: development/admin-only.

### Promote Candidate

`POST /api/admin/ingestion/candidates/{candidate_id}/promote`

Purpose: create a POI from a candidate and immediately run verification through the configured POI adapter. Mock verification remains the default.

Response: `CandidatePromotionResponse` with `candidate` and `poiId`.

Errors:

- `404` unknown candidate.

Audience: development/admin-only.

## Admin/Development POI Verification Endpoints

### Verify Candidate

`POST /api/admin/poi/verify-candidate/{candidate_id}`

Response: `CandidateVerificationResponse` with `candidate` and `verification`.

The verification payload is adapter-neutral. With the default mock adapter, `provider` is `mock_local`. With `ENABLE_REAL_POI_PROVIDER=true` and `POI_PROVIDER=google_places`, the same fields carry normalized Google Places status, confidence, provider version, provider request/reference ID, verified timestamp, and warnings. Raw provider payloads and secrets are never returned.

Errors:

- `404` unknown candidate.

Audience: development/admin-only.

### Verify POI

`POST /api/admin/poi/verify/{poi_id}`

Response: `POIVerificationResponse` with `poi` and `verification`.

The returned `poi` persists verification provider, confidence, verified name/address/coordinates, opening-hours note, optional provider-supplied source URL, verification notes, manual review status, and provenance metadata. Low-confidence and no-match real-provider results remain `needs_review`.

Errors:

- `404` unknown POI.

Audience: development/admin-only.

### List Unverified POIs

`GET /api/admin/poi/unverified`

Response: `POI[]` where status needs verification/review.

Audience: development/admin-only.

### Mark POI Reviewed

`POST /api/admin/poi/{poi_id}/mark-reviewed`

Response: reviewed `POI`.

Errors:

- `404` unknown POI.

Audience: development/admin-only.

## Admin/Development Seed Data Endpoints

`SeedDataPayload`: `destinations`, `books`, `pois`, `itineraries`.

### Reset Seed Data

`POST /api/admin/seed/reset`

Purpose: destructive local reset and bundled reseed.

Response: `SeedOperationResult`.

Audience: development/admin-only.

### Export Seed Data

`GET /api/admin/seed/export`

Response: `SeedDataPayload`.

Audience: development/admin-only.

### Import Seed Data

`POST /api/admin/seed/import`

Request: `SeedDataPayload`.

Response: `SeedOperationResult`; invalid seed data returns `validation.valid=false` and does not import.

Audience: development/admin-only.

### Validate Seed Data

`GET /api/admin/seed/validate`

Response: `SeedValidationReport` with `valid`, `errors`, `warnings`, and `counts`.

Audience: development/admin-only.
