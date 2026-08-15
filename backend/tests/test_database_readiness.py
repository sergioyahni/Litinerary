from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core import database as database_module
from app.core.config import Settings
from app.core.database import Base
from app.core.database_readiness import (
    database_readiness_status,
    expected_alembic_heads,
    validate_database_startup,
)
from app.models import domain  # noqa: F401
from app.services import mock_repository
from app.services.seed import seed_database


DEPLOYED_ENVS = ["internal", "beta", "staging", "production"]


def test_development_default_database_configuration_remains_allowed() -> None:
    settings = Settings(app_env="development", database_url_configured=False)

    assert settings.database_configuration_validation_errors() == []


def test_test_database_configuration_can_use_explicit_temporary_sqlite(tmp_path) -> None:
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{tmp_path / 'litinerary-test.db'}",
        database_url_configured=True,
    )

    assert settings.database_configuration_validation_errors() == []


@pytest.mark.parametrize("app_env", DEPLOYED_ENVS)
def test_deployed_database_url_is_required(app_env: str) -> None:
    settings = Settings(app_env=app_env, database_url_configured=False)

    errors = settings.database_configuration_validation_errors()

    assert "LITINERARY_DATABASE_URL is required in deployed environments." in errors


@pytest.mark.parametrize("app_env", DEPLOYED_ENVS)
def test_deployed_default_sqlite_fallback_is_rejected(app_env: str) -> None:
    settings = Settings(
        app_env=app_env,
        database_url="sqlite:///./litinerary.db",
        database_url_configured=False,
    )

    errors = settings.database_configuration_validation_errors()

    assert any("default local SQLite fallback" in error for error in errors)


def test_malformed_database_url_is_rejected_without_echoing_value() -> None:
    settings = Settings(
        app_env="production",
        database_url="://user:super-secret@example.test/db",
        database_url_configured=True,
    )

    errors = settings.database_configuration_validation_errors()

    assert errors == ["LITINERARY_DATABASE_URL is malformed or unsupported."]
    assert "super-secret" not in " ".join(errors)


def test_representative_valid_deployed_database_config_passes_without_connecting() -> None:
    settings = Settings(
        app_env="production",
        database_url="postgresql+psycopg://user:super-secret@example.test/litinerary",
        database_url_configured=True,
    )

    assert settings.database_configuration_validation_errors() == []
    assert settings.safe_database_dialect() == "postgresql+psycopg"


def test_deployed_init_db_create_all_shortcut_is_blocked(monkeypatch) -> None:
    monkeypatch.setattr(
        database_module,
        "settings",
        Settings(
            app_env="production",
            database_url="sqlite:///explicit-production-test.db",
            database_url_configured=True,
        ),
    )

    with pytest.raises(RuntimeError) as exc_info:
        database_module.init_db()

    assert "Alembic migrations explicitly" in str(exc_info.value)


def test_current_migration_head_reports_ready(tmp_path) -> None:
    database_url = _migrate(tmp_path / "current.db", "head")
    store, engine = _session_factory(database_url)

    try:
        with store() as db:
            status = database_readiness_status(
                db,
                settings=Settings(
                    app_env="staging",
                    database_url=database_url,
                    database_url_configured=True,
                ),
            )
    finally:
        engine.dispose()

    assert status["status"] == "ok"
    assert status["connectivity"] == "ok"
    assert status["migrations"]["status"] == "current"
    assert status["migrations"]["currentRevisions"] == expected_alembic_heads()


def test_database_one_migration_behind_reports_not_ready(tmp_path) -> None:
    database_url = _migrate(tmp_path / "behind.db", "20260815_0008")
    store, engine = _session_factory(database_url)

    try:
        with store() as db:
            status = database_readiness_status(
                db,
                settings=Settings(
                    app_env="staging",
                    database_url=database_url,
                    database_url_configured=True,
                ),
            )
    finally:
        engine.dispose()

    assert status["status"] == "error"
    assert status["migrations"]["status"] == "behind"


def test_empty_database_reports_missing_migration(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'empty.db'}"
    store, engine = _session_factory(database_url)

    try:
        with store() as db:
            status = database_readiness_status(
                db,
                settings=Settings(
                    app_env="beta",
                    database_url=database_url,
                    database_url_configured=True,
                ),
            )
    finally:
        engine.dispose()

    assert status["status"] == "error"
    assert status["migrations"]["status"] == "missing"


def test_schema_created_without_alembic_revision_reports_not_ready(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'create-all.db'}"
    store, engine = _session_factory(database_url)
    Base.metadata.create_all(bind=engine)

    try:
        with store() as db:
            status = database_readiness_status(
                db,
                settings=Settings(
                    app_env="production",
                    database_url=database_url,
                    database_url_configured=True,
                ),
            )
    finally:
        engine.dispose()

    assert status["status"] == "error"
    assert status["migrations"]["status"] == "missing"


def test_unknown_database_revision_reports_not_ready(tmp_path) -> None:
    database_url = _migrate(tmp_path / "unknown.db", "head")
    store, engine = _session_factory(database_url)
    with engine.begin() as connection:
        connection.execute(text("UPDATE alembic_version SET version_num = 'not_a_real_revision'"))

    try:
        with store() as db:
            status = database_readiness_status(
                db,
                settings=Settings(
                    app_env="staging",
                    database_url=database_url,
                    database_url_configured=True,
                ),
            )
    finally:
        engine.dispose()

    assert status["status"] == "error"
    assert status["migrations"]["status"] == "unknown_revision"
    assert status["migrations"]["unknownRevisions"] == ["not_a_real_revision"]


def test_connection_failure_reports_not_ready_without_url_leak(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'missing' / 'unreachable.db'}"
    store, engine = _session_factory(database_url)

    try:
        with store() as db:
            status = database_readiness_status(
                db,
                settings=Settings(
                    app_env="production",
                    database_url=database_url,
                    database_url_configured=True,
                ),
            )
    finally:
        engine.dispose()

    assert status["status"] == "error"
    assert status["connectivity"] == "error"
    assert "unreachable.db" not in str(status)


def test_validate_database_startup_passes_for_deployed_current_head(tmp_path) -> None:
    database_url = _migrate(tmp_path / "startup-current.db", "head")

    validate_database_startup(
        Settings(app_env="beta", database_url=database_url, database_url_configured=True)
    )


def test_validate_database_startup_fails_for_deployed_missing_url() -> None:
    with pytest.raises(RuntimeError) as exc_info:
        validate_database_startup(Settings(app_env="production", database_url_configured=False))

    assert "LITINERARY_DATABASE_URL" in str(exc_info.value)


def test_validate_database_startup_fails_for_deployed_unmigrated_database(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'startup-empty.db'}"

    with pytest.raises(RuntimeError) as exc_info:
        validate_database_startup(
            Settings(app_env="staging", database_url=database_url, database_url_configured=True)
        )

    assert "migrations=missing" in str(exc_info.value)


def test_validate_database_startup_fails_for_deployed_unavailable_database(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'missing' / 'startup-unreachable.db'}"

    with pytest.raises(RuntimeError) as exc_info:
        validate_database_startup(
            Settings(app_env="staging", database_url=database_url, database_url_configured=True)
        )

    assert "connectivity=error" in str(exc_info.value)
    assert "startup-unreachable.db" not in str(exc_info.value)


def test_local_empty_database_can_still_use_mock_fallback(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    mock_repository.get_settings.cache_clear()
    database_url = f"sqlite:///{tmp_path / 'local-empty.db'}"
    store, engine = _session_factory(database_url)

    try:
        with store() as db:
            assert mock_repository._use_database(db) is False
    finally:
        engine.dispose()


def test_deployed_empty_database_does_not_use_mock_fallback(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    mock_repository.get_settings.cache_clear()
    database_url = f"sqlite:///{tmp_path / 'deployed-empty.db'}"
    store, engine = _session_factory(database_url)
    Base.metadata.create_all(bind=engine)

    try:
        with store() as db:
            assert mock_repository._use_database(db) is True
    finally:
        engine.dispose()


def test_seed_preserves_empty_usage_history_and_reference_data(tmp_path) -> None:
    database_url = _migrate(tmp_path / "seed.db", "head")
    store, engine = _session_factory(database_url)

    try:
        with store() as db:
            seed_database(db)
            counts = {
                name: db.execute(text(f"SELECT count(*) FROM {name}")).scalar_one()
                for name in ["destinations", "books", "pois", "itineraries"]
            }
            usage_count = db.execute(text("SELECT count(*) FROM usage_limit_counters")).scalar_one()
    finally:
        engine.dispose()

    assert counts == {
        "destinations": 5,
        "books": 10,
        "pois": 13,
        "itineraries": 2,
    }
    assert usage_count == 0


def _migrate(db_path: Path, revision: str) -> str:
    database_url = f"sqlite:///{db_path}"
    config = _alembic_config(database_url)
    command.upgrade(config, revision)
    return database_url


def _session_factory(database_url: str):
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    return sessionmaker(autocommit=False, autoflush=False, bind=engine), engine


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config
