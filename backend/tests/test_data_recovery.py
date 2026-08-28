import os
import subprocess
import sys
import json

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.services.data_integrity import check_database_integrity
from app.services.seed import seed_database


def _seeded_database(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'recovery-test.sqlite3'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        seed_database(db)
    return database_url, TestingSessionLocal, engine


def test_integrity_checker_reports_ok_for_seeded_database(tmp_path) -> None:
    _, session_factory, engine = _seeded_database(tmp_path)

    with session_factory() as db:
        violations = check_database_integrity(db)

    assert violations == []
    engine.dispose()


def test_integrity_checker_detects_missing_poi_reference(tmp_path) -> None:
    _, session_factory, engine = _seeded_database(tmp_path)

    with session_factory() as db:
        poi_id = db.execute(text("SELECT poi_id FROM itinerary_stops LIMIT 1")).scalar_one()
        db.execute(text("DELETE FROM pois WHERE id = :poi_id"), {"poi_id": poi_id})
        db.commit()

    with session_factory() as db:
        violations = check_database_integrity(db)

    assert any(item.check == "itinerary_stops_missing_poi" for item in violations)
    engine.dispose()


def test_backup_and_restore_commands_round_trip_disposable_sqlite(tmp_path) -> None:
    database_url, session_factory, engine = _seeded_database(tmp_path)
    backup_path = tmp_path / "recovery-test.sqlite3.backup"
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env = {
        **os.environ,
        "APP_ENV": "test",
        "LITINERARY_DATABASE_URL": database_url,
    }

    backup = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.backup_database",
            "--destination",
            str(backup_path),
        ],
        cwd=backend_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    with session_factory() as db:
        db.execute(text("DELETE FROM itinerary_stops"))
        db.commit()
        assert db.execute(text("SELECT COUNT(*) FROM itinerary_stops")).scalar_one() == 0
    engine.dispose()

    restore = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.restore_database",
            "--backup",
            str(backup_path),
            "--target-database-url",
            database_url,
            "--replace",
            "--confirm-restore",
            "RESTORE",
        ],
        cwd=backend_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    restore_payload = _last_json_line(restore.stdout)
    assert json.loads(backup.stdout)["status"] == "completed"
    assert restore_payload["integrityStatus"] == "ok"
    assert restore_payload["migrationStatus"] == "missing"
    assert "sqlite:///" not in backup.stdout
    assert "sqlite:///" not in restore.stdout


def test_restore_command_requires_confirmation(tmp_path) -> None:
    database_url, _, engine = _seeded_database(tmp_path)
    backup_path = tmp_path / "empty.sqlite3.backup"
    backup_path.write_bytes(b"not-a-real-sqlite-backup")
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.restore_database",
            "--backup",
            str(backup_path),
            "--target-database-url",
            database_url,
            "--replace",
            "--confirm-restore",
            "NOPE",
        ],
        cwd=backend_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert _last_json_line(result.stderr)["errorType"] == "ValueError"
    engine.dispose()


def test_recovery_rehearsal_uses_real_database_operations(tmp_path) -> None:
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    work_dir = tmp_path / "rehearsal"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.rehearse_database_recovery",
            "--work-dir",
            str(work_dir),
            "--replace-work-dir",
        ],
        cwd=backend_root,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "completed"
    assert payload["databaseEngine"] == "sqlite"
    assert payload["mutation"]["integrityStatusAfterMutation"] == "failed"
    assert payload["mutation"]["violationsAfterMutation"] > 0
    assert payload["baseline"] == payload["restored"]
    assert payload["restore"]["integrityStatus"] == "ok"
    assert payload["restore"]["migrationStatus"] == "current"


def _last_json_line(value: str) -> dict:
    for line in reversed(value.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
    raise AssertionError(f"No JSON object found in output: {value}")
