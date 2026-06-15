# Provider Adapter Contracts

Litinerary currently uses local mock/fake providers only. This document defines the contracts future real integrations must satisfy before any external LLM, embedding, Vector DB, POI, routing, ticketing, text-to-speech, affiliate, payment, or e-commerce service is connected.

Relevant modules:

- Shared metadata/errors: `backend/app/services/provider_contracts.py`
- AI protocols: `backend/app/services/ai_types.py`
- Mock AI pipeline: `backend/app/services/mock_ai_service.py`
- Vector protocols: `backend/app/services/vector_types.py`
- Fake vector store: `backend/app/services/fake_vector_store.py`
- POI verification: `backend/app/services/poi_verification.py`
- Routing placeholder: `backend/app/services/routing_types.py`, `backend/app/services/routing_service.py`
- Ticketing placeholder: `backend/app/services/ticketing_types.py`, `backend/app/services/ticketing_service.py`
- Narration/TTS placeholder: `backend/app/services/narration_types.py`, `backend/app/services/narration_service.py`
- Affiliate placeholder: `backend/app/services/affiliate_types.py`
- Provider configuration: `backend/app/core/config.py`
- External-call guard: `backend/app/core/provider_guards.py`
- Usage/cost guardrails: `backend/app/services/usage_policy.py`

## Feature Flags

Real provider calls must remain disabled unless explicitly enabled:

| Provider category | Provider setting | Feature flag | Current implementation |
|---|---|---|---|
| LLM | `LITINERARY_AI_PROVIDER` / `LLM_PROVIDER` | `ENABLE_REAL_LLM` | `fake` mock AI by default; OpenAI-compatible boundary available when explicitly enabled |
| Embedding / Vector DB | `LITINERARY_VECTOR_PROVIDER` / `VECTOR_DB_PROVIDER` | `ENABLE_REAL_VECTOR_DB` | fake embedding + in-memory/local JSON store by default; Qdrant adapter boundary available when explicitly enabled |
| POI verification | `LITINERARY_POI_VERIFICATION_PROVIDER` / `POI_PROVIDER` / `POI_VERIFICATION_PROVIDER` | `ENABLE_REAL_POI_PROVIDER` | local mock verification by default; Google Places boundary available when explicitly enabled |
| Routing | `ROUTING_PROVIDER` | `ENABLE_REAL_ROUTING` | mock straight-line estimates by default; OpenRouteService boundary available when explicitly enabled |
| Ticketing | `TICKETING_PROVIDER` | `ENABLE_REAL_TICKETING` | provider-neutral boundary with `example.test` mock placeholders |
| Text-to-speech | `TTS_PROVIDER` | `ENABLE_REAL_TTS` | provider-neutral narration text and placeholder audio metadata only; no generated audio storage |
| Affiliate/e-commerce | `AFFILIATE_PROVIDER` | `ENABLE_AFFILIATE_LINKS` | provider-neutral boundary with `example.test` mock book links; no checkout |

Production defaults keep real provider flags disabled. Missing credentials should produce clear startup validation notes, not silent external calls.

## External-Call Policy

Every live provider call must pass the central guard in `backend/app/core/provider_guards.py` before an HTTP request is made. Real-capable selectors and HTTP transports must call `require_external_call_allowed`.

Default policy:

- `ALLOW_EXTERNAL_CALLS=false` blocks all live provider requests.
- `ENABLE_INTEGRATION_TESTS=false` keeps standard tests blocked.
- `APP_ENV=test` blocks external calls unless `ENABLE_INTEGRATION_TESTS=true`.
- `EXTERNAL_CALL_ALLOWED_ENVIRONMENTS=production` allows live calls only in production by default.
- Provider-specific flags such as `ENABLE_REAL_LLM` and `ENABLE_REAL_ROUTING` must still be enabled.
- Required provider config such as API keys, URLs, model names, and timeout values must be present.

Future integration tests that intentionally make live calls must be skipped by default and require explicit environment opt-in:

```bash
APP_ENV=test
ENABLE_INTEGRATION_TESTS=true
ALLOW_EXTERNAL_CALLS=true
ENABLE_REAL_<PROVIDER>=true
```

Do not set these in standard unit, API, frontend, or smoke test commands.

## Rate, Quota, and Cost Guardrails

Provider-like operations also pass through local usage policy helpers in `backend/app/services/usage_policy.py`. This is a mock/local foundation, not billing or production-grade metering. It records provider type, operation type, request count, estimated token usage, estimated cost, user ID or anonymous session key, timestamp, provider metadata, and whether the request was allowed or blocked.

Current guarded operations:

- Itinerary generation.
- Subscriber chat messages and chat itinerary refinement.
- LLM completion input/output size.
- Vector search and upsert.
- POI verification.
- Routing calculation.
- Ticketing lookup.
- Text narration/TTS placeholder generation.

Configurable limits live in `backend/app/core/config.py` and `.env.example`:

- `ANONYMOUS_ITINERARY_GENERATIONS_PER_DAY`
- `REGISTERED_USER_ITINERARY_GENERATIONS_PER_DAY`
- `SUBSCRIBER_CHAT_MESSAGES_PER_DAY`
- `LLM_MAX_INPUT_CHARS`
- `LLM_MAX_OUTPUT_TOKENS`
- `VECTOR_SEARCH_MAX_RESULTS`
- `POI_VERIFICATION_MAX_BATCH_SIZE`
- `ROUTING_MAX_STOPS`
- `TICKETING_LOOKUP_MAX_REQUESTS_PER_ITINERARY`
- `PROVIDER_DAILY_COST_CEILING_USD`

Default persistence is in-memory and deterministic for tests. Production must replace it with durable per-user/session metering before enabling real provider traffic. The cost ceiling defaults to `0`, so any future positive-cost operation must explicitly configure a nonzero ceiling before it can pass.

## Standard Metadata

Every adapter result should attach `ProviderMetadata` where practical:

| Field | Purpose |
|---|---|
| `provider_name` | Adapter/provider identifier, such as `mock_ai` or a future provider name |
| `provider_type` | `llm`, `embedding`, `vector_db`, `poi_verification`, `routing`, `ticketing`, `tts`, or `affiliate` |
| `provider_version` | Provider API or adapter version |
| `request_id` | Provider request/correlation ID |
| `confidence_score` | Provider-neutral confidence score when meaningful |
| `source_url` | Public source/reference URL when safe |
| `generated_at` / `verified_at` | Result timestamps |
| `model_name` | LLM/embedding model name |
| `embedding_dimension` | Embedding dimension for vector records |
| `cost_estimate` | Cost estimate before/after provider call |
| `latency_ms` | Provider latency metric |
| `warnings` | Non-sensitive warnings |
| `raw_provider_reference` | Internal-only reference; never expose raw payloads to frontend |

Use `ProviderMetadata.public_dict()` before exposing metadata outside trusted backend boundaries.

## Standard Errors

Provider errors should use `ProviderError` with `ProviderErrorCode`:

- `provider_not_configured`
- `external_call_blocked`
- `provider_unavailable`
- `provider_timeout`
- `rate_limited`
- `quota_exceeded`
- `input_too_large`
- `unsupported_batch_size`
- `too_many_stops`
- `invalid_provider_response`
- `low_confidence_result`
- `unsafe_or_copyright_restricted_input`
- `unsupported_location`
- `no_match_found`
- `cost_limit_exceeded`
- `real_provider_disabled`

Adapters should normalize provider-specific failures into these codes. API responses for these errors return a structured `detail` object with `code`, `message`, and safe provider metadata; frontend clients should display the `message`. Raw provider errors may be logged internally only if they do not contain secrets, copyrighted text, or sensitive user data.

## Contract Expectations

### LLM Provider

Inputs: safe book summaries, curated source metadata, POI candidates, itinerary request parameters, review text, and existing itinerary data.

Outputs: structured ingestion summaries, extracted locations, generated/adapted itineraries, judge validation results, review feedback signals, and `ProviderMetadata`.

Current mock behavior: deterministic local generation from seeded POIs in `mock_ai_service.py`; no external LLM calls.

First real adapter target: OpenAI-compatible chat/completions JSON adapter. No project-specific provider had been selected yet, so the first boundary is provider-neutral at the app layer and OpenAI-compatible at the transport layer. This keeps future OpenAI, Azure OpenAI, compatible gateway, or self-hosted compatible endpoints isolated behind the same AI service interfaces.

Current OpenAI-compatible boundary:

- Adapter: `backend/app/services/openai_compatible_llm_adapter.py`
- Grounding checks: `backend/app/services/llm_grounding.py`
- Selection: set `ENABLE_REAL_LLM=true` and `LLM_PROVIDER=openai_compatible` or `LITINERARY_AI_PROVIDER=openai_compatible`.
- Required config when enabled: `LLM_API_KEY`, `LLM_MODEL_NAME`, and an `APP_ENV` allowed by `LLM_ALLOWED_ENVIRONMENTS`.
- Optional config: `LLM_BASE_URL`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_TOKENS`, `LLM_MAX_RETRIES`, `LLM_MONTHLY_BUDGET_USD`.
- Test behavior: standard tests inject fake LLM transports and never open network connections. `APP_ENV=test` blocks real LLM startup even if `ENABLE_REAL_LLM=true`.
- Supported future tasks behind one pipeline: summary/location extraction, POI extraction, itinerary generation, itinerary adaptation, review feedback synthesis, and judge validation.

Grounding policy:

- Allowed source types: `public_domain_text_reference`, `summary_document`, `manually_curated_location_list`, and `metadata_only`.
- Unsafe full-text metadata keys such as `fullText`, `full_text`, `copyrightedFullText`, and `rawText` are rejected before any provider call.
- Copyrighted full text is not allowed. Copyrighted summaries are allowed only with `summary_only` processing.
- Summary/public-domain source records must carry either source license or a known copyright status.
- Itinerary tasks require grounded POIs. POIs must be verified or explicitly marked as unverified/review-needed, have usable coordinates, and include provenance metadata or candidate source notes.
- Grounding context is passed as `GroundedLLMRequest` structured data, not as scattered prompt strings.

Judge controls:

- The judge result includes `approved`, `reasons`, `warnings`, `confidence_score`, `required_fixes`, and provider metadata.
- The local judge checks required schema fields, supported transportation mode, stop count per day, stop ordering, stop text, coordinates, POI verification state, low-confidence/review-needed POIs, route distance/duration metadata, unreasonable walking distance, provenance, and source licensing flags.
- Rejected API candidates return structured rejection details while preserving the existing `reasons` field.

Future requirements:

- Add production rate limiting, spend enforcement, retries with backoff, and observability before sustained traffic.
- Add prompt/version registry if prompt templates grow beyond structured request payloads.
- Require judge validation before saving/returning generated routes.
- Persist enough provenance for auditability without storing sensitive raw provider payloads.
- Do not log provider prompts, API keys, raw copyrighted inputs, or raw provider payloads.

### Embedding and Vector DB Provider

Inputs: text, collection name, vector ID, and metadata filters.

Outputs: vector records, search results, scores, and embedding `ProviderMetadata`.

Current mock behavior: deterministic `FakeEmbeddingProvider`, `InMemoryVectorStore`, optional `LocalJsonVectorStore`.

First real adapter target: Qdrant. The SDD lists Pinecone, Milvus, and Qdrant without selecting one. Qdrant is the first implemented boundary because it supports local/self-hosted development, has a simple HTTP API, and keeps the adapter isolated behind `VectorStore`.

Current Qdrant boundary:

- Adapter: `backend/app/services/qdrant_vector_store.py`
- Selection: set `ENABLE_REAL_VECTOR_DB=true` and `VECTOR_DB_PROVIDER=qdrant` or `LITINERARY_VECTOR_PROVIDER=qdrant`.
- Required config when enabled: `QDRANT_URL` or `VECTOR_DB_URL`, plus positive `LITINERARY_VECTOR_DIMENSION`.
- Optional config: `QDRANT_API_KEY` or `VECTOR_DB_API_KEY`, `QDRANT_COLLECTION_PREFIX`, `QDRANT_TIMEOUT_SECONDS`.
- Supported operations: collection initialization, upsert, batch upsert, search, delete, metadata fetch through scroll.
- Test behavior: unit tests inject a recording transport and never open network connections.
- Current embedding behavior: still uses deterministic local `FakeEmbeddingProvider`; no external embedding provider is connected yet.

Qdrant payload strategy:

- Litinerary vector IDs are preserved in Qdrant payload metadata as `vector_id`.
- Qdrant point IDs are deterministic UUIDv5 values derived from collection and vector ID.
- User/provider metadata is stored under the Qdrant payload `metadata` object.
- Raw provider payloads and secrets are not exposed to frontend responses.

Backfill plan stub:

```bash
cd backend
..\venv\Scripts\python.exe -m scripts.vector_backfill_plan
```

The stub prints the future backfill order for user preferences, reviews, itineraries, POIs, and book-city mappings. It does not generate embeddings or call any Vector DB.

Future requirements:

- Track embedding model, dimension, collection, external vector ID, and metadata version.
- Add batching/backfill policy before production migration.
- Keep user-specific metadata isolated.
- Enforce deletion behavior for privacy and retention requirements.

### POI Verification Provider

Inputs: place query, city/destination ID, candidate coordinates, and existing POI data.

Outputs: verification status, confidence, verified name/address/coordinates, opening-hours note, ticketing URL placeholder, notes, and `ProviderMetadata`.

Current mock behavior: matches against local seeded POIs only.

First real adapter target: Google Places API. The SDD explicitly names Google Places API as a POI Search API option, and it can support text search, coordinates, public place URLs, opening-hours summaries, provider IDs, and request provenance behind one isolated adapter. Foursquare remains a reasonable later alternative if Google cost, terms, regional coverage, or data-shape constraints become a poor fit.

Current Google Places boundary:

- Adapter: `backend/app/services/google_places_poi_adapter.py`
- Selection: set `ENABLE_REAL_POI_PROVIDER=true` and `POI_PROVIDER=google_places` or `LITINERARY_POI_VERIFICATION_PROVIDER=google_places`.
- Required config when enabled: `POI_PROVIDER_API_KEY`, `GOOGLE_PLACES_API_KEY`, or `POI_VERIFICATION_API_KEY`.
- Optional config: `POI_PROVIDER_BASE_URL`, `POI_PROVIDER_TIMEOUT_SECONDS`, `POI_PROVIDER_RESULT_LIMIT`, `POI_PROVIDER_MIN_CONFIDENCE`, `POI_PROVIDER_REGION_CODE`, `POI_PROVIDER_LANGUAGE_CODE`.
- Default confidence threshold: `0.82`. Results at or above the threshold become `provider_verified`; lower-confidence matches become `needs_review`; no matches become `needs_review` with confidence `0.0`.
- Supported operations: search by candidate/POI name plus destination, resolve candidates, verify existing POIs, validate/enrich coordinates, normalize opening-hours notes, pass through a reliable Google place/maps URL when supplied.
- Error normalization: timeout, rate-limit, provider unavailable, invalid response, missing config, low-confidence/no-match conditions are represented through provider-neutral statuses, notes, or `ProviderError` codes.
- Test behavior: unit tests inject fake transports and do not open network connections. A live integration placeholder is skipped by default and requires explicit future opt-in.

Google Places payload strategy:

- Only normalized fields are returned: name, address, coordinates, Google place ID/request reference, source URL, confidence, warnings, and timing.
- Raw provider payloads and API keys are not exposed to frontend responses.
- `ProviderMetadata.public_dict()` still excludes `raw_provider_reference`.
- POI persistence records `externalProviderUsed=true` only when a non-mock provider result is applied.

Future requirements:

- Store provider request ID, version, confidence, and `last_verified_at`.
- Avoid treating low-confidence matches as production-ready.
- Separate ticketing lookup from place verification when provider terms require it.
- Add cost/rate-limit controls and observability before sustained production traffic.
- Review Google Places terms for caching, display attribution, place URL usage, and retention before enabling in production.

### Routing Provider

Inputs: ordered route points, transportation mode, optional max duration.

Outputs: route segments, total distance/duration, frontend-friendly route geometry, feasibility, warnings, and `ProviderMetadata`.

Current mock behavior: straight-line distance estimates only.

First real adapter target: OpenRouteService. The frontend currently uses Leaflet with OpenStreetMap tiles, so OpenRouteService is a better first fit than Mapbox Directions because it keeps the routing layer aligned with the provider-neutral OSM/Leaflet map stack. Mapbox Directions remains a reasonable future option if the frontend moves to Mapbox GL JS.

Current OpenRouteService boundary:

- Adapter: `backend/app/services/openrouteservice_routing_adapter.py`
- Selection: set `ENABLE_REAL_ROUTING=true` and `ROUTING_PROVIDER=openrouteservice`.
- Required config when enabled: `ROUTING_API_KEY` or `OPENROUTESERVICE_API_KEY`.
- Optional config: `ROUTING_BASE_URL`, `ROUTING_TIMEOUT_SECONDS`, `ROUTING_MAX_STOPS`, `ROUTING_SUPPORTED_MODES`, `ROUTING_FALLBACK_BEHAVIOR`.
- Supported modes by default: `walking` maps to `foot-walking`; `car_taxi` maps to `driving-car`.
- Public transportation: not supported by the OpenRouteService adapter by default. Requests for `public_transport` raise a normalized unsupported-location provider error; itinerary enrichment can fall back to mock straight-line routing when `ROUTING_FALLBACK_BEHAVIOR=mock`.
- Geometry strategy: provider GeoJSON `[longitude, latitude]` coordinates are normalized to `[latitude, longitude]` arrays for Leaflet. Mock routing emits the same shape using straight-line stop coordinates.
- Persistence strategy: itinerary days can store `routeGeometry`, `routingProviderMetadata`, and `routingWarnings` alongside existing distance/duration estimates.
- Test behavior: unit tests inject fake transports and do not open network connections. A live integration placeholder is skipped by default and requires explicit future opt-in.

Future requirements:

- Enforce per-provider timeout/retry/cost limits.
- Validate walking/transit/car feasibility.
- Store route provider provenance and cache keys.
- Avoid presenting straight lines as real routes.
- Review OpenRouteService terms, attribution, rate limits, and response caching before enabling production traffic.

### Ticketing Provider

Inputs: POI ID/name, destination, optional date, search query, optional quantity, and optional result limit.

Outputs: ticketing options, availability status, ticketing URL, guided tour URL, source URL, price/currency when available, affiliate marker, last checked timestamp, confidence/relevance score, warnings, and `ProviderMetadata`.

Current mock behavior: `https://example.test/tickets/...` and `https://example.test/tours/...` placeholder links only. No live inventory, booking, payment, checkout, cart, or provider lookup occurs.

Current boundary:

- Contracts: `backend/app/services/ticketing_types.py`
- Mock selector/implementation: `backend/app/services/ticketing_service.py`
- Selection: keep `TICKETING_PROVIDER=mock` and `ENABLE_REAL_TICKETING=false` for local development and tests.
- Required config if a future real provider is enabled: `TICKETING_PROVIDER`, `TICKETING_API_KEY`, `TICKETING_BASE_URL`, positive `TICKETING_TIMEOUT_SECONDS`, and `ENABLE_REAL_TICKETING=true`.
- Real provider status: intentionally not implemented. Enabling real ticketing fails clearly at startup/provider selection.
- Supported operations: ticketing search, POI ticketing options, availability lookup, ticketing URL lookup, and guided tour URL lookup.
- Metadata policy: every option can carry provider name/type, source URL, last checked timestamp, confidence/relevance score, affiliate flag, warnings, and safe public metadata.

Future requirements:

- Select a real provider only after legal/product review of affiliate disclosure, stale inventory language, attribution, caching, and deep-link terms.
- Distinguish neutral links from affiliate links.
- Avoid storing payment secrets or sensitive booking payloads.
- Provide stale-data and availability warnings.
- Add rate limits, timeout/retry policy, and cost monitoring before any live calls.
- Keep ticketing optional in itinerary display; no itinerary should depend on a ticketing link.

### Affiliate/E-Commerce Provider

Inputs: book ID, title, author, optional product format.

Outputs: product title, URL, provider product ID, format, affiliate marker, last checked timestamp, relevance score, warnings, and `ProviderMetadata`.

Current mock behavior: `https://example.test/books/...` placeholder links for print, eBook, and audiobook formats. Links are explicitly marked affiliate placeholders. No real affiliate provider, store, checkout, cart, payment, or transaction is connected.

Current boundary:

- Contracts: `backend/app/services/affiliate_types.py`
- Mock selector/implementation: `backend/app/services/affiliate_service.py`
- Selection: `AFFILIATE_PROVIDER=mock` by default. `ENABLE_AFFILIATE_LINKS=false` keeps links disabled for product use unless intentionally surfaced.
- Required config if a future real affiliate provider is enabled: `AFFILIATE_PROVIDER`, `AFFILIATE_API_KEY`, `AFFILIATE_BASE_URL`, positive `AFFILIATE_TIMEOUT_SECONDS`, and `ENABLE_AFFILIATE_LINKS=true`.
- Real provider status: intentionally not implemented. Non-mock affiliate providers fail clearly if enabled without config or after config because no real adapter exists yet.
- API shape: `Book.affiliateLinks` is optional and defaults to an empty list.

Future requirements:

- Add explicit affiliate disclosure.
- Do not add payment/e-commerce behavior until separate security review.
- Add product policy review, store/provider terms review, rate-limit controls, tracking disclosure, and observability before enabling real links.
- Keep book purchase links optional; no book or itinerary rendering should depend on affiliate data.

### Text-to-Speech Provider

Inputs: itinerary title, summary, day summaries, stop titles, narrative notes, logistics notes, requested voice style, and optional duration guidance.

Outputs: narration script text, estimated duration, audio metadata, warnings, and `ProviderMetadata`.

Current mock behavior: `backend/app/services/narration_service.py` deterministically builds text narration from itinerary days and stops. By default it returns `text_only` narration. When placeholder audio is requested it returns metadata marked `placeholder=true` with no audio URL and no stored/generated audio file. No real text-to-speech provider is connected.

Current boundary:

- Contracts: `backend/app/services/narration_types.py`
- Mock selector/implementation: `backend/app/services/narration_service.py`
- API response schemas: `backend/app/schemas/narration.py`
- Required config if a future real TTS provider is enabled: `TTS_PROVIDER`, `TTS_API_KEY` or `TEXT_TO_SPEECH_API_KEY`, positive `TTS_TIMEOUT_SECONDS`, and `ENABLE_REAL_TTS=true`.
- Real provider status: intentionally not implemented. Non-mock TTS providers fail clearly and must not make network calls.
- Metadata policy: script responses expose provider-neutral metadata through safe public fields. Raw provider payloads, prompts, API keys, voice IDs with secrets, and audio storage references must not be exposed.

Future requirements:

- Select a provider only after reviewing voice licensing, generated audio retention, attribution, accessibility fallback, moderation, rate limits, and cost controls.
- Store generated audio only after an explicit storage, deletion, retention, and CDN access policy exists.
- Keep text narration available even when audio synthesis fails or is disabled.

## Test Gate

Run provider contract tests before adding any real provider adapter:

```bash
cd backend
..\venv\Scripts\python.exe -m pytest tests\test_provider_contracts.py
```

The tests assert that mock adapters satisfy contracts, metadata is attached, normalized errors are available, real-provider feature flags block accidental use, and no external network calls occur.
