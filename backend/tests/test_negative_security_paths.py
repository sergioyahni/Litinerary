import pytest

from app.core.config import get_settings
from app.models import BookModel, DestinationModel, POIModel
from app.services import mock_repository
from app.services.ai_types import JudgeValidationResult
from app.services.mock_ai_service import get_ai_pipeline
from app.services.poi_verification import get_poi_verification_adapter
from app.services.vector_service import get_vector_service


@pytest.fixture(autouse=True)
def clear_cached_services():
    get_settings.cache_clear()
    get_ai_pipeline.cache_clear()
    get_vector_service.cache_clear()
    get_poi_verification_adapter.cache_clear()
    yield
    get_settings.cache_clear()
    get_ai_pipeline.cache_clear()
    get_vector_service.cache_clear()
    get_poi_verification_adapter.cache_clear()


def test_invalid_public_catalog_and_repository_inputs_return_errors(client) -> None:
    bad_destination_books = client.get("/api/books", params={"city_id": "atlantis"})
    bad_repository_destination = client.get("/api/itineraries", params={"city_id": "atlantis"})
    bad_repository_book = client.get("/api/itineraries", params={"book_id": "not-a-book"})
    bad_itinerary = client.get("/api/itineraries/not-a-real-itinerary")

    assert bad_destination_books.status_code == 404
    assert bad_repository_destination.status_code == 404
    assert bad_repository_book.status_code == 404
    assert bad_itinerary.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {
            "destinationId": "london",
            "bookId": "oliver-twist",
            "durationDays": 1,
            "transportationMode": "hoverboard",
        },
        {
            "destinationId": "london",
            "bookId": "oliver-twist",
            "durationDays": 0,
            "transportationMode": "walking",
        },
        {
            "destinationId": "london",
            "bookId": "oliver-twist",
            "durationDays": 8,
            "transportationMode": "walking",
        },
        {"destinationId": "london"},
    ],
)
def test_malformed_generation_requests_are_rejected(client, payload) -> None:
    response = client.post("/api/itinerary/generate", json=payload)

    assert response.status_code == 422


def test_generation_rejects_unknown_destination_and_book(client) -> None:
    unknown_destination = client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "atlantis",
            "bookId": "oliver-twist",
            "durationDays": 1,
            "transportationMode": "walking",
        },
    )
    unknown_book = client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "london",
            "bookId": "not-a-book",
            "durationDays": 1,
            "transportationMode": "walking",
        },
    )
    unavailable_book = client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "london",
            "bookId": "les-miserables",
            "durationDays": 1,
            "transportationMode": "walking",
        },
    )

    assert unknown_destination.status_code == 404
    assert unknown_book.status_code == 404
    assert unavailable_book.status_code == 400


def test_generation_returns_404_when_no_local_pois_are_available(client, db_session) -> None:
    destination = DestinationModel(
        id="empty-city",
        name="Empty City",
        country="Nowhere",
        description="A seeded test destination without POIs.",
        latitude=10.0,
        longitude=10.0,
        supported=True,
    )
    book = BookModel(
        id="empty-book",
        title="Empty Book",
        author="Nobody",
        description="A seeded test book without POIs.",
        public_domain=True,
        themes=[],
        destinations=[destination],
    )
    db_session.add_all([destination, book])
    db_session.commit()

    response = client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "empty-city",
            "bookId": "empty-book",
            "durationDays": 1,
            "transportationMode": "walking",
        },
    )

    assert response.status_code == 404
    assert "No mock POIs" in response.json()["detail"]


def test_mock_judge_rejection_returns_clear_backend_error(client, monkeypatch) -> None:
    class RejectingPipeline:
        def adapt_candidate_itinerary(self, source, request):
            return source

        def validate_itinerary(self, itinerary):
            return JudgeValidationResult(approved=False, reasons=["Route is not feasible."])

    monkeypatch.setattr(mock_repository, "get_ai_pipeline", lambda: RejectingPipeline())

    response = client.post(
        "/api/itineraries/adapt",
        json={
            "sourceItineraryId": "it-london-oliver-twist-1-walking",
            "durationDays": 1,
            "transportationMode": "walking",
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"]["reasons"] == ["Route is not feasible."]


def test_invalid_user_review_and_preference_payloads_are_rejected(client) -> None:
    client.post("/api/users", json={"id": "payload-reader"})

    invalid_review = client.post(
        "/api/users/payload-reader/reviews",
        json={"itineraryId": "it-london-oliver-twist-1-walking", "rating": 6},
    )
    missing_itinerary_review = client.post(
        "/api/users/payload-reader/reviews",
        json={"rating": 5, "comment": "Missing itinerary."},
    )
    invalid_preference = client.post(
        "/api/users/payload-reader/preferences",
        json={"key": "", "value": ["not", "an", "object"]},
    )

    assert invalid_review.status_code == 422
    assert missing_itinerary_review.status_code == 422
    assert invalid_preference.status_code == 422


def test_invalid_bookmark_operations_return_errors(client) -> None:
    client.post("/api/users", json={"id": "bookmark-reader"})

    unknown_user = client.post(
        "/api/users/not-a-user/bookmarks/it-london-oliver-twist-1-walking"
    )
    unknown_itinerary = client.post("/api/users/bookmark-reader/bookmarks/not-an-itinerary")

    assert unknown_user.status_code == 404
    assert unknown_itinerary.status_code == 404


def test_duplicate_bookmarks_are_idempotent_and_nonexistent_remove_is_safe(client) -> None:
    client.post("/api/users", json={"id": "bookmark-reader"})

    first = client.post("/api/users/bookmark-reader/bookmarks/it-london-oliver-twist-1-walking")
    second = client.post("/api/users/bookmark-reader/bookmarks/it-london-oliver-twist-1-walking")
    remove_missing = client.delete("/api/users/bookmark-reader/bookmarks/not-an-itinerary")

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(second.json()["itineraries"]) == 1
    assert remove_missing.status_code == 200
    assert len(remove_missing.json()["itineraries"]) == 1


def test_user_bookmark_collections_are_scoped_by_path_user_id(client) -> None:
    client.post("/api/users", json={"id": "reader-one"})
    client.post("/api/users", json={"id": "reader-two"})

    client.post("/api/users/reader-one/bookmarks/it-london-oliver-twist-1-walking")

    reader_one = client.get("/api/users/reader-one/bookmarks")
    reader_two = client.get("/api/users/reader-two/bookmarks")

    assert {item["id"] for item in reader_one.json()["itineraries"]} == {
        "it-london-oliver-twist-1-walking"
    }
    assert reader_two.json()["itineraries"] == []


def test_user_specific_recommendations_do_not_mix_vector_interest_metadata(client) -> None:
    get_vector_service.cache_clear()
    client.post("/api/users", json={"id": "interest-reader"})
    client.post("/api/users", json={"id": "other-reader"})
    client.post(
        "/api/users/interest-reader/preferences",
        json={"key": "travel", "value": {"cityId": "london", "bookId": "oliver-twist"}},
    )

    interested = client.get("/api/users/interest-reader/recommendations/mock")
    other = client.get("/api/users/other-reader/recommendations/mock")

    assert interested.status_code == 200
    assert interested.json()["userId"] == "interest-reader"
    assert other.status_code == 200
    assert other.json()["userId"] == "other-reader"
    assert other.json()["itinerariesFromPreferences"] == []


def test_admin_routes_can_be_disabled_by_flag(client, monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_ADMIN_ROUTES", "false")
    get_settings.cache_clear()

    response = client.get("/api/admin/seed/validate")

    assert response.status_code == 403


def test_debug_routes_can_be_disabled_by_flag(client, monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_DEBUG_ROUTES", "false")
    get_settings.cache_clear()

    response = client.get("/api/users/dev-reader/recommendations/mock")

    assert response.status_code == 403


def test_invalid_provider_names_fail_clearly(monkeypatch) -> None:
    monkeypatch.setenv("LITINERARY_AI_PROVIDER", "not-real")
    monkeypatch.setenv("LITINERARY_VECTOR_PROVIDER", "not-real")
    monkeypatch.setenv("LITINERARY_POI_VERIFICATION_PROVIDER", "not-real")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("ENABLE_REAL_VECTOR_DB", "true")
    monkeypatch.setenv("ENABLE_REAL_POI_PROVIDER", "true")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="AI provider 'not-real'"):
        get_ai_pipeline()
    with pytest.raises(RuntimeError, match="Vector provider 'not-real'"):
        get_vector_service()
    with pytest.raises(RuntimeError, match="POI verification provider 'not-real'"):
        get_poi_verification_adapter()


def test_production_does_not_enable_mock_services_by_default(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ENABLE_MOCK_SERVICES", raising=False)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="Mock AI services are disabled"):
        get_ai_pipeline()
