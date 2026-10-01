from copy import deepcopy
import json
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.models import BookModel, ItineraryImportRecordModel, ItineraryModel
from app.services import database_repository


_PUBLICLY_FORBIDDEN_KEYS = {
    "artifactHash",
    "batchSource",
    "contractVersion",
    "createdByMode",
    "createdByUserId",
    "generatedByService",
    "importBatchIdentity",
    "importContractVersion",
    "importJobId",
    "initiatedByUserId",
    "manualReviewStatus",
    "ownerUserId",
    "providerRequestId",
    "reviewedByUserId",
    "sourceAttribution",
    "sourceContentHash",
    "stableSourceIdentity",
    "subscriberOnly",
}


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def import_batch() -> dict:
    path = Path(__file__).parent / "fixtures" / "itinerary_import_v1_valid.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_import_authorization_and_disabled_environment(client, monkeypatch, import_batch) -> None:
    _enable_admin_auth(monkeypatch)
    endpoint = "/api/admin/ingestion/itinerary-imports"

    assert client.post(endpoint, json=import_batch).status_code == 401
    assert client.post(endpoint, headers=_user_headers(), json=import_batch).status_code == 403
    allowed = client.post(endpoint, headers=_admin_headers(), json=import_batch)
    assert allowed.status_code == 201

    monkeypatch.setenv("ENABLE_ADMIN_ROUTES", "false")
    get_settings.cache_clear()
    disabled = client.get(
        f"{endpoint}/{allowed.json()['id']}",
        headers=_admin_headers(),
    )
    assert disabled.status_code == 403


def test_dry_run_is_non_mutating_and_rejects_unsafe_inputs(
    client,
    db_session,
    monkeypatch,
    import_batch,
) -> None:
    _enable_admin_auth(monkeypatch)
    endpoint = "/api/admin/ingestion/itinerary-imports"
    before = db_session.scalar(select(func.count()).select_from(ItineraryModel))

    preview = client.post(endpoint, headers=_admin_headers(), json=import_batch)
    assert preview.status_code == 201
    payload = preview.json()
    assert payload["dryRun"] is True
    assert payload["status"] == "previewed"
    assert payload["preview"]["newRecords"] == 1
    assert payload["preview"]["projectedMutations"] == 1
    assert db_session.scalar(select(func.count()).select_from(ItineraryModel)) == before

    unsupported = deepcopy(import_batch)
    unsupported["version"] = "litinerary-import/v99"
    assert client.post(endpoint, headers=_admin_headers(), json=unsupported).status_code == 422

    duplicate = deepcopy(import_batch)
    duplicate["records"].append(deepcopy(duplicate["records"][0]))
    assert client.post(endpoint, headers=_admin_headers(), json=duplicate).status_code == 422

    unknown = deepcopy(import_batch)
    unknown["records"][0]["unexpected"] = "rejected"
    assert client.post(endpoint, headers=_admin_headers(), json=unknown).status_code == 422

    sensitive = deepcopy(import_batch)
    sensitive["source"]["metadata"]["apiToken"] = "must-not-be-stored"
    response = client.post(endpoint, headers=_admin_headers(), json=sensitive)
    assert response.status_code == 400
    assert "sensitive-looking" in response.json()["detail"]

    oversized = deepcopy(import_batch)
    oversized["source"]["metadata"]["padding"] = "x" * 2_000_001
    response = client.post(endpoint, headers=_admin_headers(), json=oversized)
    assert response.status_code == 400
    assert "2000000-byte" in response.json()["detail"]


def test_confirm_verify_publish_repository_book(
    client,
    db_session,
    monkeypatch,
    import_batch,
) -> None:
    _enable_admin_auth(monkeypatch)
    endpoint = "/api/admin/ingestion/itinerary-imports"
    preview = client.post(endpoint, headers=_admin_headers(), json=import_batch).json()
    itinerary_id = import_batch["records"][0]["itinerary"]["id"]

    confirm = client.post(f"{endpoint}/{preview['id']}/confirm", headers=_admin_headers())
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "persisted"
    assert client.get(f"/api/itineraries/{itinerary_id}").status_code == 404
    assert client.get(f"/api/itineraries/{itinerary_id}", headers=_admin_headers()).status_code == 200

    verification = client.get(f"{endpoint}/{preview['id']}/verify", headers=_admin_headers())
    assert verification.status_code == 200
    assert verification.json()["verified"] is True
    assert verification.json()["records"][0]["publicationState"] == "draft"

    publish = client.post(f"{endpoint}/{preview['id']}/publish", headers=_admin_headers())
    assert publish.status_code == 200
    assert publish.json()["status"] == "published"
    detail = client.get(f"/api/itineraries/{itinerary_id}")
    listing = client.get("/api/itineraries")
    filtered = client.get(
        "/api/itineraries",
        params={
            "city_id": "london",
            "book_id": "oliver-twist",
            "transportation_mode": "walking",
        },
    )
    assert detail.status_code == 200
    assert listing.status_code == 200
    assert filtered.status_code == 200

    public_payloads = [
        detail.json(),
        next(item for item in listing.json() if item["id"] == itinerary_id),
        next(item for item in filtered.json() if item["id"] == itinerary_id),
    ]
    for payload in public_payloads:
        assert payload["id"] == itinerary_id
        assert payload["title"] == "Gate B Controlled Oliver Twist Walk"
        assert payload["isPublic"] is True
        assert payload["visibility"] == "public"
        assert payload["generatedFrom"] == "imported"
        assert payload["sourceType"] == "corpus_import"
        assert payload["days"]
        public_poi = payload["days"][0]["stops"][0]["poi"]
        assert "verificationProvider" in public_poi
        assert "verificationNotes" in public_poi
        assert "provenanceMetadata" in public_poi
        exposed_internal_keys = _serialized_keys(payload) & _PUBLICLY_FORBIDDEN_KEYS
        assert not exposed_internal_keys, exposed_internal_keys

    persisted = database_repository.get_itinerary(db_session, itinerary_id)
    assert persisted is not None
    assert persisted.createdByMode == "admin"
    assert persisted.createdByUserId == "gate-b-admin"
    assert persisted.providerRequestId == preview["id"]
    assert persisted.generatedByService == "itinerary_import_service"
    assert persisted.provenanceMetadata["importJobId"] == preview["id"]
    assert persisted.provenanceMetadata["sourceAttribution"]
    assert persisted.provenanceMetadata["stableSourceIdentity"]

    published_verification = client.get(
        f"{endpoint}/{preview['id']}/verify",
        headers=_admin_headers(),
    )
    assert published_verification.status_code == 200
    assert published_verification.json()["verified"] is True
    assert published_verification.json()["records"][0]["provenanceMatches"] is True

    audit = db_session.scalar(
        select(ItineraryImportRecordModel).where(
            ItineraryImportRecordModel.source_identity
            == import_batch["records"][0]["sourceIdentity"]
        )
    )
    assert audit is not None
    assert audit.status == "published"


def test_external_snapshot_import_does_not_create_book_model(
    client,
    db_session,
    monkeypatch,
    import_batch,
) -> None:
    _enable_admin_auth(monkeypatch)
    endpoint = "/api/admin/ingestion/itinerary-imports"
    batch = deepcopy(import_batch)
    record = batch["records"][0]
    batch["batchIdentity"] = "gate-b-external-fixture-v1"
    record["sourceIdentity"] = "gate-b-fixture:external-book:london:walking:1d:v1"
    record["itinerary"]["id"] = "it-import-gate-b-external-fixture"
    record["book"] = {
        "semantics": "external_snapshot",
        "id": "external-gate-b-book",
        "title": "Gate B External Book",
        "author": "Gate B Fixture Author",
        "description": "Controlled external-book snapshot for Gate B.",
        "publicationYear": 1901,
        "publicDomain": True,
        "themes": ["gate-b", "external-snapshot"],
        "coverUrl": None,
        "sourceType": "external",
        "providerId": "gate-b-fixture-provider-id",
        "provenanceMetadata": {"fixture": True},
    }
    before = db_session.scalar(select(func.count()).select_from(BookModel))

    preview = client.post(endpoint, headers=_admin_headers(), json=batch).json()
    assert client.post(f"{endpoint}/{preview['id']}/confirm", headers=_admin_headers()).status_code == 200
    assert db_session.get(BookModel, "external-gate-b-book") is None
    assert db_session.scalar(select(func.count()).select_from(BookModel)) == before
    assert client.post(f"{endpoint}/{preview['id']}/publish", headers=_admin_headers()).status_code == 200

    filtered = client.get("/api/itineraries", params={"book_id": "external-gate-b-book"})
    projected_books = client.get(
        "/api/books",
        params={"city_id": "london", "q": "Gate B External"},
    )
    assert [item["id"] for item in filtered.json()] == ["it-import-gate-b-external-fixture"]
    assert {item["id"] for item in projected_books.json()} == {"external-gate-b-book"}
    assert db_session.get(BookModel, "external-gate-b-book") is None


def test_idempotency_conflict_and_domain_invalid(
    client,
    db_session,
    monkeypatch,
    import_batch,
) -> None:
    _enable_admin_auth(monkeypatch)
    endpoint = "/api/admin/ingestion/itinerary-imports"
    first = client.post(endpoint, headers=_admin_headers(), json=import_batch).json()
    assert client.post(f"{endpoint}/{first['id']}/confirm", headers=_admin_headers()).status_code == 200
    before = db_session.scalar(select(func.count()).select_from(ItineraryModel))

    retry = deepcopy(import_batch)
    retry["batchIdentity"] = "gate-b-controlled-fixture-retry"
    second = client.post(endpoint, headers=_admin_headers(), json=retry)
    assert second.status_code == 201
    assert second.json()["preview"]["alreadyImportedRecords"] == 1
    assert second.json()["preview"]["projectedMutations"] == 0
    assert client.post(
        f"{endpoint}/{second.json()['id']}/confirm",
        headers=_admin_headers(),
    ).status_code == 200
    assert client.get(
        f"{endpoint}/{second.json()['id']}/verify",
        headers=_admin_headers(),
    ).json()["verified"] is True
    assert db_session.scalar(select(func.count()).select_from(ItineraryModel)) == before

    changed = deepcopy(import_batch)
    changed["batchIdentity"] = "gate-b-controlled-fixture-conflict"
    changed["records"][0]["itinerary"]["title"] = "Changed content"
    conflict = client.post(endpoint, headers=_admin_headers(), json=changed)
    assert conflict.status_code == 201
    assert conflict.json()["preview"]["conflicts"] == 1
    assert client.post(
        f"{endpoint}/{conflict.json()['id']}/confirm",
        headers=_admin_headers(),
    ).status_code == 400

    invalid = deepcopy(import_batch)
    invalid["batchIdentity"] = "gate-b-invalid-fixture"
    invalid["records"][0]["sourceIdentity"] = "gate-b-invalid-source"
    invalid["records"][0]["itinerary"]["id"] = "it-import-gate-b-invalid"
    invalid["records"][0]["itinerary"]["days"][0]["stops"][0]["poiId"] = "missing-poi"
    preview = client.post(endpoint, headers=_admin_headers(), json=invalid)
    assert preview.status_code == 201
    assert preview.json()["preview"]["invalidRecords"] == 1
    assert client.post(
        f"{endpoint}/{preview.json()['id']}/confirm",
        headers=_admin_headers(),
    ).status_code == 400


def test_record_atomic_failure_is_retryable(
    client,
    db_session,
    monkeypatch,
    import_batch,
) -> None:
    _enable_admin_auth(monkeypatch)
    endpoint = "/api/admin/ingestion/itinerary-imports"
    batch = deepcopy(import_batch)
    first = batch["records"][0]
    first["sourceIdentity"] = "gate-b-atomic-first"
    first["itinerary"]["id"] = "it-import-atomic-first"
    second = deepcopy(first)
    second["sourceIdentity"] = "gate-b-atomic-second"
    second["itinerary"]["id"] = "it-import-atomic-second"
    batch["batchIdentity"] = "gate-b-atomic-batch"
    batch["records"] = [first, second]

    preview = client.post(endpoint, headers=_admin_headers(), json=batch).json()
    original = database_repository.save_itinerary
    calls = {"count": 0}

    def fail_second(db, itinerary):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("forced Gate B persistence failure")
        return original(db, itinerary)

    monkeypatch.setattr(database_repository, "save_itinerary", fail_second)
    failed = client.post(f"{endpoint}/{preview['id']}/confirm", headers=_admin_headers())
    assert failed.status_code == 200
    assert failed.json()["status"] == "persistence_failed"
    assert failed.json()["persistedItineraryIds"] == ["it-import-atomic-first"]
    assert db_session.get(ItineraryModel, "it-import-atomic-first") is not None
    assert db_session.get(ItineraryModel, "it-import-atomic-second") is None

    retry = client.post(f"{endpoint}/{preview['id']}/confirm", headers=_admin_headers())
    assert retry.status_code == 200
    assert retry.json()["status"] == "persisted"
    assert set(retry.json()["persistedItineraryIds"]) == {
        "it-import-atomic-first",
        "it-import-atomic-second",
    }


def _enable_admin_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_ADMIN_ROUTES", "true")
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "dev")
    monkeypatch.setenv("AUTH_ALLOW_DEV_USER_FALLBACK", "false")
    get_settings.cache_clear()


def _admin_headers() -> dict[str, str]:
    return {"Authorization": "Bearer dev:gate-b-admin:admin:none"}


def _user_headers() -> dict[str, str]:
    return {"Authorization": "Bearer dev:gate-b-reader:user:none"}


def _serialized_keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            key
            for item in value.values()
            for key in _serialized_keys(item)
        }
    if isinstance(value, list):
        return {key for item in value for key in _serialized_keys(item)}
    return set()
