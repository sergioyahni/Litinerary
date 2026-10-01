# Gate B automated contract coverage audit

This matrix records the coverage audit performed before Gate B importer implementation and the focused coverage added during Gate B.

| Contract / invariant | Before Gate B | Significant gap found | Gate B coverage |
| --- | --- | --- | --- |
| Anonymous public destination/book/itinerary consumption | Partial coverage across repository tests and `test_public_repository_authenticated_generation.py` | No single contract test proved normal destination + book + filtered itinerary + direct detail together | `test_gate_b_contract_coverage.py::test_anonymous_repository_consumption_covers_public_contract` |
| External-book snapshot public projection | Covered by `test_authenticated_external_book_generation_publishes_repository_snapshot` | None after Gate A regression repair | Existing regression retained; importer external-snapshot publication test extends it |
| Anonymous external discovery/generation/adaptation denial | Book discovery, generation, adaptation covered | Destination discovery denial was implicit/missing | `test_gate_b_contract_coverage.py::test_anonymous_external_destination_discovery_is_denied`; existing generation/adaptation denial retained |
| Ordinary authenticated repository access | Indirectly covered | No focused positive repository-consumption assertion | `test_authenticated_ordinary_user_keeps_repository_access` |
| Authentication is not administrator authorization | Admin guards existed, positive/negative ingestion matrix incomplete | Existing ingestion tests relied on auth-disabled development behavior | Strict admin guard on ingestion router + `test_import_authorization_and_disabled_environment` |
| External discovery alone does not persist repository state | External generation test proved no placeholder `BookModel` after generation | Discovery-only no-mutation contract not isolated | `test_external_discovery_alone_does_not_mutate_repository` |
| Reuse before generation | Covered by authenticated external-book generation regression and existing generation tests | None | Existing regression retained |
| Non-public visibility does not leak | Covered for private/unlisted external snapshots | Import draft lifecycle not covered | `test_confirm_verify_publish_repository_book` |
| Admin ingestion: anonymous denied / user denied / admin allowed / disabled env fails closed | Legacy admin route flag test only; legacy ingestion allowed when auth disabled | Positive strict-admin path and all four states missing | `test_import_authorization_and_disabled_environment`; legacy book ingestion tests now authenticate as admin |
| Versioned import contract | Missing | Entire contract missing | `test_itinerary_import.py` structural/version/domain tests + strict Pydantic schema |
| Mandatory dry run / zero canonical mutation | Missing | Entire contract missing | `test_dry_run_is_non_mutating_and_rejects_unsafe_inputs` |
| Explicit preview -> confirm separation | Missing | Entire contract missing | import route lifecycle tests |
| Canonical validation/persistence reuse | Generation/adaptation used `database_repository.save_itinerary()` | Import did not exist | importer builds canonical `Itinerary` and uses canonical validators / `save_itinerary()` |
| Stable source identity / exact re-import / changed-content conflict | Missing for corpus ingestion | Entire contract missing | `test_idempotency_conflict_and_domain_invalid`; duplicate source identities rejected structurally |
| Record/batch retry safety | Missing | Entire contract missing | exact re-import test + forced record-atomic failure/retry test |
| Provenance/auditability | Generation/provider provenance existed | Corpus job/source linkage missing | persistent import job/record models + publish/verification assertions |
| Publication lifecycle | Public visibility rules existed | Imported draft -> publish lifecycle missing | `test_confirm_verify_publish_repository_book` |
| External-book import without placeholder `BookModel` | Gate A generation behavior covered | Import path missing | `test_external_snapshot_import_does_not_create_book_model` |
| Failure/transaction semantics | Canonical single-itinerary save rolled back on failure | Batch semantics undefined | `test_record_atomic_failure_is_retryable` |
| Migration from accepted Gate A head | Existing migration suite reached then-current head | No import-audit migration | `test_itinerary_import_migration.py` upgrades `20260928_0010 -> 20261001_0011` and downgrades only to Gate A head |
| Guarded external-book downgrade | Covered by `test_itinerary_ownership_migration.py` | New head expectation must advance without weakening guard | Existing guard retained; current-head assertions updated to `20261001_0011` |

## Coverage posture

Gate B intentionally keeps the existing Gate A repository/generation regressions and adds importer-specific tests rather than replacing them. The controlled import tests cover repository-book and external-book records, malformed/unsupported input, domain-invalid records, duplicate stable identities, exact re-import, changed-content conflicts, publication visibility, forced persistence failure, safe retry, and migration behavior.

The several-hundred-itinerary real corpus is not a Gate B fixture and is not part of this automated suite.
