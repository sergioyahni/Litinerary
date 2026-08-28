import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database_readiness import expected_alembic_heads, migration_readiness_status
from app.core.observability import EventName, configure_logging, log_event
from app.services.data_integrity import check_database_integrity


CONFIRMATION = "RESTORE"


def restore_database(
    *,
    backup: Path,
    target_database_url: str,
    replace: bool,
    confirm_restore: str,
) -> dict:
    if confirm_restore != CONFIRMATION:
        raise ValueError(f"Restore requires --confirm-restore {CONFIRMATION}.")
    if not backup.exists():
        raise FileNotFoundError(f"Backup file not found: {backup}")
    if target_database_url.startswith("sqlite"):
        _restore_sqlite(backup=backup, target_database_url=target_database_url, replace=replace)
        engine_name = "sqlite"
        restore_format = "sqlite-backup"
    elif target_database_url.startswith("postgresql"):
        _restore_postgresql(backup=backup, target_database_url=target_database_url)
        engine_name = "postgresql"
        restore_format = "pg_restore-custom"
    else:
        raise ValueError("Unsupported database dialect for restore.")

    verification = verify_restored_database(target_database_url)
    return {
        "engine": engine_name,
        "restore_format": restore_format,
        "integrity_status": verification["integrity_status"],
        "violations": verification["violations"],
        "migration_status": verification["migration_status"],
        "current_revisions": verification["current_revisions"],
    }


def verify_restored_database(target_database_url: str) -> dict:
    engine = create_engine(
        target_database_url,
        connect_args={"check_same_thread": False} if target_database_url.startswith("sqlite") else {},
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    try:
        with SessionLocal() as db:
            violations = check_database_integrity(db)
            migration = migration_readiness_status(db, expected_heads=expected_alembic_heads())
    finally:
        engine.dispose()
    return {
        "integrity_status": "ok" if not violations else "failed",
        "violations": sum(item.count for item in violations),
        "migration_status": migration["status"],
        "current_revisions": migration["currentRevisions"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore a database backup to an explicit target.")
    parser.add_argument("--backup", required=True, help="Backup file to restore.")
    parser.add_argument("--target-database-url", required=True, help="Explicit restore target URL.")
    parser.add_argument("--replace", action="store_true", help="Allow replacing an existing target.")
    parser.add_argument("--confirm-restore", required=True, help=f"Must be {CONFIRMATION}.")
    args = parser.parse_args()
    configure_logging()

    try:
        result = restore_database(
            backup=Path(args.backup).resolve(),
            target_database_url=args.target_database_url,
            replace=args.replace,
            confirm_restore=args.confirm_restore,
        )
    except Exception as exc:
        log_event(
            EventName.DATABASE_RESTORE_FAILED,
            category="database_recovery",
            operation="restore_database",
            error_type=exc.__class__.__name__,
            success=False,
        )
        print(
            json.dumps(
                {
                    "status": "failed",
                    "operation": "restore_database",
                    "errorType": exc.__class__.__name__,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1

    success = result["integrity_status"] == "ok" and result["migration_status"] == "current"
    log_event(
        EventName.DATABASE_RESTORE_COMPLETED if success else EventName.DATABASE_RESTORE_FAILED,
        category="database_recovery",
        operation="restore_database",
        database_engine=result["engine"],
        restore_format=result["restore_format"],
        integrity_status=result["integrity_status"],
        violations=result["violations"],
        migration_status=result["migration_status"],
        success=success,
    )
    print(
        json.dumps(
            {
                "status": "completed" if success else "failed",
                "operation": "restore_database",
                "databaseEngine": result["engine"],
                "restoreFormat": result["restore_format"],
                "integrityStatus": result["integrity_status"],
                "violations": result["violations"],
                "migrationStatus": result["migration_status"],
                "currentRevisions": result["current_revisions"],
            },
            sort_keys=True,
        )
    )
    return 0 if success else 1


def _restore_sqlite(*, backup: Path, target_database_url: str, replace: bool) -> None:
    target = _sqlite_path(target_database_url)
    if target is None:
        raise ValueError("SQLite restore target must be file-backed.")
    if target.exists() and not replace:
        raise FileExistsError("Restore target exists; pass --replace after verifying the target.")
    target.parent.mkdir(parents=True, exist_ok=True)
    source_connection = sqlite3.connect(str(backup))
    target_connection = sqlite3.connect(str(target))
    try:
        source_connection.backup(target_connection)
    finally:
        target_connection.close()
        source_connection.close()


def _restore_postgresql(*, backup: Path, target_database_url: str) -> None:
    executable = shutil.which("pg_restore")
    if executable is None:
        raise RuntimeError("pg_restore is not available on PATH.")
    subprocess.run(
        [executable, "--clean", "--if-exists", "--dbname", target_database_url, str(backup)],
        check=True,
        capture_output=True,
        text=True,
    )


def _sqlite_path(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite:///"):
        return None
    return Path(database_url.replace("sqlite:///", "", 1)).resolve()


if __name__ == "__main__":
    sys.exit(main())
