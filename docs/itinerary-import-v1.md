# `litinerary-import/v1`

Gate B adds an administrator-only application-level itinerary import contract. It is not database-table serialization and must not bypass canonical itinerary validation or persistence.

## Lifecycle and API

The administrative lifecycle is:

`parse -> validate -> preview -> confirm -> persist -> verify -> publish`

All endpoints are under `/api/admin/ingestion/itinerary-imports` and require both an enabled ingestion-admin boundary and an authenticated administrator. Local/test uses `ENABLE_ADMIN_ROUTES`; controlled staging acceptance uses the narrower `ENABLE_STAGING_ADMIN_INGESTION_ROUTES` switch described in `gate-b-staging-admin-activation.md`:

- `POST /api/admin/ingestion/itinerary-imports`: parse, validate, and store a dry-run preview.
- `GET /api/admin/ingestion/itinerary-imports`: list import jobs.
- `GET /api/admin/ingestion/itinerary-imports/{job_id}`: retrieve job/audit state.
- `POST /api/admin/ingestion/itinerary-imports/{job_id}/confirm`: explicitly confirm canonical persistence.
- `GET /api/admin/ingestion/itinerary-imports/{job_id}/verify`: verify canonical rows and provenance.
- `POST /api/admin/ingestion/itinerary-imports/{job_id}/publish`: deliberately publish eligible records.

Gate B keeps ingestion API/CLI-oriented. There is no dedicated admin ingestion frontend in the current product; adding one is not necessary to prove authorization, validation, or persistence. Any future UI must call these backend endpoints and must not receive direct database access.

## Contract

A batch has:

- `version`: exactly `litinerary-import/v1`;
- `batchIdentity`: stable source-batch identity;
- `source`: source name, optional attribution, and non-secret metadata;
- `records`: 1-500 records with unique `sourceIdentity` values.

Each record has a stable source identity, attribution, destination identity/metadata, book identity/metadata, itinerary content, and `publicationIntent` (`draft` or `publish`). Itinerary content includes duration, transportation mode, days, and ordered stops referencing canonical POIs.

The Pydantic contract rejects unknown fields and unsupported versions. The canonical JSON artifact is limited to 2,000,000 bytes. Metadata keys that look like credentials, passwords, secrets, tokens, or authorization values are rejected. Because the Gate B upload surface is a JSON body, filenames and client MIME declarations are not trusted or used. Import artifacts are data only; no code or templates are executed.

A controlled example is in `backend/tests/fixtures/itinerary_import_v1_valid.json`.

## Repository and external-book semantics

`book.semantics` is:

- `repository`: the `BookModel` must already exist, be linked to the destination, and referenced POIs must be linked to that book.
- `external_snapshot`: the identity must not collide with an existing `BookModel`. The supplied metadata is stored as the itinerary's book snapshot. No standalone placeholder `BookModel` is created.

Destinations and POIs are resolved from canonical repository data. This preserves the public external-book projection established before Gate B.

## Dry run and preview

`POST /api/admin/ingestion/itinerary-imports` is mandatory before persistence. It parses the exact artifact, resolves identities, builds the canonical `Itinerary` DTO, calls the same access/reference validation used by canonical persistence, evaluates idempotency/conflicts, and reports projected mutations and per-record errors.

It stores only the import job/audit artifact and preview. It never calls canonical itinerary persistence and never publishes.

Preview outcomes:

- `new`: valid and projected to create one draft canonical itinerary;
- `already_imported`: identical stable source identity and content hash already exist;
- `conflict`: stable source identity exists with different content;
- `invalid`: domain/reference/persistence validation fails.

Confirmation is rejected while any record is `conflict` or `invalid`.

## Stable identity and retry policy

`sourceIdentity` is the record idempotency key. A SHA-256 hash of canonical record JSON is stored with it.

- First valid import creates one audit record and one canonical itinerary.
- Exact re-import performs no duplicate canonical mutation.
- Re-running an accepted batch is safe because records resolve by stable source identity.
- Changed content under the same identity is a deterministic conflict and cannot be silently duplicated.
- Duplicate source identities in one batch fail structural validation.
- If `itinerary.id` is omitted, a deterministic ID is derived from `sourceIdentity`.
- A supplied itinerary ID that already exists without matching import provenance is rejected.

## Canonical persistence

Import creates the ordinary `app.schemas.domain.Itinerary` object and persists it through `app.services.database_repository.save_itinerary()`; it does not construct and insert `ItineraryModel` rows directly.

The shared path enforces visibility/ownership invariants, destination identity, repository-book linkage, external-book snapshot semantics, POI identity/destination linkage, repository-book POI linkage, and canonical itinerary/day/stop construction.

Imported drafts use:

- `generatedFrom = "imported"`;
- `sourceType = "corpus_import"`;
- `createdByMode = "admin"`;
- `isPublic = false`;
- `visibility = "unlisted"`.

## Provenance and auditability

Canonical imported itineraries retain contract version, stable source identity, source-content hash, batch identity, original import job ID, source attribution, and import service/provider metadata.

Persistent import jobs retain job and batch IDs, initiating administrator, timestamps, contract version, artifact hash and parsed artifact, preview results, dry-run/mutation state, persisted/published itinerary IDs, completion/failure state, and sanitized failure categories. Import record audit rows retain stable source identity, content hash, itinerary ID, publication intent, attribution, status, and timestamps.

Structured ingestion events follow the existing `log_event` convention and emit identifiers, counts, state, and failure categories without logging the corpus payload.

## Publication lifecycle

Gate B uses the existing canonical visibility model:

`previewed -> persisted (unlisted/non-public) -> published (public)`

Persistence and publication are separate administrator actions. Only records whose contract intent is `publish` are eligible for publication. Anonymous repository APIs continue to expose only eligible `isPublic=true`, `visibility=public` itineraries.

Public itinerary detail and list/filter endpoints serialize through a dedicated public DTO.
They retain product-facing source/provider/book/destination provenance, but omit ownership,
administrator creation, entitlement, provider-request, service-correlation, stable import
identity, source hash, batch/job, source-attribution, import-contract audit metadata, and
nested POI manual-review fields.
The canonical itinerary and import audit tables retain those fields for verification,
idempotency, history, and publication workflow.

## Transaction and failure semantics

Persistence is **record-atomic with explicit partial-success reporting**. The audit row/job progress and canonical itinerary for a record are committed in the same SQLAlchemy session/transaction via the canonical persistence boundary. If the current record fails, that record is rolled back; previously committed records remain explicitly reported, the job becomes `persistence_failed`, and retry re-previews the batch. Already committed records become idempotent while the failed record is retried.

Publication uses the same record-atomic retry model and reports `publication_failed` on a failed record. Failure reports store sanitized exception categories rather than raw payloads, credentials, or stack data.

## Migration and rollback

Gate B migration `20261001_0011` adds only import audit/job tables and upgrades from accepted Gate A head `20260928_0010`. It can be downgraded to `20260928_0010`. The existing guarded `0010 -> 0009` downgrade for snapshot-backed external books remains unchanged and is still tested.

## Gate C procedure

The real several-hundred-itinerary corpus is not part of Gate B. After Gate B is accepted and Gate C is separately authorized, the operator should convert the corpus to `litinerary-import/v1`, run dry-run, resolve every invalid/conflicting record, review projected mutations, explicitly confirm, verify persisted identities/provenance, re-run for idempotency, publish eligible records, and verify anonymous repository discovery/filter/detail behavior.

Gate B does not authorize sourcing or importing the real corpus, freezing production corpus state, or production deployment.
