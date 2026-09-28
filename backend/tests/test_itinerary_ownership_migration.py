import importlib
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine

from app.models import BookModel, DestinationModel, ItineraryModel, POIModel
from app.services.seed import seed_database


def test_itinerary_ownership_migration_uses_portable_boolean_literal(monkeypatch) -> None:
    migration = importlib.import_module(
        "migrations.versions.20260815_0008_itinerary_owner_constraints"
    )
    statements: list[str] = []

    class BatchAlterTableStub:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def create_foreign_key(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(migration.op, "execute", lambda statement: statements.append(statement))
    monkeypatch.setattr(
        migration.op,
        "batch_alter_table",
        lambda *args, **kwargs: BatchAlterTableStub(),
    )
    monkeypatch.setattr(migration.op, "create_index", lambda *args, **kwargs: None)

    migration.upgrade()

    boolean_updates = [
        statement
        for statement in statements
        if "UPDATE itineraries" in statement and "SET is_public" in statement
    ]
    assert len(boolean_updates) == 1
    assert "SET is_public = FALSE" in boolean_updates[0]
    assert "SET is_public = 0" not in boolean_updates[0]


def test_itinerary_ownership_migration_preserves_legacy_rows_and_reaches_head(
    tmp_path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "ownership-migration.db"
    database_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("LITINERARY_DATABASE_URL", database_url)
    config = _alembic_config(database_url)

    command.upgrade(config, "20260614_0007")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO destinations (
                    id, name, country, description, latitude, longitude, supported
                )
                VALUES (
                    'legacy-city', 'Legacy City', 'Testland',
                    'Legacy migration city.', 1.0, 2.0, 1
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO books (
                    id, title, author, description, public_domain, themes
                )
                VALUES (
                    'legacy-book', 'Legacy Book', 'A. Writer',
                    'Legacy migration book.', 1, '[]'
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO itineraries (
                    id, destination_id, book_id, title, summary, duration_days,
                    transportation_mode, is_public, generated_from, source_type,
                    adaptation_notes, created_at, owner_user_id, visibility,
                    created_by_mode, created_by_user_id, subscriber_only,
                    provenance_metadata
                )
                VALUES (
                    'legacy-private', 'legacy-city', 'legacy-book',
                    'Legacy Private', 'Legacy private row.', 1, 'walking',
                    0, 'new_generation', 'new_mock_generation', '[]',
                    '2026-08-15T00:00:00+00:00', 'missing-owner', 'private',
                    'registered_user', 'missing-owner', 0, '{}'
                )
                """
            )
        )

    command.upgrade(config, "head")

    with engine.begin() as connection:
        current_revision = connection.execute(text("SELECT version_num FROM alembic_version"))
        assert current_revision.scalar_one() == "20260928_0010"
        legacy = connection.execute(
            text(
                """
                SELECT id, owner_user_id, created_by_user_id, visibility, is_public,
                       book_title, destination_name
                FROM itineraries
                WHERE id = 'legacy-private'
                """
            )
        ).mappings().one()
        assert legacy["owner_user_id"] is None
        assert legacy["created_by_user_id"] is None
        assert legacy["visibility"] == "private"
        assert legacy["is_public"] in (0, False)
        assert legacy["book_title"] == "Legacy Book"
        assert legacy["destination_name"] == "Legacy City"

    inspector = inspect(engine)
    indexes = {index["name"] for index in inspector.get_indexes("itineraries")}
    foreign_keys = inspector.get_foreign_keys("itineraries")
    assert "ix_itineraries_public_visibility" in indexes
    assert "ix_itineraries_owner_visibility" in indexes
    assert "ix_itineraries_source_itinerary_id" in indexes
    assert "usage_limit_counters" in inspector.get_table_names()
    usage_indexes = {index["name"] for index in inspector.get_indexes("usage_limit_counters")}
    assert "ix_usage_limit_counters_subject_action" in usage_indexes
    assert "ix_usage_limit_counters_window_end" in usage_indexes
    assert any(
        key["referred_table"] == "users" and key["constrained_columns"] == ["owner_user_id"]
        for key in foreign_keys
    )

    command.downgrade(config, "20260815_0009")
    downgraded_inspector = inspect(engine)
    downgraded_columns = {
        column["name"] for column in downgraded_inspector.get_columns("itineraries")
    }
    downgraded_foreign_keys = downgraded_inspector.get_foreign_keys("itineraries")
    assert "book_title" not in downgraded_columns
    assert any(
        key["referred_table"] == "books" and key["constrained_columns"] == ["book_id"]
        for key in downgraded_foreign_keys
    )
    with engine.begin() as connection:
        assert connection.execute(
            text("SELECT COUNT(*) FROM itineraries WHERE id = 'legacy-private'")
        ).scalar_one() == 1

    command.upgrade(config, "head")
    with engine.begin() as connection:
        restored = connection.execute(
            text(
                """
                SELECT book_title, destination_name
                FROM itineraries
                WHERE id = 'legacy-private'
                """
            )
        ).mappings().one()
        assert restored["book_title"] == "Legacy Book"
        assert restored["destination_name"] == "Legacy City"
    engine.dispose()


def test_external_book_itinerary_blocks_downgrade_before_schema_mutation(
    tmp_path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "external-book-downgrade.db"
    database_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("LITINERARY_DATABASE_URL", database_url)
    config = _alembic_config(database_url)

    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    event.listen(Engine, "connect", enable_sqlite_foreign_keys)
    engine = None
    try:
        command.upgrade(config, "head")
        engine = create_engine(database_url)
        assert not any(
            key["referred_table"] == "books" and key["constrained_columns"] == ["book_id"]
            for key in inspect(engine).get_foreign_keys("itineraries")
        )

        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO destinations (
                        id, name, country, description, latitude, longitude, supported
                    )
                    VALUES (
                        'external-city', 'External City', 'Testland',
                        'External itinerary destination.', 1.0, 2.0, 1
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO itineraries (
                        id, destination_id, book_id, title, summary, duration_days,
                        transportation_mode, is_public, generated_from, source_type,
                        adaptation_notes, created_at, visibility, created_by_mode,
                        subscriber_only, provenance_metadata, book_title, book_author,
                        book_description, book_public_domain, book_themes,
                        book_source_type, book_provider_id, book_provenance_metadata,
                        destination_name, destination_country, destination_description,
                        destination_latitude, destination_longitude,
                        destination_source_type, destination_provenance_metadata
                    )
                    VALUES (
                        'external-itinerary', 'external-city', 'external-book',
                        'External Book Route', 'Generated from transient metadata.', 1,
                        'walking', 1, 'new_generation', 'new_mock_generation', '[]',
                        '2026-09-28T00:00:00+00:00', 'public', 'registered_user', 0, '{}',
                        'External Book', 'A. External', 'Transient book metadata.', 1,
                        '[]', 'external', 'provider:external-book', '{}',
                        'External City', 'Testland', 'External itinerary destination.',
                        1.0, 2.0, 'repository', '{}'
                    )
                    """
                )
            )
            assert connection.execute(
                text("SELECT COUNT(*) FROM books WHERE id = 'external-book'")
            ).scalar_one() == 0

        with pytest.raises(RuntimeError, match="cannot represent external-book snapshots alone"):
            command.downgrade(config, "20260815_0009")

        inspector = inspect(engine)
        columns = {column["name"] for column in inspector.get_columns("itineraries")}
        assert "book_title" in columns
        assert "destination_name" in columns
        with engine.begin() as connection:
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == "20260928_0010"
            assert connection.execute(
                text("SELECT COUNT(*) FROM itineraries WHERE id = 'external-itinerary'")
            ).scalar_one() == 1
            assert connection.execute(
                text("SELECT COUNT(*) FROM books WHERE id = 'external-book'")
            ).scalar_one() == 0
            assert connection.execute(text("SELECT COUNT(*) FROM itineraries")).scalar_one() == 1
    finally:
        if engine is not None:
            engine.dispose()
        event.remove(Engine, "connect", enable_sqlite_foreign_keys)


def test_postgresql_guard_rejects_before_any_schema_operation(monkeypatch) -> None:
    migration = importlib.import_module(
        "migrations.versions.20260928_0010_public_itinerary_snapshots"
    )
    operations: list[str] = []

    class DialectStub:
        name = "postgresql"

    class BindStub:
        dialect = DialectStub()

        def scalar(self, statement) -> int:
            assert "LEFT JOIN books" in str(statement)
            return 2

    monkeypatch.setattr(migration.op, "get_bind", BindStub)
    monkeypatch.setattr(
        migration.op,
        "drop_column",
        lambda *args, **kwargs: operations.append("drop_column"),
    )
    monkeypatch.setattr(
        migration.op,
        "create_foreign_key",
        lambda *args, **kwargs: operations.append("create_foreign_key"),
    )

    with pytest.raises(RuntimeError, match="found 2 itinerary row"):
        migration.downgrade()

    assert operations == []


def test_seed_database_remains_valid_at_current_metadata_head(db_session) -> None:
    seed_database(db_session)

    assert db_session.query(DestinationModel).count() >= 5
    assert db_session.query(BookModel).count() >= 10
    assert db_session.query(POIModel).count() >= 13
    assert db_session.query(ItineraryModel).count() >= 2


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config
