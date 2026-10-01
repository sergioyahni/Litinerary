import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.models import BookModel, DestinationModel, ItineraryModel


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_anonymous_repository_consumption_covers_public_contract(client, monkeypatch) -> None:
    _enable_dev_auth(monkeypatch)

    destinations = client.get("/api/destinations", params={"q": "London"})
    books = client.get("/api/books", params={"city_id": "london", "q": "Oliver"})
    itineraries = client.get(
        "/api/itineraries",
        params={
            "city_id": "london",
            "book_id": "oliver-twist",
            "transportation_mode": "walking",
        },
    )
    detail = client.get("/api/itineraries/it-london-oliver-twist-1-walking")

    assert destinations.status_code == 200
    assert {item["id"] for item in destinations.json()} == {"london"}
    assert books.status_code == 200
    assert {item["id"] for item in books.json()} == {"oliver-twist"}
    assert itineraries.status_code == 200
    assert {item["id"] for item in itineraries.json()} == {
        "it-london-oliver-twist-1-walking"
    }
    assert detail.status_code == 200


def test_anonymous_external_destination_discovery_is_denied(client, monkeypatch) -> None:
    _enable_dev_auth(monkeypatch)

    response = client.get("/api/discovery/destinations", params={"q": "Edinburgh"})

    assert response.status_code == 401


def test_external_discovery_alone_does_not_mutate_repository(
    client,
    db_session,
    monkeypatch,
) -> None:
    _enable_dev_auth(monkeypatch)
    headers = {"Authorization": "Bearer dev:gate-b-reader:user:none"}
    before = {
        "books": db_session.scalar(select(func.count()).select_from(BookModel)),
        "destinations": db_session.scalar(select(func.count()).select_from(DestinationModel)),
        "itineraries": db_session.scalar(select(func.count()).select_from(ItineraryModel)),
    }

    book_discovery = client.get(
        "/api/discovery/books",
        params={"city_id": "london", "q": "Bleak"},
        headers=headers,
    )
    destination_discovery = client.get(
        "/api/discovery/destinations",
        params={"q": "Edinburgh"},
        headers=headers,
    )

    assert book_discovery.status_code == 200
    assert book_discovery.json()["externalDiscoveryUsed"] is True
    assert destination_discovery.status_code == 200
    assert destination_discovery.json()["externalDiscoveryUsed"] is True
    after = {
        "books": db_session.scalar(select(func.count()).select_from(BookModel)),
        "destinations": db_session.scalar(select(func.count()).select_from(DestinationModel)),
        "itineraries": db_session.scalar(select(func.count()).select_from(ItineraryModel)),
    }
    assert after == before

    assert client.get("/api/books", params={"city_id": "london", "q": "Bleak"}).json() == []
    assert client.get("/api/destinations", params={"q": "Edinburgh"}).json() == []


def test_authenticated_ordinary_user_keeps_repository_access(client, monkeypatch) -> None:
    _enable_dev_auth(monkeypatch)
    headers = {"Authorization": "Bearer dev:gate-b-reader:user:none"}

    assert client.get("/api/destinations", headers=headers).status_code == 200
    assert client.get("/api/books", headers=headers).status_code == 200
    assert client.get("/api/itineraries", headers=headers).status_code == 200


def _enable_dev_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "dev")
    monkeypatch.setenv("AUTH_ALLOW_DEV_USER_FALLBACK", "false")
    get_settings.cache_clear()
