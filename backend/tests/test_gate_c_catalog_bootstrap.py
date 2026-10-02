from copy import deepcopy
import json
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.models import DestinationModel, ItineraryModel, POIModel


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def import_batch() -> dict:
    path = Path(__file__).parent / "fixtures" / "itinerary_import_v1_valid.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_catalog_bootstrap_preview_confirm_publish_and_idempotency(
    client,
    db_session,
    monkeypatch,
    import_batch,
) -> None:
    _enable_admin_auth(monkeypatch)
    endpoint = "/api/admin/ingestion/itinerary-imports"
    batch = _new_destination_batch(import_batch)

    before_destinations = db_session.scalar(select(func.count()).select_from(DestinationModel))
    before_pois = db_session.scalar(select(func.count()).select_from(POIModel))
    before_itineraries = db_session.scalar(select(func.count()).select_from(ItineraryModel))

    preview = client.post(endpoint, headers=_admin_headers(), json=batch)
    assert preview.status_code == 201
    preview_payload = preview.json()
    assert preview_payload["dryRun"] is True
    assert preview_payload["preview"]["newRecords"] == 1
    assert preview_payload["preview"]["projectedCatalogMutations"] == 2
    assert preview_payload["preview"]["projectedMutations"] == 3
    assert db_session.get(DestinationModel, "bath") is None
    assert db_session.get(POIModel, "bath-royal-crescent") is None
    assert db_session.scalar(select(func.count()).select_from(DestinationModel)) == before_destinations
    assert db_session.scalar(select(func.count()).select_from(POIModel)) == before_pois
    assert db_session.scalar(select(func.count()).select_from(ItineraryModel)) == before_itineraries

    confirm = client.post(
        f"{endpoint}/{preview_payload['id']}/confirm",
        headers=_admin_headers(),
    )
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "persisted"
    assert db_session.get(DestinationModel, "bath") is not None
    assert db_session.get(POIModel, "bath-royal-crescent") is not None
    assert db_session.get(ItineraryModel, "it-import-gate-c-bath-fixture") is not None

    publish = client.post(
        f"{endpoint}/{preview_payload['id']}/publish",
        headers=_admin_headers(),
    )
    assert publish.status_code == 200
    assert publish.json()["status"] == "published"
    detail = client.get("/api/itineraries/it-import-gate-c-bath-fixture")
    assert detail.status_code == 200
    assert detail.json()["destinationId"] == "bath"
    assert detail.json()["bookId"] == "northanger-abbey-external"

    retry = deepcopy(batch)
    retry["batchIdentity"] = "gate-c-catalog-bootstrap-retry"
    second = client.post(endpoint, headers=_admin_headers(), json=retry)
    assert second.status_code == 201
    assert second.json()["preview"]["alreadyImportedRecords"] == 1
    assert second.json()["preview"]["projectedCatalogMutations"] == 0
    assert second.json()["preview"]["projectedMutations"] == 0
    assert client.post(
        f"{endpoint}/{second.json()['id']}/confirm",
        headers=_admin_headers(),
    ).status_code == 200


def test_catalog_change_fails_closed(
    client,
    monkeypatch,
    import_batch,
) -> None:
    _enable_admin_auth(monkeypatch)
    endpoint = "/api/admin/ingestion/itinerary-imports"
    batch = _new_destination_batch(import_batch)
    first = client.post(endpoint, headers=_admin_headers(), json=batch).json()
    assert client.post(f"{endpoint}/{first['id']}/confirm", headers=_admin_headers()).status_code == 200

    changed = deepcopy(batch)
    changed["batchIdentity"] = "gate-c-catalog-bootstrap-conflict"
    changed["pois"][0]["literaryRelevance"] = (
        "Changed relevance must not silently overwrite canonical catalog data."
    )
    conflict = client.post(endpoint, headers=_admin_headers(), json=changed)
    assert conflict.status_code == 201
    assert conflict.json()["preview"]["invalidRecords"] == 1
    assert "differs from the import catalog snapshot" in " ".join(
        conflict.json()["preview"]["records"][0]["errors"]
    )
    assert client.post(
        f"{endpoint}/{conflict.json()['id']}/confirm",
        headers=_admin_headers(),
    ).status_code == 400


def test_repository_catalog_bootstrap_requires_declared_book_link(
    client,
    monkeypatch,
    import_batch,
) -> None:
    _enable_admin_auth(monkeypatch)
    endpoint = "/api/admin/ingestion/itinerary-imports"
    batch = deepcopy(import_batch)
    record = batch["records"][0]
    batch["batchIdentity"] = "gate-c-repository-poi-bootstrap"
    record["sourceIdentity"] = "gate-c:repo-poi:london:oliver-twist:v1"
    record["itinerary"]["id"] = "it-import-gate-c-repo-poi"
    record["itinerary"]["days"][0]["stops"][0]["poiId"] = "gate-c-dickens-place"
    batch["pois"] = [
        {
            "id": "gate-c-dickens-place",
            "destinationId": "london",
            "name": "Gate C Dickens Place",
            "description": "Controlled catalog-bootstrap fixture for an existing repository book.",
            "latitude": 51.51,
            "longitude": -0.12,
            "estimatedDurationMinutes": 30,
            "literaryRelevance": "Exercises repository-book linkage for catalog bootstrap.",
            "verificationStatus": "unverified",
            "repositoryBookIds": [],
            "provenanceMetadata": {"fixture": True},
        }
    ]

    invalid = client.post(endpoint, headers=_admin_headers(), json=batch)
    assert invalid.status_code == 201
    assert invalid.json()["preview"]["invalidRecords"] == 1
    assert "not linked to repository book 'oliver-twist'" in " ".join(
        invalid.json()["preview"]["records"][0]["errors"]
    )

    batch["batchIdentity"] = "gate-c-repository-poi-bootstrap-linked"
    batch["pois"][0]["repositoryBookIds"] = ["oliver-twist"]
    valid = client.post(endpoint, headers=_admin_headers(), json=batch)
    assert valid.status_code == 201
    assert valid.json()["preview"]["invalidRecords"] == 0
    assert valid.json()["preview"]["projectedCatalogMutations"] == 1


def test_legacy_record_hash_remains_idempotent_without_catalog_entries(
    client,
    monkeypatch,
    import_batch,
) -> None:
    _enable_admin_auth(monkeypatch)
    endpoint = "/api/admin/ingestion/itinerary-imports"
    first = client.post(endpoint, headers=_admin_headers(), json=import_batch).json()
    assert client.post(f"{endpoint}/{first['id']}/confirm", headers=_admin_headers()).status_code == 200

    retry = deepcopy(import_batch)
    retry["batchIdentity"] = "gate-b-controlled-fixture-after-gate-c-extension"
    second = client.post(endpoint, headers=_admin_headers(), json=retry)
    assert second.status_code == 201
    assert second.json()["preview"]["alreadyImportedRecords"] == 1
    assert second.json()["preview"]["conflicts"] == 0


def _new_destination_batch(import_batch: dict) -> dict:
    batch = deepcopy(import_batch)
    record = batch["records"][0]
    batch["batchIdentity"] = "gate-c-catalog-bootstrap-bath"
    batch["source"] = {
        "name": "Gate C controlled catalog-bootstrap fixture",
        "attribution": "Engineering coverage for Gate C only.",
        "metadata": {"gate": "C", "fixture": True},
    }
    record["sourceIdentity"] = "gate-c-fixture:northanger-abbey:bath:walking:1d:v1"
    record["sourceAttribution"] = {"fixture": "test_gate_c_catalog_bootstrap.py"}
    record["destination"] = {
        "id": "bath",
        "name": "Bath",
        "country": "United Kingdom",
        "region": "England",
        "description": "A Georgian city strongly associated with Jane Austen's fiction and life.",
        "latitude": 51.3811,
        "longitude": -2.3590,
        "imageUrl": None,
    }
    record["book"] = {
        "semantics": "external_snapshot",
        "id": "northanger-abbey-external",
        "title": "Northanger Abbey",
        "author": "Jane Austen",
        "description": "A novel whose Bath episodes provide literary context for a city walk.",
        "publicationYear": 1817,
        "publicDomain": True,
        "themes": ["regency", "satire", "bath"],
        "coverUrl": None,
        "sourceType": "external",
        "providerId": "gate-c-fixture-northanger-abbey",
        "provenanceMetadata": {"fixture": True},
    }
    record["itinerary"] = {
        "id": "it-import-gate-c-bath-fixture",
        "title": "Gate C Bath Catalog Bootstrap Fixture",
        "summary": "A controlled fixture proving destination and POI bootstrap through itinerary-import/v1.",
        "durationDays": 1,
        "transportationMode": "walking",
        "days": [
            {
                "dayNumber": 1,
                "title": "Georgian Bath",
                "summary": "A deterministic one-stop engineering fixture.",
                "stops": [
                    {
                        "poiId": "bath-royal-crescent",
                        "order": 1,
                        "title": "Royal Crescent",
                        "narrativeNote": "Use the Georgian streetscape as contextual grounding for Austen's Bath.",
                        "logisticsNote": "Engineering fixture only.",
                        "estimatedStartTime": "10:00",
                        "estimatedEndTime": "10:30",
                    }
                ],
                "estimatedDistanceKm": 0.0,
                "estimatedDurationHours": 0.5,
            }
        ],
    }
    record["publicationIntent"] = "publish"
    batch["pois"] = [
        {
            "id": "bath-royal-crescent",
            "destinationId": "bath",
            "name": "Royal Crescent",
            "description": "A landmark Georgian crescent in Bath used here as a controlled fixture POI.",
            "latitude": 51.3868,
            "longitude": -2.3681,
            "address": None,
            "estimatedDurationMinutes": 30,
            "ticketingNote": "Public outdoor view; individual venues have separate access rules.",
            "literaryRelevance": "Provides period streetscape context for Austen's Bath settings.",
            "verificationStatus": "unverified",
            "verificationProvider": None,
            "providerVersion": None,
            "providerRequestId": None,
            "verificationConfidence": None,
            "verifiedName": None,
            "verifiedAddress": None,
            "verifiedLatitude": None,
            "verifiedLongitude": None,
            "openingHoursNote": None,
            "ticketingUrl": None,
            "verificationNotes": ["Controlled Gate C test fixture; not real corpus evidence."],
            "lastVerifiedAt": None,
            "manualReviewStatus": "not_reviewed",
            "repositoryBookIds": [],
            "provenanceMetadata": {"fixture": True},
        }
    ]
    return batch


def _enable_admin_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_ADMIN_ROUTES", "true")
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "dev")
    monkeypatch.setenv("AUTH_ALLOW_DEV_USER_FALLBACK", "false")
    get_settings.cache_clear()


def _admin_headers() -> dict[str, str]:
    return {"Authorization": "Bearer dev:gate-c-admin:admin:none"}
