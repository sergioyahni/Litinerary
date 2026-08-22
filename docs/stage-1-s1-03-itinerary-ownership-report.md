# Litinerary Stage 1 S1-03 Itinerary Ownership Report

Date: 2026-08-15

## Executive Summary

S1-03 is complete.

Litinerary now has an explicit server-side trust boundary for itinerary
ownership, visibility, and private access. Public repository itineraries remain
anonymous, ownerless, and readable without authentication. Subscriber chat
refinements create private, subscriber-only itineraries owned by the verified
backend `CurrentUser`. Private and unlisted itinerary detail/narration are
available only to the owner or an admin. User bookmark/review operations cannot
target another user's private itinerary by guessing an itinerary ID, and
bookmark lists filter inaccessible private rows.

The work intentionally did not implement a new sharing system, private itinerary
CRUD UI, managed-auth provider SDK, durable rate/cost metering, observability
platform integration, CI/CD, or live provider rollout. Those items are outside
the S1-03 scope boundary and remain separate production-readiness units.

## Starting State

Current branch at inspection time: `main`.

Current commit at inspection time:
`86a40dc90ff7dcfd4497ef1da190dc2da35e73ca`.

Relevant recent history included:

- `86a40dc Fix deployment readiness profile imports`
- `0e27a71 Update form-data dependency`
- `7bee38e Restore repository hygiene and document development status`
- `18c8463 docs: record Render rehearsal shutdown`
- `e8de4d6 docs: record Render log hygiene review`

The working tree already contained Stage 0, S1-01, and S1-02 edits and reports.
Those pre-existing changes were preserved.

Read first:

- `docs/stage-1-s1-02-managed-auth-report.md`
- `docs/production-development-progress.md`
- `docs/re-onboarding-production-readiness-review.md`
- itinerary/API/product/readiness docs under `docs/`

## Existing Itinerary Model

The repository already contained itinerary ownership/visibility fields:

- `itineraries.is_public`
- `itineraries.owner_user_id`
- `itineraries.visibility`
- `itineraries.created_by_mode`
- `itineraries.created_by_user_id`
- `itineraries.subscriber_only`

Before S1-03, public repository queries filtered to `isPublic=true` and
`visibility="public"`, but private owner read paths were incomplete and
bookmark/review targets were looked up without an owner-aware itinerary access
check.

## Existing Access Inventory

This matrix was created before code modification and drove the implementation.

| Operation | Current authentication before S1-03 | Current ownership before S1-03 | Current visibility before S1-03 | Production-safe before S1-03? |
| --- | --- | --- | --- | --- |
| Generate itinerary: `POST /api/itinerary/generate` | Anonymous/public | Generated public repository itinerary had no owner | Public | Yes for intended public generation |
| List itineraries: `GET /api/itineraries` | Anonymous/public | Owner ignored | Returned only `is_public=true` and `visibility="public"` | Mostly yes |
| Read itinerary: `GET /api/itineraries/{id}` | Anonymous/public | Owner ignored | Returned public only; private hidden as 404 | Safe for hiding, but no owner read path |
| Itinerary narration: `GET/POST /api/itineraries/{id}/narration` | Anonymous/public | Owner ignored | Used public-only itinerary lookup | Safe for hiding, but no owner narration path |
| Adapt itinerary: `POST /api/itineraries/adapt` | Anonymous/public | Owner ignored | Source lookup was public-only | Yes for public adaptation |
| Subscriber refine itinerary: `POST /api/subscribers/chat/sessions/{id}/refine-itinerary` | Subscriber auth required | Created private itinerary owned by verified current user | Private/subscriber-only | Mostly yes |
| Bookmark itinerary: `POST /api/users/{user_id}/bookmarks/{itinerary_id}` | User-feature auth when enabled/deployed | User path owner/admin guarded by S1-02; itinerary lookup unrestricted | Could bookmark private itinerary if ID was known | No |
| List bookmarks: `GET /api/users/{user_id}/bookmarks` | User-feature auth when enabled/deployed | User path owner/admin guarded by S1-02 | Returned all bookmarked itineraries, including stale inaccessible private rows | No |
| Remove bookmark: `DELETE /api/users/{user_id}/bookmarks/{itinerary_id}` | User-feature auth when enabled/deployed | Mutated only user's bookmark collection | Did not expose itinerary details | Acceptable, but response needed filtering |
| Save review: `POST /api/users/{user_id}/reviews` | User-feature auth when enabled/deployed | User path owner/admin guarded by S1-02; itinerary lookup unrestricted | Could review private itinerary if ID was known | No |
| List reviews: `GET /api/users/{user_id}/reviews` | User-feature auth when enabled/deployed | User path owner/admin guarded by S1-02 | Returned the user's own review records | Yes |
| Update itinerary | No endpoint exists | Not applicable | Not applicable | Not applicable |
| Delete itinerary | No endpoint exists | Not applicable | Not applicable | Not applicable |
| Publish/unpublish/share itinerary | No endpoint exists | Not applicable | Not applicable | Not applicable |

## Product Intent Evidence

Existing documentation and UX show three current itinerary concepts:

- Anonymous public generation and browsing are intentional product behavior.
- Persisted public repository itineraries are shared catalog/repository records.
- Subscriber chat refinements create private, subscriber-only itineraries tied
  to the subscriber.

No current product requirement or route implements publish/unpublish, share
links, unlisted access tokens, user-owned itinerary CRUD, or a "my itineraries"
page. Therefore S1-03 used the minimum production-safe model instead of
inventing a full sharing system.

## Ownership and Visibility Decision

Ownership:

- Public repository itineraries may be ownerless.
- Private/subscriber-only itineraries must have an owner.
- Ownership is represented by `itineraries.owner_user_id`.
- For authenticated creation, ownership is derived from the verified backend
  `CurrentUser`.
- Client-supplied owner/user/creator fields do not assign itinerary ownership.

Visibility:

- `public`: repository-visible, anonymous-readable, requires `isPublic=true`.
- `private`: owner/admin-only, requires `isPublic=false`.
- `unlisted`: schema-compatible but treated like private until a real sharing
  contract exists.

Admin:

- Existing `CurrentUser.is_admin` policy is retained. Admins can access private
  itinerary detail/narration and user route operations.

Update/delete/list:

- No direct itinerary update, delete, publish, unpublish, share, or private
  itinerary list endpoint exists today.
- Existing mutation surfaces are generation/adaptation, subscriber refinement,
  bookmarks, and reviews.

## Database/Migration Design

Migration added:

- `backend/migrations/versions/20260815_0008_itinerary_owner_constraints.py`

Model changes:

- `ItineraryModel.owner_user_id` now references `users.id` with
  `ON DELETE SET NULL`.
- `ItineraryModel.owner` and `UserModel.owned_itineraries` relationships were
  added.
- Indexes were added for public visibility and owner visibility lookups.

Migration behavior:

- Normalizes missing visibility to `public` or `private` based on `is_public`.
- Forces non-public visibility rows to `is_public=false`.
- Clears orphaned `owner_user_id` values instead of manufacturing ownership.
- Clears orphaned `created_by_user_id` values.
- Adds `ix_itineraries_public_visibility`,
  `ix_itineraries_owner_visibility`,
  `ix_itineraries_source_itinerary_id`, and
  `ix_chat_itinerary_references_itinerary_id`.

Alembic environment change:

- `backend/migrations/env.py` now calls `fileConfig(..., disable_existing_loggers=False)`
  so migration runs do not disable Litinerary's structured logger.

## Legacy Data Handling

Existing seeded/public rows are deliberately anonymous public repository data,
so they remain public and ownerless.

Existing private rows with unverifiable owners are preserved as private but have
orphaned owner/creator IDs cleared. S1-03 does not assign legacy private rows to
an arbitrary user. This keeps the migration deterministic and avoids creating
false ownership.

## Server-Side Authorization

Implemented access helpers in `database_repository`:

- `get_accessible_itinerary`
- `get_accessible_itinerary_model`
- `itinerary_row_is_accessible`
- `itinerary_is_accessible`
- `itinerary_row_is_public_repository`
- `validate_itinerary_access_invariants`

Route/service effects:

- Public listing still returns only `is_public=true` and `visibility=public`.
- Public generation remains anonymous and creates public ownerless itineraries.
- Public adaptation remains anonymous and only adapts public source
  itineraries.
- Itinerary detail and narration accept optional current-user auth and return
  private/unlisted rows only to owner/admin.
- Subscriber chat refinement continues to create private owner-bound itineraries
  from verified subscriber identity.
- Bookmark/review writes require public or owner/admin-accessible itinerary
  targets.
- Bookmark list responses filter inaccessible private rows.

Unauthorized private IDs return `404`, matching missing itinerary behavior and
avoiding private existence disclosure. Malformed or invalid bearer tokens still
return `401`.

## Frontend Impact

No trusted ownership control was added to the frontend. The frontend does not
send owner IDs as authority.

The existing detail route remains compatible. Its banner copy changed from
"public repository route" to "accessible route" because the same backend detail
endpoint can now return owner/admin private itineraries when authenticated.

Frontend auth/provider SDK integration remains outside S1-03 and is still a
separate production-readiness task.

## API Contract Changes

`docs/api-contract.md` now documents:

- public repository visibility rules;
- private/unlisted detail and narration owner/admin behavior;
- `404` behavior for inaccessible private IDs;
- anonymous public generation/list/adaptation semantics;
- generated public itineraries being ownerless;
- bookmark/review target authorization;
- bookmark list filtering;
- deployed auth startup/user-route expectations from S1-02.

## Security Properties

After S1-03:

- A client-controlled itinerary ID is not enough to read another user's private
  itinerary.
- A client-controlled user ID is not enough to act as another user in deployed
  or auth-required user routes.
- Client-supplied ownership fields do not assign ownership in public generation.
- Private itinerary detail/narration is owner/admin-only.
- Bookmark/review writes cannot target inaccessible private rows.
- Public catalog, public repository, public generation, and public adaptation
  remain intentionally anonymous.
- `unlisted` does not create accidental sharing before a sharing model exists.

## Files Changed

Implementation:

- `backend/app/models/domain.py`
- `backend/app/services/database_repository.py`
- `backend/app/services/mock_repository.py`
- `backend/app/services/user_repository.py`
- `backend/app/api/routes/itineraries.py`
- `backend/app/api/routes/users.py`
- `backend/migrations/env.py`
- `backend/migrations/versions/20260815_0008_itinerary_owner_constraints.py`
- `frontend/src/views/ItineraryDetailView.vue`

Tests:

- `backend/tests/test_itinerary_ownership.py`
- `backend/tests/test_itinerary_ownership_migration.py`

Documentation:

- `docs/api-contract.md`
- `docs/production-development-progress.md`
- `docs/production-readiness.md`
- `docs/beta-go-no-go-report.md`
- `docs/litinerary-development-status-report.md`
- `README.md`
- `backend/README.md`
- `docs/stage-1-s1-03-itinerary-ownership-report.md`

## Migration Results

Migration/seed command:

```powershell
$env:LITINERARY_DATABASE_URL='sqlite:///../tests/.artifacts/tmp/s1-03-migration-seed-20260815.db'
..\venv\Scripts\python.exe -m alembic upgrade head
..\venv\Scripts\python.exe -m alembic current
..\venv\Scripts\python.exe -m scripts.seed_database
```

Result:

- Alembic reached `20260815_0008 (head)`.
- Seed loaded 5 destinations, 10 books, 13 POIs, and 2 itineraries.

Migration tests also verified upgrade from previous head `20260614_0007`,
survival of compatible legacy rows, owner/creator orphan cleanup, index
presence, owner foreign-key presence, current head, and seed validity.

## Complete Validation Results

| Command | Result |
| --- | --- |
| `.\venv\Scripts\python.exe -m pytest backend\tests\test_itinerary_ownership.py backend\tests\test_itinerary_ownership_migration.py -q` | Passed: 8 passed, 3 warnings. |
| `.\venv\Scripts\python.exe -m pytest backend\tests\test_mvp_api.py backend\tests\test_model_metadata_migrations.py backend\tests\test_negative_security_paths.py backend\tests\test_subscriber_chat.py backend\tests\test_auth_foundation.py -q` | Passed: 71 passed, 1 warning. |
| `.\venv\Scripts\python.exe -m pytest -q --basetemp=tests\.artifacts\tmp\pytest-s1-03-full-fixed` | Passed: 313 passed, 3 skipped, 12 warnings. |
| `npm.cmd run typecheck` from `frontend/` | Passed. |
| `npm.cmd test` from `frontend/` | Passed: 13 files, 65 tests. |
| `npm.cmd run build` from `frontend/` | Passed. |
| Temp DB migration/seed validation | Passed: head `20260815_0008`; 5 destinations, 10 books, 13 POIs, 2 itineraries. |
| Temporary backend runtime validation | Passed: `/api/health=ok`, `/api/readiness=ready`, owner private detail `200`, other user `404`, anonymous `404`, public list count 2. |
| `git diff --check` | Passed with line-ending warnings only. |
| `git status --short --branch` | Reviewed; new S1-03 migration/tests/report are untracked and intentional; generated DB/pytest artifacts remain ignored. |

Warnings observed:

- Starlette/FastAPI `TestClient` deprecation warning.
- Alembic `path_separator` deprecation warning.
- Starlette `HTTP_413_REQUEST_ENTITY_TOO_LARGE` deprecation warning.

## Remaining Ownership/Sharing Gaps

Remaining product gaps:

- No dedicated private itinerary list endpoint exists.
- No direct private itinerary save/edit/delete endpoint exists.
- No publish/unpublish endpoint exists.
- No sharing link or unlisted-token behavior exists.
- No frontend private itinerary management UI exists.

These gaps are not S1-03 blockers because the corresponding operations do not
exist today. Future work must reuse the same owner/admin authorization boundary.

## Newly Discovered Production Risks

- Alembic `fileConfig` previously disabled app loggers during migration tests,
  which hid structured logs from later observability tests. This was fixed by
  preserving existing loggers.
- The earlier persistence-integrity risk remains: missing POI stops can still be
  silently dropped by the persistence mapper. S1-03 inspected the touched save
  path and added ownership invariants, but did not expand into the separate stop
  integrity task.
- Private CRUD/sharing product semantics are still undefined. `unlisted` is
  deliberately private until that future design exists.

## Production Impact

S1-03 removes the known current-route risk that a user could reference another
user's private itinerary by ID through detail/narration, bookmark, or review
paths. It also makes legacy data handling safer and owner constraints explicit.

Production remains no-go for reasons outside S1-03: real managed auth provider
selection/staging, frontend provider login/session UX, durable usage/cost
controls, observability retention/alerts, deployment/migration readiness, live
provider gates, dependency/security scanning, and future private CRUD/sharing
design.

## Next Recommended Task

S1-04: implement durable usage/rate/cost controls.

## Prompt Compliance Matrix

| # | Requirement | Status | Evidence |
| - | ----------- | ------ | -------- |
| 1 | Read current project state | DONE | Read S1-02, progress, re-onboarding, docs, branch/commit/status/history. |
| 2 | Preserve S1-02 auth guarantees | DONE | Reused `CurrentUser`, optional/required auth dependencies, and existing owner/admin policy. Full auth tests passed. |
| 3 | Reconstruct itinerary model | DONE | Inspected models, schemas, migrations, repositories, routes, services, tests, seed data, frontend services/views, and docs. |
| 4 | Produce access inventory before code changes | DONE | Inventory table in this report was created before implementation. |
| 5 | Determine product intent | DONE | Identified public repository, anonymous generation, and subscriber private refinement as current intent. |
| 6 | Define ownership contract | DONE | Contract documented in this report and `docs/api-contract.md`. |
| 7 | Enforce security invariant | DONE | Owner/admin access helpers prevent ID/user-ID-only access to private itineraries. |
| 8 | Design DB change before applying | DONE | Designed owner FK, indexes, visibility normalization, and legacy cleanup before migration. |
| 9 | Existing-data migration strategy | DONE | Public legacy rows remain public/ownerless; orphan owners are cleared, not reassigned. |
| 10 | Implement persistence-layer ownership | DONE | Model, migration, repository access helpers, and save invariants implemented. |
| 11 | Implement server-side authorization | DONE | Detail/narration, bookmarks, reviews, list filtering, public list/generation/adaptation behavior covered. |
| 12 | Prevent ownership injection | DONE | Generation ignores client ownership fields; regression test added. |
| 13 | Preserve anonymous/public behavior | DONE | Public generation/list/detail/adaptation remain anonymous; tests cover public behavior. |
| 14 | Handle missing vs unauthorized safely | DONE | Unauthorized private IDs return `404` like missing IDs; invalid bearer tokens remain `401`. |
| 15 | Verify admin semantics | DONE | Existing admin policy retained; admin private itinerary access tested. |
| 16 | Frontend impact analysis/implementation | DONE | Frontend creation/list/detail/auth paths inspected; detail copy updated; no trusted ownership controls added. |
| 17 | API contract update | DONE | `docs/api-contract.md` updated for auth, authorization, visibility, and error behavior. |
| 18 | Migration tests | DONE | New tests cover prior-head upgrade, legacy row survival, constraints/indexes/FK, seed validity, and current head. |
| 19 | Ownership security tests | DONE | Tests cover owner, cross-user, anonymous, public, ID manipulation, ownership injection, admin, and missing resource behavior. |
| 20 | List-query isolation tests | DONE | Public list excludes private rows; bookmark list filters inaccessible private rows. No "my itineraries" endpoint exists. |
| 21 | Persistence-integrity check | DONE | Touched save path inspected; issue not worsened and remains recorded as separate backlog work. |
| 22 | Complete backend validation | DONE | Full backend pytest passed: 313 passed, 3 skipped, 12 warnings. |
| 23 | Complete frontend validation | DONE | `npm.cmd run typecheck`, `npm.cmd test`, and `npm.cmd run build` passed. |
| 24 | Migration and seed validation | DONE | Temp DB migrated to head, seeded, and representative counts verified. |
| 25 | Runtime validation | DONE | Temporary backend health/readiness and private owner/other/anonymous API checks passed. |
| 26 | Git validation | DONE | `git diff --check` passed with line-ending warnings only; `git status --short --branch` reviewed; diff reviewed for scope and no secrets/generated tracked artifacts. |
| 27 | Update production progress docs | DONE | `docs/production-development-progress.md` updated with S1-03 status and evidence. |
| 28 | Update contradictory docs | DONE | Current docs updated and historical reports marked superseded for ownership/auth claims. |
| 29 | Create S1-03 session report | DONE | This file exists with all required sections. |
| 30 | Include matrix rows 1-30 | DONE | This matrix includes every numbered mandatory requirement individually. |
