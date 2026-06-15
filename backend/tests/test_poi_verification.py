from app.models import POIModel
from app.services.poi_verification import MockPOIVerificationAdapter, PlaceSearchQuery


def test_mock_verification_success_for_seeded_poi(client, db_session) -> None:
    poi = db_session.scalars(db_session.query(POIModel).statement).first()

    response = client.post(f"/api/admin/poi/verify/{poi.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["verification"]["status"] == "mock_verified"
    assert payload["verification"]["confidence"] >= 0.85
    assert payload["poi"]["verificationProvider"] == "mock_local"
    assert payload["poi"]["ticketingUrl"].startswith("https://example.test/tickets/")


def test_mock_verification_low_confidence_for_unknown_candidate(client) -> None:
    created = client.post(
        "/api/admin/ingestion/jobs",
        json={
            "bookId": "oliver-twist",
            "source": {
                "sourceType": "manually_curated_location_list",
                "metadata": {
                    "locations": [
                        {
                            "name": "Completely New Fictional Corner",
                            "destinationId": "london",
                            "latitude": 51.0,
                            "longitude": -0.5,
                        }
                    ]
                },
            },
        },
    ).json()
    processed = client.post(f"/api/admin/ingestion/jobs/{created['id']}/run").json()
    candidate_id = processed["candidates"][0]["id"]

    response = client.post(f"/api/admin/poi/verify-candidate/{candidate_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["verification"]["status"] == "needs_review"
    assert payload["verification"]["confidence"] < 0.85
    assert payload["verification"]["ticketingUrl"] is None


def test_mock_adapter_rejects_missing_or_zero_coordinates() -> None:
    adapter = MockPOIVerificationAdapter()

    assert adapter.validate_coordinates(None, -0.1) is False
    assert adapter.validate_coordinates(51.5, None) is False
    assert adapter.validate_coordinates(0.0, -0.1) is False
    assert adapter.validate_coordinates(51.5, -0.1) is True


def test_candidate_promotion_carries_verification_metadata(client, db_session) -> None:
    seeded = db_session.scalars(db_session.query(POIModel).statement).first()
    created = client.post(
        "/api/admin/ingestion/jobs",
        json={
            "bookId": seeded.books[0].id,
            "source": {
                "sourceType": "manually_curated_location_list",
                "metadata": {
                    "locations": [
                        {
                            "name": seeded.name,
                            "destinationId": seeded.destination_id,
                            "latitude": seeded.latitude,
                            "longitude": seeded.longitude,
                        }
                    ]
                },
            },
        },
    ).json()
    processed = client.post(f"/api/admin/ingestion/jobs/{created['id']}/run").json()
    candidate_id = processed["candidates"][0]["id"]

    response = client.post(f"/api/admin/ingestion/candidates/{candidate_id}/promote")

    assert response.status_code == 200
    promoted = db_session.get(POIModel, response.json()["poiId"])
    assert promoted.verification_status == "mock_verified"
    assert promoted.verification_provider == "mock_local"
    assert promoted.verification_confidence >= 0.85
    assert promoted.verified_name == seeded.name


def test_unverified_and_mark_reviewed_endpoints(client, db_session) -> None:
    poi = POIModel(
        id="poi-needs-review",
        destination_id="london",
        name="Needs Review",
        description="Temporary test POI.",
        latitude=51.5,
        longitude=-0.1,
        estimated_duration_minutes=30,
        literary_relevance="Test relevance.",
        verification_status="needs_review",
        verification_notes=[],
    )
    db_session.add(poi)
    db_session.commit()

    unverified = client.get("/api/admin/poi/unverified")
    reviewed = client.post("/api/admin/poi/poi-needs-review/mark-reviewed")

    assert unverified.status_code == 200
    assert "poi-needs-review" in {item["id"] for item in unverified.json()}
    assert reviewed.status_code == 200
    assert reviewed.json()["verificationStatus"] == "mock_verified"


def test_mock_search_is_deterministic(db_session) -> None:
    poi = db_session.scalars(db_session.query(POIModel).statement).first()
    adapter = MockPOIVerificationAdapter()
    query = PlaceSearchQuery(
        name=poi.name,
        city_id=poi.destination_id,
        latitude=poi.latitude,
        longitude=poi.longitude,
    )

    assert adapter.search_places(db_session, query) == adapter.search_places(db_session, query)
