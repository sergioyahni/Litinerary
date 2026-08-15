from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.models import BookModel, DestinationModel, ItineraryModel, POIModel
from app.services.seed import seed_database


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
        assert current_revision.scalar_one() == "20260815_0009"
        legacy = connection.execute(
            text(
                """
                SELECT id, owner_user_id, created_by_user_id, visibility, is_public
                FROM itineraries
                WHERE id = 'legacy-private'
                """
            )
        ).mappings().one()
        assert legacy["owner_user_id"] is None
        assert legacy["created_by_user_id"] is None
        assert legacy["visibility"] == "private"
        assert legacy["is_public"] in (0, False)

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
    engine.dispose()


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
