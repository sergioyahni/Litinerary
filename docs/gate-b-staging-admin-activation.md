# Gate B staging admin ingestion activation

This runbook is only for the controlled Gate B fixture in
`backend/tests/fixtures/itinerary_import_v1_valid.json`. It does not authorize Gate C,
the real corpus, production deployment, or any other administrative mutation.

## Security model

The normal staging and production profiles keep both admin switches false. The temporary
staging capability uses:

```text
APP_ENV=staging
ENABLE_ADMIN_ROUTES=false
ENABLE_STAGING_ADMIN_INGESTION_ROUTES=true
ENABLE_AUTH=true
AUTH_PROVIDER=auth0
AUTH_ROLES_CLAIM=roles
AUTH_ALLOW_DEV_USER_FALLBACK=false
```

The dedicated switch enables only `/api/admin/ingestion/*`. Seed and POI admin routes
remain disabled because they still require `ENABLE_ADMIN_ROUTES=true`. Every ingestion
request also passes through `require_admin_user`, so anonymous callers receive `401` and
managed ordinary users receive `403`. Deployed startup validation rejects the broad admin
switch, the dedicated switch is invalid outside staging, and request guards enforce both
boundaries even if configuration is forced.

## Preconditions

1. Record the accepted main SHA, green CI run, and successful staging deployment.
2. Verify backend `/api/version` and frontend `/release.json` report that exact SHA.
3. Verify backend health, readiness, and migration head `20261001_0011`.
4. Verify the controlled itinerary `it-import-gate-b-controlled-fixture` is `404` anonymously.
5. Obtain short-lived managed Auth0 tokens for one ordinary staging user and one user whose
   `roles` claim contains `admin`. Never place tokens in files, logs, command history, or reports.
6. Confirm product providers remain mock/fake and external product calls remain disabled.

## Activate

In the Render staging backend service only, set
`ENABLE_STAGING_ADMIN_INGESTION_ROUTES=true`. Keep `ENABLE_ADMIN_ROUTES=false`. Redeploy or
restart the accepted candidate, then recheck version, health, readiness, and migration head.
Do not change the production service or blueprint profile.

Validate the active environment from a secure operator shell:

```powershell
Set-Location backend
..\venv\Scripts\python.exe -m scripts.validate_beta_config `
  --profile staging --allow-staging-admin-ingestion
```

## Authorization matrix

Use `GET /api/admin/ingestion/itinerary-imports` so authorization checks do not mutate data:

1. No token: `401`.
2. Managed ordinary-user token: `403`, `Admin role is required.`
3. Managed administrator token: `200`.

Development tokens are not acceptable evidence in staging.

## Controlled lifecycle

1. Reconfirm anonymous detail for `it-import-gate-b-controlled-fixture` is `404`.
2. POST the unchanged committed fixture to `/api/admin/ingestion/itinerary-imports` with the
   administrator token. Record the job ID, artifact hash, `dryRun=true`, `status=previewed`,
   and projected mutation counts.
3. Reconfirm anonymous detail is still `404` after preview.
4. POST `/api/admin/ingestion/itinerary-imports/{job_id}/confirm`. Verify one canonical
   itinerary was persisted as `isPublic=false`, `visibility=unlisted`, with import provenance
   and audit state. Anonymous detail must remain `404`.
5. GET `/api/admin/ingestion/itinerary-imports/{job_id}/verify` and retain the verification
   result.
6. Re-submit the unchanged fixture and verify deterministic `already_imported` behavior and
   no duplicate canonical itinerary. The automated suite covers changed-content conflict;
   exercise it live only if the acceptance owner explicitly requires the non-persisting preview.
7. POST `/api/admin/ingestion/itinerary-imports/{job_id}/publish`. Verify the separate
   publication audit transition and public visibility.
8. Without a token, verify direct detail, repository listing, destination/book filtering, and
   the public DTO. `ownerUserId`, `createdByMode`, `createdByUserId`, `subscriberOnly`,
   `providerRequestId`, `generatedByService`, stable import identity/content hash, import
   batch/job/contract data, source attribution, and batch source must not appear anywhere in
   the serialized public response. Admin verification must still report matching provenance.
9. Recheck readiness/provider posture and confirm no unrelated `BookModel` or other canonical
   placeholder was created.

## Restore and verify

Set `ENABLE_STAGING_ADMIN_INGESTION_ROUTES=false` on the staging backend and redeploy or
restart the same accepted SHA. Then verify:

1. Version, frontend release, health, readiness, and migration identity are unchanged.
2. An administrator request to `/api/admin/ingestion/itinerary-imports` now returns `403` with
   `Admin/development endpoints are disabled in this environment.`
3. The published controlled itinerary remains anonymously consumable.
4. `ENABLE_ADMIN_ROUTES=false` and all product-provider locks remain unchanged.

Record activation and restoration times, deployment IDs, status codes, job/itinerary IDs, and
sanitized response fields. Do not record bearer tokens.
