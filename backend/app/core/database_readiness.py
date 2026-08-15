from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings


def database_readiness_status(
    db: Session,
    settings: Settings | None = None,
) -> dict[str, Any]:
    resolved = settings or get_settings()
    expected_heads = expected_alembic_heads()
    status: dict[str, Any] = {
        "status": "ok",
        "required": resolved.is_deployed_environment,
        "configured": resolved.database_url_configured,
        "dialect": resolved.safe_database_dialect(),
        "connectivity": "unknown",
        "configurationErrors": resolved.database_configuration_validation_errors(),
        "migrations": {
            "status": "unknown",
            "currentRevisions": [],
            "expectedHeads": expected_heads,
        },
    }

    if status["configurationErrors"]:
        status["status"] = "error"
        status["connectivity"] = "not_checked"
        status["migrations"]["status"] = "not_checked"
        return status

    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        db.rollback()
        status["status"] = "error"
        status["connectivity"] = "error"
        status["errorType"] = exc.__class__.__name__
        status["migrations"]["status"] = "not_checked"
        return status

    status["connectivity"] = "ok"
    migration_status = migration_readiness_status(db, expected_heads=expected_heads)
    status["migrations"] = migration_status

    if resolved.is_deployed_environment and migration_status["status"] != "current":
        status["status"] = "error"

    return status


def migration_readiness_status(
    db: Session,
    *,
    expected_heads: list[str] | None = None,
) -> dict[str, Any]:
    heads = expected_heads or expected_alembic_heads()
    known_revisions = known_alembic_revisions()
    result: dict[str, Any] = {
        "status": "unknown",
        "currentRevisions": [],
        "expectedHeads": heads,
    }

    try:
        bind = db.get_bind()
        if not inspect(bind).has_table("alembic_version"):
            result["status"] = "missing"
            return result
        rows = db.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
    except SQLAlchemyError as exc:
        db.rollback()
        result["status"] = "error"
        result["errorType"] = exc.__class__.__name__
        return result

    revisions = sorted(str(row) for row in rows if row)
    result["currentRevisions"] = revisions
    if not revisions:
        result["status"] = "missing"
        return result

    unknown = [revision for revision in revisions if revision not in known_revisions]
    if unknown:
        result["status"] = "unknown_revision"
        result["unknownRevisions"] = unknown
        return result

    result["status"] = "current" if set(revisions) == set(heads) else "behind"
    return result


def validate_database_startup(settings: Settings | None = None) -> None:
    resolved = settings or get_settings()
    errors = resolved.database_configuration_validation_errors()
    if errors:
        raise RuntimeError(
            f"Database configuration is incomplete for APP_ENV={resolved.app_env}: "
            + " ".join(errors)
        )

    if not resolved.is_deployed_environment:
        return

    connect_args = {"check_same_thread": False} if resolved.database_url.startswith("sqlite") else {}
    engine = create_engine(resolved.database_url, connect_args=connect_args)
    try:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        with SessionLocal() as db:
            status = database_readiness_status(db, settings=resolved)
    finally:
        engine.dispose()

    if status["status"] != "ok":
        migration_status = status["migrations"]["status"]
        raise RuntimeError(
            f"Database is not ready for APP_ENV={resolved.app_env}: "
            f"connectivity={status['connectivity']} migrations={migration_status}."
        )


def expected_alembic_heads() -> list[str]:
    return sorted(_script_directory().get_heads())


def known_alembic_revisions() -> set[str]:
    return {revision.revision for revision in _script_directory().walk_revisions()}


def _script_directory() -> ScriptDirectory:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "migrations"))
    return ScriptDirectory.from_config(config)
