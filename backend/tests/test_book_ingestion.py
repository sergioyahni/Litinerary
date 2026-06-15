from app.models import POIModel


def test_development_ingestion_job_can_be_created_listed_and_processed(client) -> None:
    create_response = client.post(
        "/api/admin/ingestion/jobs",
        json={
            "bookId": "oliver-twist",
            "source": {
                "sourceType": "manually_curated_location_list",
                "title": "Curated Dickens locations",
                "metadata": {
                    "locations": [
                        {
                            "name": "Mock Workhouse Gate",
                            "destinationId": "london",
                            "description": "A safe, manually curated mock location.",
                            "literaryRelevance": "Represents social themes in the novel.",
                        }
                    ]
                },
            },
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["status"] == "pending"
    assert created["source"]["sourceType"] == "manually_curated_location_list"

    list_response = client.get("/api/admin/ingestion/jobs")
    assert list_response.status_code == 200
    assert created["id"] in {job["id"] for job in list_response.json()}

    run_response = client.post(f"/api/admin/ingestion/jobs/{created['id']}/run")
    detail_response = client.get(f"/api/admin/ingestion/jobs/{created['id']}")

    assert run_response.status_code == 200
    processed = run_response.json()
    assert processed["status"] == "completed"
    assert processed["candidates"][0]["bookId"] == "oliver-twist"
    assert processed["candidates"][0]["destinationId"] == "london"
    assert processed["candidates"][0]["name"] == "Mock Workhouse Gate"
    assert processed["artifacts"]
    assert detail_response.json() == processed


def test_ingestion_rejects_unsafe_full_text_metadata(client) -> None:
    response = client.post(
        "/api/admin/ingestion/jobs",
        json={
            "bookId": "oliver-twist",
            "source": {
                "sourceType": "summary_document",
                "metadata": {"fullText": "This must not be accepted."},
            },
        },
    )

    assert response.status_code == 400
    assert "full-text" in response.json()["detail"]


def test_ingestion_candidate_can_be_promoted_to_poi(client, db_session) -> None:
    created = client.post(
        "/api/admin/ingestion/jobs",
        json={
            "bookId": "oliver-twist",
            "source": {
                "sourceType": "summary_document",
                "title": "Safe summary",
                "metadata": {
                    "summary": "A safe summary, not full text.",
                    "locations": ["Mock Parish Steps"],
                },
            },
        },
    ).json()
    processed = client.post(f"/api/admin/ingestion/jobs/{created['id']}/run").json()
    candidate_id = processed["candidates"][0]["id"]

    promotion_response = client.post(
        f"/api/admin/ingestion/candidates/{candidate_id}/promote"
    )

    assert promotion_response.status_code == 200
    payload = promotion_response.json()
    assert payload["candidate"]["status"] == "promoted"
    assert payload["candidate"]["promotedPoiId"] == payload["poiId"]

    poi = db_session.get(POIModel, payload["poiId"])
    assert poi is not None
    assert poi.name == "Mock Parish Steps"
    assert poi.verification_status in {"mock_verified", "needs_review"}
    assert [book.id for book in poi.books] == ["oliver-twist"]


def test_existing_itinerary_generation_still_works_after_ingestion_routes(client) -> None:
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
