import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine

from app.core.config import get_settings
from app.core.observability import EventName, configure_logging, log_event


def create_database_backup(*, database_url: str, destination: Path) -> dict:
    if destination.exists():
        raise FileExistsError(f"Backup destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if database_url.startswith("sqlite"):
        _backup_sqlite(database_url=database_url, destination=destination)
        return {"engine": "sqlite", "backup_format": "sqlite-backup", "path": str(destination)}
    if database_url.startswith("postgresql"):
        _backup_postgresql(database_url=database_url, destination=destination)
        return {"engine": "postgresql", "backup_format": "pg_dump-custom", "path": str(destination)}
    raise ValueError("Unsupported database dialect for backup.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a safe database backup.")
    parser.add_argument("--destination", required=True, help="Explicit backup destination path.")
    args = parser.parse_args()
    configure_logging()
    settings = get_settings()
    destination = Path(args.destination).resolve()

    try:
        result = create_database_backup(
            database_url=settings.database_url,
            destination=destination,
        )
    except Exception as exc:
        log_event(
            EventName.DATABASE_BACKUP_FAILED,
            category="database_recovery",
            operation="backup_database",
            error_type=exc.__class__.__name__,
            success=False,
        )
        print(
            json.dumps(
                {
                    "status": "failed",
                    "operation": "backup_database",
                    "errorType": exc.__class__.__name__,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1

    log_event(
        EventName.DATABASE_BACKUP_COMPLETED,
        category="database_recovery",
        operation="backup_database",
        database_engine=result["engine"],
        backup_format=result["backup_format"],
        success=True,
    )
    print(
        json.dumps(
            {
                "status": "completed",
                "operation": "backup_database",
                "databaseEngine": result["engine"],
                "backupFormat": result["backup_format"],
                "backupPath": result["path"],
            },
            sort_keys=True,
        )
    )
    return 0


def _backup_sqlite(*, database_url: str, destination: Path) -> None:
    engine = create_engine(database_url)
    raw_connection = engine.raw_connection()
    backup_connection = sqlite3.connect(str(destination))
    try:
        try:
            source = raw_connection.driver_connection
        except AttributeError:
            source = raw_connection.connection
        source.backup(backup_connection)
    finally:
        backup_connection.close()
        raw_connection.close()
        engine.dispose()


def _backup_postgresql(*, database_url: str, destination: Path) -> None:
    executable = shutil.which("pg_dump")
    if executable is None:
        raise RuntimeError("pg_dump is not available on PATH.")
    subprocess.run(
        [executable, "--format=custom", "--file", str(destination), database_url],
        check=True,
        capture_output=True,
        text=True,
    )


if __name__ == "__main__":
    sys.exit(main())
