from collections.abc import Generator
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db
from app.data import mock_data
from app.main import app
from app.models import domain  # noqa: F401
from app.services.seed import seed_database
from app.services.usage_policy import get_usage_guard


BASE_ITINERARIES = deepcopy(mock_data.ITINERARIES)


@pytest.fixture(autouse=True)
def reset_mock_repository() -> None:
    get_usage_guard.cache_clear()
    mock_data.ITINERARIES[:] = deepcopy(BASE_ITINERARIES)
    yield
    get_usage_guard.cache_clear()


@pytest.fixture
def db_session(tmp_path) -> Generator[Session, None, None]:
    database_url = f"sqlite:///{tmp_path / 'litinerary-test.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        seed_database(db)
        yield db

    engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
