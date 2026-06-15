from app.services.vector_service import get_vector_service
from app.services.vector_types import VectorCollection


def test_development_user_can_be_created_and_retrieved(client) -> None:
    create_response = client.post(
        "/api/users",
        json={
            "id": "dev-reader",
            "email": "reader@example.test",
            "displayName": "Development Reader",
        },
    )
    get_response = client.get("/api/users/dev-reader")

    assert create_response.status_code == 201
    assert create_response.json()["id"] == "dev-reader"
    assert get_response.status_code == 200
    assert get_response.json()["displayName"] == "Development Reader"


def test_user_preferences_can_be_saved(client) -> None:
    get_vector_service.cache_clear()
    client.post("/api/users", json={"id": "dev-reader"})

    response = client.post(
        "/api/users/dev-reader/preferences",
        json={
            "key": "travel",
            "value": {
                "pace": "slow",
                "themes": ["classic"],
                "cityId": "london",
                "bookId": "oliver-twist",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["userId"] == "dev-reader"
    assert payload["key"] == "travel"
    assert payload["value"] == {
        "pace": "slow",
        "themes": ["classic"],
        "cityId": "london",
        "bookId": "oliver-twist",
    }

    vector = get_vector_service().fetch_by_metadata(
        VectorCollection.USER_PREFERENCES,
        {"user_id": "dev-reader"},
    )[0]
    assert vector.metadata["preference_id"] == payload["id"]
    assert vector.metadata["city_id"] == "london"
    assert vector.metadata["book_id"] == "oliver-twist"


def test_itinerary_can_be_bookmarked_listed_and_unbookmarked(client) -> None:
    client.post("/api/users", json={"id": "dev-reader"})

    bookmark_response = client.post(
        "/api/users/dev-reader/bookmarks/it-london-oliver-twist-1-walking"
    )
    list_response = client.get("/api/users/dev-reader/bookmarks")
    delete_response = client.delete(
        "/api/users/dev-reader/bookmarks/it-london-oliver-twist-1-walking"
    )

    assert bookmark_response.status_code == 200
    assert bookmark_response.json()["itineraries"][0]["id"] == "it-london-oliver-twist-1-walking"
    assert list_response.status_code == 200
    assert {item["id"] for item in list_response.json()["itineraries"]} == {
        "it-london-oliver-twist-1-walking"
    }
    assert delete_response.status_code == 200
    assert delete_response.json()["itineraries"] == []


def test_user_review_can_be_saved_and_listed(client) -> None:
    get_vector_service.cache_clear()
    client.post("/api/users", json={"id": "dev-reader"})

    save_response = client.post(
        "/api/users/dev-reader/reviews",
        json={
            "itineraryId": "it-london-oliver-twist-1-walking",
            "rating": 5,
            "comment": "Useful for a first mock route.",
        },
    )
    list_response = client.get("/api/users/dev-reader/reviews")

    assert save_response.status_code == 201
    assert save_response.json()["rating"] == 5
    assert list_response.status_code == 200
    assert list_response.json()[0]["comment"] == "Useful for a first mock route."

    vector = get_vector_service().fetch_by_metadata(
        VectorCollection.USER_REVIEWS,
        {"user_id": "dev-reader"},
    )[0]
    assert vector.metadata["review_id"] == save_response.json()["id"]
    assert vector.metadata["itinerary_id"] == "it-london-oliver-twist-1-walking"
    assert vector.metadata["city_id"] == "london"
    assert vector.metadata["book_id"] == "oliver-twist"
    assert vector.metadata["rating"] == 5


def test_development_mock_recommendations_are_available(client) -> None:
    get_vector_service.cache_clear()
    client.post("/api/users", json={"id": "dev-reader"})
    client.post(
        "/api/users/dev-reader/preferences",
        json={
            "key": "travel",
            "value": {"pace": "slow", "cityId": "london", "bookId": "oliver-twist"},
        },
    )
    client.post(
        "/api/users/dev-reader/reviews",
        json={
            "itineraryId": "it-london-oliver-twist-1-walking",
            "rating": 5,
            "comment": "Loved the London market route.",
        },
    )

    first = client.get("/api/users/dev-reader/recommendations/mock?limit=3")
    second = client.get("/api/users/dev-reader/recommendations/mock?limit=3")

    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["developmentOnly"] is True
    assert first.json()["itinerariesFromPreferences"]
    assert first.json()["itinerariesFromPositiveReviews"]
    assert first.json()["poisFromInterests"]


def test_anonymous_itinerary_generation_still_works(client) -> None:
    response = client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "london",
            "bookId": "oliver-twist",
            "durationDays": 1,
            "transportationMode": "walking",
        },
    )

    assert response.status_code == 200
    assert response.json()["matchedExisting"] is True
