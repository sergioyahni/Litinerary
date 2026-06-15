def test_public_contract_shapes(client) -> None:
    health = client.get("/api/health")
    destinations = client.get("/api/destinations")
    books = client.get("/api/books?city_id=london")
    generated = client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "london",
            "bookId": "oliver-twist",
            "durationDays": 1,
            "transportationMode": "walking",
        },
    )
    narration = client.get("/api/itineraries/it-london-oliver-twist-1-walking/narration")

    assert health.json() == {"status": "ok"}
    assert {"id", "name", "country", "description", "latitude", "longitude", "supported"} <= (
        destinations.json()[0].keys()
    )
    assert {"id", "destinationIds", "title", "author", "description", "publicDomain"} <= (
        books.json()[0].keys()
    )
    payload = generated.json()
    assert {"itinerary", "matchedExisting", "sourceItineraryId", "message"} <= payload.keys()
    itinerary = payload["itinerary"]
    assert {
        "id",
        "destinationId",
        "bookId",
        "durationDays",
        "transportationMode",
        "days",
        "isPublic",
        "generatedFrom",
        "createdAt",
    } <= itinerary.keys()
    poi = itinerary["days"][0]["stops"][0]["poi"]
    assert {
        "id",
        "destinationId",
        "bookIds",
        "latitude",
        "longitude",
        "verificationStatus",
        "verificationNotes",
    } <= poi.keys()
    assert {"itineraryId", "script", "audio", "format"} <= narration.json().keys()
    assert {"text", "estimatedDurationSeconds", "providerType"} <= (
        narration.json()["script"].keys()
    )


def test_user_contract_shapes(client) -> None:
    client.post("/api/users", json={"id": "contract-user"})
    preference = client.post(
        "/api/users/contract-user/preferences",
        json={"key": "travel", "value": {"pace": "slow"}},
    )
    review = client.post(
        "/api/users/contract-user/reviews",
        json={
            "itineraryId": "it-london-oliver-twist-1-walking",
            "rating": 5,
            "comment": "Great route.",
        },
    )
    bookmarks = client.get("/api/users/contract-user/bookmarks")

    assert {"id", "userId", "key", "value", "createdAt"} <= preference.json().keys()
    assert {"id", "userId", "itineraryId", "rating", "comment", "createdAt"} <= (
        review.json().keys()
    )
    assert {"userId", "itineraries"} <= bookmarks.json().keys()


def test_development_admin_contract_shapes(client) -> None:
    job = client.post(
        "/api/admin/ingestion/jobs",
        json={
            "bookId": "oliver-twist",
            "source": {"sourceType": "metadata_only", "metadata": {}},
        },
    ).json()
    run = client.post(f"/api/admin/ingestion/jobs/{job['id']}/run").json()
    candidate_id = run["candidates"][0]["id"]
    verified = client.post(f"/api/admin/poi/verify-candidate/{candidate_id}")
    seed_validation = client.get("/api/admin/seed/validate")

    assert {"id", "bookId", "source", "status", "candidates", "artifacts"} <= run.keys()
    assert {"candidate", "verification"} <= verified.json().keys()
    assert {
        "status",
        "provider",
        "confidence",
        "verifiedName",
        "notes",
    } <= verified.json()["verification"].keys()
    assert {"valid", "errors", "warnings", "counts"} <= seed_validation.json().keys()
