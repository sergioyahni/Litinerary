# Litinerary API Contract

Current scope: Phase 1 MVP plus Phase 2 foundations. Public endpoints are user-facing. Admin endpoints are development-only scaffolding and are not production admin APIs.

Base URL in local development: `http://127.0.0.1:8000`

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
- `500`: judge rejection may return `{"detail": {"message": "...", "reasons": [...], "warnings": [...], "confidenceScore": 0.2, "requiredFixes": [...]}}`.

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

Public repository endpoints return only itineraries where `isPublic=true` and `visibility="public"`. Private itinerary ownership enforcement is foundation-only until production auth and ownership route work are completed.

## Public Endpoints

### Health

`GET /api/health`

Purpose: service health check.

Response:

```json
{"status": "ok"}
```

Audience: user-facing/dev.

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

Purpose: fetch one itinerary by ID.

Response: `Itinerary`.

Errors:

- `404` unknown itinerary.

Audience: user-facing.

### Itinerary Narration

`GET /api/itineraries/{itinerary_id}/narration`

Purpose: return provider-neutral narration for an itinerary. This is deterministic mock/local behavior and is safe to call without prior generation.

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
- `422` invalid request body.

Audience: user-facing. Text fallback should remain available even when audio is unavailable.

### Adapt Itinerary

`POST /api/itineraries/adapt`

Purpose: adapt an existing public itinerary to a requested duration and transportation mode.

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

Auth mode: auth is disabled by default. When `ENABLE_AUTH=true` and `AUTH_REQUIRED_FOR_USER_FEATURES=true`, user endpoints require `Authorization: Bearer <token>`. The only implemented validator is the local/test development token format:

```text
dev:<user_id>:<comma-separated-roles>:<subscription_status>
```

Future managed providers should validate JWT issuer, audience, accepted algorithms, signature, expiry, and claims behind the same backend auth boundary.

### Create User

`POST /api/users`

Request: `UserCreateRequest`

```json
{"id": "dev-reader", "email": "reader@example.test", "displayName": "Reader"}
```

Response: `UserProfile`, including `role`, `subscriptionStatus`, optional `authProvider`, and `updatedAt`.

Errors:

- `409` user already exists.

Audience: development user-facing account foundation.

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

Response: `UserBookmarksResponse` with `userId` and `itineraries`.

Errors:

- `404` unknown user or itinerary.

Audience: development user-facing account foundation.

### Remove Bookmark

`DELETE /api/users/{user_id}/bookmarks/{itinerary_id}`

Purpose: remove itinerary bookmark.

Response: `UserBookmarksResponse`.

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

Request:

```json
{"itineraryId": "it-london-oliver-twist-1-walking", "rating": 5, "comment": "Great route."}
```

Response: `UserReview`.

Errors:

- `404` unknown user or itinerary.
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
