def test_health_endpoint_returns_ok(client) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_destination_listing_returns_supported_mock_destinations(client) -> None:
    response = client.get("/api/destinations")

    assert response.status_code == 200
    destinations = response.json()
    assert [destination["id"] for destination in destinations] == [
        "london",
        "paris",
        "dublin",
        "prague",
        "samarkand",
    ]
    assert all(destination["supported"] for destination in destinations)


def test_book_listing_by_city_returns_only_books_for_that_city(client) -> None:
    response = client.get("/api/books", params={"city_id": "london"})

    assert response.status_code == 200
    books = response.json()
    assert {book["id"] for book in books} == {"oliver-twist", "sherlock-holmes"}
    assert all("london" in book["destinationIds"] for book in books)


def test_itinerary_generation_rejects_invalid_request_shape(client) -> None:
    response = client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "london",
            "bookId": "oliver-twist",
            "durationDays": 0,
            "transportationMode": "walking",
        },
    )

    assert response.status_code == 422


def test_itinerary_generation_returns_exact_repository_match(client) -> None:
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
    payload = response.json()
    assert payload["matchedExisting"] is True
    assert payload["sourceItineraryId"] == "it-london-oliver-twist-1-walking"
    assert payload["itinerary"]["sourceType"] == "exact_match"
    assert payload["itinerary"]["generatedFrom"] == "exact_match"
    assert payload["itinerary"]["days"][0]["stops"][0]["poi"]["id"] == "smithfield-market"


def test_itinerary_generation_adapts_partial_repository_match(client) -> None:
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
    payload = response.json()
    itinerary = payload["itinerary"]
    assert payload["matchedExisting"] is True
    assert payload["sourceItineraryId"] == "it-london-oliver-twist-1-walking"
    assert itinerary["sourceType"] == "adapted_match"
    assert itinerary["durationDays"] == 2
    assert itinerary["transportationMode"] == "public_transport"
    assert len(itinerary["days"]) == 2
    assert any("Expanded from 1 day" in note for note in itinerary["adaptationNotes"])
    assert any("Transportation changed" in note for note in itinerary["adaptationNotes"])


def test_itinerary_generation_creates_new_mock_itinerary_when_no_match_exists(client) -> None:
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
    itinerary = payload["itinerary"]
    assert payload["matchedExisting"] is False
    assert itinerary["id"] == "it-paris-les-miserables-2-walking-generated"
    assert itinerary["sourceType"] == "new_mock_generation"
    assert itinerary["generatedFrom"] == "new_generation"
    assert itinerary["durationDays"] == 2
    assert [day["dayNumber"] for day in itinerary["days"]] == [1, 2]


def test_itinerary_detail_lookup_returns_seeded_repository_itinerary(client) -> None:
    response = client.get("/api/itineraries/it-samarkand-khayyam-1-car-taxi")

    assert response.status_code == 200
    itinerary = response.json()
    assert itinerary["id"] == "it-samarkand-khayyam-1-car-taxi"
    assert itinerary["bookId"] == "rubaiyat"
    assert itinerary["transportationMode"] == "car_taxi"


def test_invalid_city_book_and_itinerary_ids_return_errors(client) -> None:
    bad_city = client.get("/api/books", params={"city_id": "atlantis"})
    bad_book = client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "london",
            "bookId": "les-miserables",
            "durationDays": 1,
            "transportationMode": "walking",
        },
    )
    bad_itinerary = client.get("/api/itineraries/not-real")

    assert bad_city.status_code == 404
    assert bad_book.status_code == 400
    assert bad_itinerary.status_code == 404
