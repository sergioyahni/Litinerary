import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.models import BookModel


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_public_discovery_is_repository_only(client, monkeypatch) -> None:
    _enable_dev_auth(monkeypatch)

    public_books = client.get("/api/books", params={"city_id": "london", "q": "Bleak"})
    public_destinations = client.get("/api/destinations", params={"q": "Edinburgh"})

    assert public_books.status_code == 200
    assert public_books.json() == []
    assert public_destinations.status_code == 200
    assert public_destinations.json() == []


def test_anonymous_users_cannot_invoke_discovery_generation_or_adaptation(
    client,
    monkeypatch,
) -> None:
    _enable_dev_auth(monkeypatch)

    discovery = client.get("/api/discovery/books", params={"city_id": "london", "q": "Bleak"})
    generation = client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "london",
            "bookId": "oliver-twist",
            "durationDays": 1,
            "transportationMode": "walking",
        },
    )
    adaptation = client.post(
        "/api/itineraries/adapt",
        json={
            "sourceItineraryId": "it-london-oliver-twist-1-walking",
            "durationDays": 2,
            "transportationMode": "walking",
        },
    )

    assert discovery.status_code == 401
    assert generation.status_code == 401
    assert adaptation.status_code == 401


def test_authenticated_external_book_generation_publishes_repository_snapshot(
    client,
    db_session,
    monkeypatch,
) -> None:
    _enable_dev_auth(monkeypatch)
    headers = _auth_header("reader-a")
    before_count = db_session.scalar(select(func.count()).select_from(BookModel))

    discovery = client.get(
        "/api/discovery/books",
        params={"city_id": "london", "q": "Bleak"},
        headers=headers,
    )
    assert discovery.status_code == 200
    assert discovery.json()["externalDiscoveryUsed"] is True
    assert discovery.json()["results"][0]["id"] == "external-london-bleak-house"

    generated = client.post(
        "/api/itinerary/generate",
        headers=headers,
        json={
            "destinationId": "london",
            "bookId": "external-london-bleak-house",
            "durationDays": 1,
            "transportationMode": "walking",
        },
    )

    assert generated.status_code == 200
    payload = generated.json()
    itinerary = payload["itinerary"]
    assert payload["matchedExisting"] is False
    assert itinerary["isPublic"] is True
    assert itinerary["visibility"] == "public"
    assert itinerary["bookTitle"] == "Bleak House"
    assert itinerary["bookSourceType"] == "external"
    assert itinerary["createdByMode"] == "registered_user"
    assert db_session.get(BookModel, "external-london-bleak-house") is None
    after_count = db_session.scalar(select(func.count()).select_from(BookModel))
    assert after_count == before_count

    public_books = client.get("/api/books", params={"city_id": "london", "q": "Bleak"})
    public_detail = client.get(f"/api/itineraries/{itinerary['id']}")

    assert public_books.status_code == 200
    assert {book["id"] for book in public_books.json()} == {"external-london-bleak-house"}
    assert public_detail.status_code == 200
    assert public_detail.json()["id"] == itinerary["id"]

    reused = client.post(
        "/api/itinerary/generate",
        headers=headers,
        json={
            "destinationId": "london",
            "bookId": "external-london-bleak-house",
            "durationDays": 1,
            "transportationMode": "walking",
        },
    )
    assert reused.status_code == 200
    assert reused.json()["matchedExisting"] is True
    assert reused.json()["sourceItineraryId"] == itinerary["id"]


def _enable_dev_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "dev")
    monkeypatch.setenv("AUTH_ALLOW_DEV_USER_FALLBACK", "false")
    get_settings.cache_clear()


def _auth_header(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer dev:{user_id}:user:none"}
