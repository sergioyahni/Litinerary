from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


GATE_A_HEAD = "20260928_0010"
GATE_B_HEAD = "20261001_0011"


def test_gate_b_import_audit_migration_upgrades_from_gate_a_head(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'gate-b-migration.db'}"
    config = _alembic_config(database_url)

    command.upgrade(config, GATE_A_HEAD)
    engine = create_engine(database_url)
    assert "itinerary_import_jobs" not in inspect(engine).get_table_names()
    assert "itinerary_import_records" not in inspect(engine).get_table_names()

    command.upgrade(config, "head")
    inspector = inspect(engine)
    assert {"itinerary_import_jobs", "itinerary_import_records"} <= set(
        inspector.get_table_names()
    )
    with engine.begin() as connection:
        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == GATE_B_HEAD

    record_indexes = {
        index["name"] for index in inspector.get_indexes("itinerary_import_records")
    }
    assert "ix_itinerary_import_records_job_id" in record_indexes
    assert "ix_itinerary_import_records_itinerary_id" in record_indexes

    command.downgrade(config, GATE_A_HEAD)
    downgraded = inspect(engine)
    assert "itinerary_import_jobs" not in downgraded.get_table_names()
    assert "itinerary_import_records" not in downgraded.get_table_names()
    with engine.begin() as connection:
        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == GATE_A_HEAD
    engine.dispose()


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config
