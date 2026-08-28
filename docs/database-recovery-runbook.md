# Database Recovery Runbook

This runbook defines Litinerary database integrity, backup, restore, and rollback procedures for PLU-06. It is repository-owned operational guidance. It does not claim that hosted PostgreSQL recovery has been tested yet; that validation belongs to PLU-07 after real staging infrastructure exists.

## Ownership

Primary database recovery owner: repository/application owner.

Current responsible owner: `sergioyahni`.

The recovery owner is responsible for triage, stopping unsafe writes when needed, preserving evidence, selecting rollback versus restore, and recording the recovery result.

## Decision Table

| Scenario | Response |
| --- | --- |
| Application regression, schema compatible | Roll back the application release to the prior known-good version. Keep the database schema in place if it is backward-compatible. |
| Additive migration bug, data intact | Prefer a forward fix or corrected migration. Do not downgrade real data until the specific downgrade has been reviewed against the current data state. |
| Data corruption or destructive migration | Stop writes if necessary, preserve evidence, restore from a known-good backup/snapshot, then validate integrity and migration revision. |
| Provider outage | Not a database restore event. Follow provider incident procedures. |
| Integrity checker reports missing itinerary/POI/book/destination references | Treat as a data integrity incident. Stop writes if the issue is growing, preserve sample IDs, and decide between forward repair and restore. |

## Integrity Check

Run a read-only integrity check:

```powershell
cd backend
python -m scripts.check_data_integrity
```

Expected healthy output:

```text
integrity_status=ok
violations=0
```

The checker does not modify data and does not print the database URL. It returns non-zero if violations are found.

## Backup Procedure

Create a backup from the configured database:

```powershell
cd backend
python -m scripts.backup_database --destination <explicit-backup-path>
```

Safety rules:

- The destination must be explicit.
- Existing backup files are not overwritten.
- Database URLs and credentials are not printed.
- SQLite uses the native SQLite backup API.
- PostgreSQL production/staging should use `pg_dump` custom format or the hosting provider's managed snapshot mechanism once provisioned.
- Backup artifacts must be stored outside tracked source paths or under ignored artifact directories.

## Restore Procedure

Restore only to an explicit target:

```powershell
cd backend
python -m scripts.restore_database `
  --backup <backup-path> `
  --target-database-url <explicit-target-database-url> `
  --replace `
  --confirm-restore RESTORE
```

Safety rules:

- A default configured database is never restored implicitly.
- The target URL must be explicit.
- The confirmation token `RESTORE` is required.
- Existing SQLite targets require `--replace`.
- Restore output omits database URLs and secrets.
- Restore is followed by migration and integrity verification.

## Post-Restore Validation

After restore:

1. Confirm database connectivity.
2. Confirm Alembic migration status is `current`.
3. Run `python -m scripts.check_data_integrity`.
4. Confirm seed/reference rows and key counts are restored.
5. Confirm representative itinerary reads work.
6. Preserve command output and deployment/application revision identifiers.

## Application Rollback Policy

Use application-only rollback when the database schema remains compatible with the prior application version. Prefer this for application regressions that do not corrupt data.

Do not run database restore for provider outages, external API failures, or ordinary application exceptions when data is intact.

## Database Rollback Policy

Alembic downgrades are not the default production rollback strategy.

Use migration downgrade only when:

- the exact migration downgrade has been reviewed;
- the current data state is compatible with the downgrade;
- a known-good backup exists;
- the operation has been rehearsed on a copy or staging target.

For additive and backward-compatible migration defects, prefer a forward fix or corrected migration. If a destructive or incompatible migration corrupts/removes data, use restore from a known-good backup or managed snapshot.

## Provisional Recovery Objectives

Until staging and hosting capabilities are measured, recovery objectives are provisional:

- Provisional RPO: bounded by the freshness of the latest verified backup/snapshot.
- Provisional RTO: bounded by backup availability, restore duration, migration verification, integrity checks, and application validation.

Do not treat these as production guarantees until PLU-07 validates the actual hosted PostgreSQL plan.

## PLU-07 Staging Validation

PLU-07 must validate this procedure against real staging PostgreSQL or the selected hosting provider's managed backup/snapshot feature:

- create or identify a staging backup/snapshot;
- restore to an explicit staging recovery target;
- verify Alembic revision;
- run integrity checks;
- verify reference application reads;
- record duration, operator steps, and provider-specific retention/freshness details.

## Evidence To Preserve

- Incident timeline.
- Application commit/release identifier.
- Alembic revision before and after restore.
- Backup identifier/path or provider snapshot identifier.
- Integrity-check output.
- Counts/reference records before mutation and after restore.
- Any data repair SQL reviewed or executed.
- Owner approval for destructive restore or downgrade.
