import pytest

from app.core.config import get_settings


def test_backend_mvp_and_phase2_smoke_path(client) -> None:
    health = client.get("/api/health")
    destinations = client.get("/api/destinations")
    books = client.get("/api/books?city_id=london")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert destinations.status_code == 200
    assert any(destination["id"] == "london" for destination in destinations.json())
    assert books.status_code == 200
    assert any(book["id"] == "oliver-twist" for book in books.json())

    generated = client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "london",
            "bookId": "oliver-twist",
            "durationDays": 1,
            "transportationMode": "walking",
        },
    )
    assert generated.status_code == 200
    itinerary = generated.json()["itinerary"]
    assert itinerary["days"]
    assert itinerary["days"][0]["stops"]
    assert itinerary["days"][0]["stops"][0]["poi"]["latitude"]

    repository = client.get("/api/itineraries")
    detail = client.get(f"/api/itineraries/{itinerary['id']}")
    assert repository.status_code == 200
    assert itinerary["id"] in {item["id"] for item in repository.json()}
    assert detail.status_code == 200
    assert detail.json()["id"] == itinerary["id"]

    created_user = client.post(
        "/api/users",
        json={"id": "smoke-reader", "displayName": "Smoke Reader"},
    )
    preference = client.post(
        "/api/users/smoke-reader/preferences",
        json={"key": "travel", "value": {"pace": "slow", "cityId": "london"}},
    )
    bookmark = client.post(f"/api/users/smoke-reader/bookmarks/{itinerary['id']}")
    review = client.post(
        "/api/users/smoke-reader/reviews",
        json={
            "itineraryId": itinerary["id"],
            "rating": 5,
            "comment": "Smoke path worked.",
        },
    )

    assert created_user.status_code == 201
    assert preference.status_code == 200
    assert bookmark.status_code == 200
    assert bookmark.json()["itineraries"][0]["id"] == itinerary["id"]
    assert review.status_code == 201
    assert review.json()["rating"] == 5


def test_backend_development_admin_smoke_path(client, monkeypatch) -> None:
    _enable_admin_auth(monkeypatch)
    headers = _admin_headers()
    validation = client.get("/api/admin/seed/validate")
    exported = client.get("/api/admin/seed/export")

    assert validation.status_code == 200
    assert validation.json()["valid"] is True
    assert exported.status_code == 200
    assert exported.json()["destinations"]

    created_job = client.post(
        "/api/admin/ingestion/jobs",
        headers=headers,
        json={
            "bookId": "oliver-twist",
            "source": {
                "sourceType": "metadata_only",
                "metadata": {},
            },
        },
    )
    assert created_job.status_code == 201

    job_id = created_job.json()["id"]
    processed_job = client.post(
        f"/api/admin/ingestion/jobs/{job_id}/run",
        headers=headers,
    )
    candidate_id = processed_job.json()["candidates"][0]["id"]
    verified_candidate = client.post(f"/api/admin/poi/verify-candidate/{candidate_id}")
    unverified = client.get("/api/admin/poi/unverified")

    assert processed_job.status_code == 200
    assert processed_job.json()["status"] == "completed"
    assert verified_candidate.status_code == 200
    assert "verification" in verified_candidate.json()
    assert unverified.status_code == 200


def _enable_admin_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_ADMIN_ROUTES", "true")
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "dev")
    monkeypatch.setenv("AUTH_ALLOW_DEV_USER_FALLBACK", "false")
    get_settings.cache_clear()


def _admin_headers() -> dict[str, str]:
    return {"Authorization": "Bearer dev:gate-b-admin:admin:none"}
