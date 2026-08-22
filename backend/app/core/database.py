from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
configuration_errors = settings.database_configuration_validation_errors()
if configuration_errors:
    raise RuntimeError(
        f"Database configuration is incomplete for APP_ENV={settings.app_env}: "
        + " ".join(configuration_errors)
    )
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    if settings.is_deployed_environment:
        raise RuntimeError(
            "init_db/create_all is not allowed in deployed environments; "
            "run Alembic migrations explicitly."
        )
    from app.models import domain  # noqa: F401

    Base.metadata.create_all(bind=engine)
