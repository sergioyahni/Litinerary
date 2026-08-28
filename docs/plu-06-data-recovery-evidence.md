# PLU-06 Data Recovery Evidence

## Scope

PLU-06 completed the repository-owned data integrity, backup/restore, and rollback readiness unit. No production deployment, hosted database provisioning, Auth0/Render provisioning, PR merge, or PLU-07/08 work was performed.

## Missing-POI Defect

Original behavior: `itinerary_to_model()` built itinerary stops with a conditional equivalent to `if db.get(POIModel, stop.poi.id) is not None`. If an input itinerary contained a valid stop whose POI was absent from the database, the save could succeed while the persisted itinerary contained fewer stops than the input.

Regression evidence: `test_legacy_missing_poi_filter_would_silently_drop_stop` demonstrates that legacy construction would produce:

- input itinerary contains `N` stops;
- persisted model construction contains fewer than `N` stops;
- no explicit failure would be raised by that filter.

## Resolution

Policy selected: explicit transactional rejection.

Rationale: the current application flow builds generated and adapted itineraries from catalog POIs returned by repository queries. Seed/import code also loads POIs before itineraries. POIs are therefore expected to exist as canonical catalog records before an itinerary references them. PLU-06 does not convert generated itinerary stop POI payloads into canonical durable POIs.

`save_itinerary()` now validates before destructive replacement:

- itinerary destination exists;
- itinerary book exists;
- book is linked to the itinerary destination;
- every stop POI exists;
- every stop POI belongs to the itinerary destination;
- every stop POI is linked to the itinerary book;
- owner/visibility invariants still hold.

Failures raise `ItineraryPersistenceError`, rollback the session, and leave existing data intact.

## Atomicity Evidence

Focused tests prove:

- existing POIs persist all stops and round-trip;
- missing POI saves are rejected;
- mixed existing/missing POI saves do not partially persist;
- failed replacement keeps the previous itinerary intact;
- persisted stop count equals intended stop count for successful saves;
- persisted stops join to real POIs;
- cross-destination POIs are rejected.

Command:

```powershell
venv\Scripts\python.exe -m pytest backend\tests\test_persistent_repository.py backend\tests\test_data_recovery.py -q
```

Result: `15 passed, 1 warning`.

## Integrity Checker

Command:

```powershell
cd backend
python -m scripts.check_data_integrity
```

Read-only checks detect:

- itinerary days referencing missing itineraries;
- itinerary stops referencing missing days;
- itinerary stops referencing missing POIs;
- itineraries referencing missing destinations/books;
- itinerary book/destination mismatches;
- itinerary stop POI destination mismatches;
- itinerary stop POI book mismatches;
- POIs referencing missing destinations;
- POI/book links referencing missing books;
- owner/visibility invariant violations.

Disposable restored rehearsal result:

```text
integrity_status=ok
violations=0
```

## Backup Command

Command:

```powershell
cd backend
python -m scripts.backup_database --destination <explicit-backup-path>
```

SQLite mechanism: native SQLite backup API.

PostgreSQL mechanism: `pg_dump --format=custom` wrapper when `pg_dump` is available. Hosted PostgreSQL restore validation remains PLU-07.

Safety:

- destination is explicit;
- existing backup files are not overwritten;
- database URLs and credentials are not printed;
- failures exit non-zero.

## Restore Command

Command:

```powershell
cd backend
python -m scripts.restore_database `
  --backup <backup-path> `
  --target-database-url <explicit-target-database-url> `
  --replace `
  --confirm-restore RESTORE
```

Safety:

- target database URL is explicit;
- destructive replacement requires `--replace`;
- confirmation token `RESTORE` is required;
- database URLs and credentials are not printed;
- post-restore migration and integrity checks are run.

## Recovery Rehearsal

Command:

```powershell
cd backend
python -m scripts.rehearse_database_recovery `
  --work-dir ..\tests\.artifacts\tmp\plu06-rehearsal `
  --replace-work-dir
```

Disposable engine: SQLite.

Baseline after Alembic upgrade and seed:

- Alembic head: `20260815_0009`
- destinations: `5`
- books: `10`
- POIs: `13`
- itineraries: `2`
- itinerary days: `2`
- itinerary stops: `5`
- reference itinerary: `it-london-oliver-twist-1-walking`
- reference stop count: `3`
- integrity: `ok`, violations `0`
- migration status: `current`

Backup:

- format: `sqlite-backup`
- path under ignored `tests/.artifacts/tmp/plu06-rehearsal`

Deliberate mutation:

- deleted referenced POI: `charles-dickens-museum`
- POI count changed from `13` to `12`
- integrity status after mutation: `failed`
- violations after mutation: `1`

Restore:

- restored from backup to the explicit disposable target;
- migration status after restore: `current`;
- integrity after restore: `ok`, violations `0`;
- restored counts match baseline;
- reference itinerary and stop count restored.

## Migration / Rollback Evidence

Current Alembic head: `20260815_0009`.

All current migration files define downgrade functions.

Disposable migration command evidence:

```text
empty SQLite database -> alembic upgrade head -> current
downgrade -1 -> upgrade head -> current
```

Observed output:

```text
after_upgrade {'status': 'current', 'currentRevisions': ['20260815_0009'], 'expectedHeads': ['20260815_0009']}
after_downgrade_upgrade {'status': 'current', 'currentRevisions': ['20260815_0009'], 'expectedHeads': ['20260815_0009']}
```

Policy:

- application regression with compatible schema -> application rollback;
- additive migration bug with data intact -> forward fix or corrected migration;
- destructive/incompatible data loss -> stop writes if necessary and restore a known-good backup/snapshot;
- migration downgrade only after migration-specific data-safety review and rehearsal.

This does not guarantee production data-safe downgrades.

## Commands Executed

```powershell
git status --short
git branch --show-current
git log -1 --oneline
git rev-parse HEAD
git rev-parse plu-05-observability-ops
git switch -c plu-06-data-recovery
venv\Scripts\python.exe -m pytest backend\tests\test_persistent_repository.py -q
venv\Scripts\python.exe -m pytest backend\tests\test_persistent_repository.py backend\tests\test_data_recovery.py -q
venv\Scripts\python.exe -m py_compile backend\app\services\database_repository.py backend\app\services\data_integrity.py backend\app\core\observability.py backend\scripts\check_data_integrity.py backend\scripts\backup_database.py backend\scripts\restore_database.py backend\scripts\rehearse_database_recovery.py backend\tests\test_persistent_repository.py backend\tests\test_data_recovery.py
venv\Scripts\python.exe -m pytest backend\tests -q
cd backend
..\venv\Scripts\python.exe -m scripts.check_data_integrity --help
..\venv\Scripts\python.exe -m scripts.backup_database --help
..\venv\Scripts\python.exe -m scripts.restore_database --help
..\venv\Scripts\python.exe -m scripts.rehearse_database_recovery --help
..\venv\Scripts\python.exe -m scripts.rehearse_database_recovery --work-dir ..\tests\.artifacts\tmp\plu06-rehearsal --replace-work-dir
$env:APP_ENV='test'; $env:LITINERARY_DATABASE_URL='sqlite:///../tests/.artifacts/tmp/plu06-rehearsal/rehearsal.sqlite3'; ..\venv\Scripts\python.exe -m scripts.check_data_integrity
```

Final backend result:

```text
366 passed, 3 skipped, 114 warnings
```

## Deferred To PLU-07

- Hosted PostgreSQL backup/snapshot validation.
- Hosted PostgreSQL restore rehearsal.
- Render staging database provisioning.
- Provider-specific backup freshness and retention measurement.
- Staging application verification after restore.

No hosted PostgreSQL recovery was performed in PLU-06.

## Artifact Hygiene

Backup and database artifacts are ignored:

- `*.db`
- `*.sqlite`
- `*.sqlite3`
- `*.backup`
- `*.dump`
- `*.pgdump`
- `tests/.artifacts/**`

No database or backup artifact is intended to be committed.
