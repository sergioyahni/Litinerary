from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app
from app.models import domain  # noqa: F401
from app.services import database_repository
from app.services.seed import seed_database


def test_adapted_itinerary_is_saved_to_database(client, db_session) -> None:
    response = client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "london",
            "bookId": "oliver-twist",
            "durationDays": 2,
            "transportationMode": "public_transport",
        },
    )

    assert response.status_code == 200
    itinerary = response.json()["itinerary"]
    saved = database_repository.get_itinerary(db_session, itinerary["id"])

    assert saved is not None
    assert saved.sourceType == "adapted_match"
    assert saved.sourceItineraryId == "it-london-oliver-twist-1-walking"
    assert saved.isPublic is True
    assert saved.adaptationNotes


def test_new_mock_generation_is_saved_to_database(client, db_session) -> None:
    response = client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "paris",
            "bookId": "les-miserables",
            "durationDays": 2,
            "transportationMode": "walking",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    saved = database_repository.get_itinerary(db_session, payload["itinerary"]["id"])

    assert payload["matchedExisting"] is False
    assert saved is not None
    assert saved.sourceType == "new_mock_generation"
    assert saved.sourceItineraryId is None
    assert saved.isPublic is True


def test_saved_itinerary_can_be_returned_as_later_exact_match(client) -> None:
    first_response = client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "paris",
            "bookId": "les-miserables",
            "durationDays": 2,
            "transportationMode": "walking",
        },
    )
    second_response = client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "paris",
            "bookId": "les-miserables",
            "durationDays": 2,
            "transportationMode": "walking",
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["matchedExisting"] is False
    assert second_response.json()["matchedExisting"] is True
    assert second_response.json()["sourceItineraryId"] == first_response.json()["itinerary"]["id"]
    assert second_response.json()["itinerary"]["sourceType"] == "exact_match"


def test_generated_itinerary_survives_new_test_client_with_same_database(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'persistent-repository.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as seed_session:
        seed_database(seed_session)

    def override_get_db():
        with TestingSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as first_client:
            generated = first_client.post(
                "/api/itinerary/generate",
                json={
                    "destinationId": "paris",
                    "bookId": "les-miserables",
                    "durationDays": 2,
                    "transportationMode": "walking",
                },
            ).json()["itinerary"]

        with TestClient(app) as restarted_client:
            detail = restarted_client.get(f"/api/itineraries/{generated['id']}")
            listing = restarted_client.get(
                "/api/itineraries",
                params={"city_id": "paris", "book_id": "les-miserables"},
            )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert detail.status_code == 200
    assert detail.json()["id"] == generated["id"]
    assert listing.status_code == 200
    assert generated["id"] in {itinerary["id"] for itinerary in listing.json()}
