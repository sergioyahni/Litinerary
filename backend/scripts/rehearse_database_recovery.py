import argparse
import json
import shutil
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.database_readiness import expected_alembic_heads, migration_readiness_status
from app.services.data_integrity import check_database_integrity
from app.services.database_repository import get_itinerary
from app.services.seed import seed_database
from scripts.backup_database import create_database_backup
from scripts.restore_database import CONFIRMATION, restore_database


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a disposable database backup/restore recovery rehearsal."
    )
    parser.add_argument("--work-dir", required=True, help="Disposable rehearsal directory.")
    parser.add_argument(
        "--replace-work-dir",
        action="store_true",
        help="Delete and recreate the disposable rehearsal directory first.",
    )
    args = parser.parse_args()
    work_dir = Path(args.work_dir).resolve()
    if args.replace_work_dir and work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = run_rehearsal(work_dir)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "operation": "rehearse_database_recovery",
                    "errorType": exc.__class__.__name__,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "completed" else 1


def run_rehearsal(work_dir: Path) -> dict:
    database_path = work_dir / "rehearsal.sqlite3"
    backup_path = work_dir / "rehearsal.sqlite3.backup"
    database_url = f"sqlite:///{database_path}"
    _upgrade_to_head(database_url)
    baseline = _seed_and_snapshot(database_url)
    backup = create_database_backup(database_url=database_url, destination=backup_path)
    mutation = _delete_referenced_poi(database_url)
    restore = restore_database(
        backup=backup_path,
        target_database_url=database_url,
        replace=True,
        confirm_restore=CONFIRMATION,
    )
    restored = _snapshot(database_url)
    status = "completed" if baseline == restored and restore["integrity_status"] == "ok" else "failed"
    return {
        "status": status,
        "operation": "rehearse_database_recovery",
        "databaseEngine": "sqlite",
        "alembicHead": expected_alembic_heads(),
        "baseline": baseline,
        "backup": {
            "engine": backup["engine"],
            "backupFormat": backup["backup_format"],
            "path": backup["path"],
        },
        "mutation": mutation,
        "restore": {
            "integrityStatus": restore["integrity_status"],
            "violations": restore["violations"],
            "migrationStatus": restore["migration_status"],
            "currentRevisions": restore["current_revisions"],
        },
        "restored": restored,
    }


def _upgrade_to_head(database_url: str) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def _seed_and_snapshot(database_url: str) -> dict:
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    try:
        with SessionLocal() as db:
            seed_database(db)
        return _snapshot_from_session_factory(SessionLocal)
    finally:
        engine.dispose()


def _snapshot(database_url: str) -> dict:
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    try:
        return _snapshot_from_session_factory(SessionLocal)
    finally:
        engine.dispose()


def _snapshot_from_session_factory(SessionLocal) -> dict:
    with SessionLocal() as db:
        migration = migration_readiness_status(db, expected_heads=expected_alembic_heads())
        violations = check_database_integrity(db)
        try:
            reference = get_itinerary(db, "it-london-oliver-twist-1-walking")
            reference_stop_count = sum(len(day.stops) for day in reference.days) if reference else 0
            reference_id = reference.id if reference else None
        except Exception:
            reference_id = None
            reference_stop_count = 0
        return {
            "counts": {
                "destinations": _count(db, "destinations"),
                "books": _count(db, "books"),
                "pois": _count(db, "pois"),
                "itineraries": _count(db, "itineraries"),
                "itinerary_days": _count(db, "itinerary_days"),
                "itinerary_stops": _count(db, "itinerary_stops"),
            },
            "referenceItinerary": {
                "id": reference_id,
                "stopCount": reference_stop_count,
            },
            "integrityStatus": "ok" if not violations else "failed",
            "violations": sum(item.count for item in violations),
            "migrationStatus": migration["status"],
            "currentRevisions": migration["currentRevisions"],
        }


def _delete_referenced_poi(database_url: str) -> dict:
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    try:
        with SessionLocal() as db:
            poi_id = db.execute(
                text("SELECT poi_id FROM itinerary_stops ORDER BY poi_id LIMIT 1")
            ).scalar_one()
            db.execute(text("DELETE FROM pois WHERE id = :poi_id"), {"poi_id": poi_id})
            db.commit()
        after = _snapshot_from_session_factory(SessionLocal)
        return {
            "deletedPoiId": str(poi_id),
            "integrityStatusAfterMutation": after["integrityStatus"],
            "violationsAfterMutation": after["violations"],
            "countsAfterMutation": after["counts"],
        }
    finally:
        engine.dispose()


def _count(db, table_name: str) -> int:
    return int(db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one())


if __name__ == "__main__":
    sys.exit(main())
