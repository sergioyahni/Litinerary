from copy import deepcopy

from app.schemas.seed_admin import SeedDataPayload
from app.services.seed_manager import export_seed_data, validate_seed_data


def test_seed_validation_accepts_current_database(db_session) -> None:
    report = validate_seed_data(export_seed_data(db_session))

    assert report.valid is True
    assert report.errors == []
    assert report.counts["destinations"] > 0
    assert report.counts["books"] > 0
    assert report.counts["pois"] > 0
    assert report.counts["itineraries"] > 0


def test_seed_validation_catches_broken_relationships(db_session) -> None:
    payload = export_seed_data(db_session)
    broken_book = payload.books[0].model_copy(update={"destinationIds": ["missing-city"]})
    broken_poi = payload.pois[0].model_copy(update={"bookIds": ["missing-book"]})
    broken_itinerary = payload.itineraries[0].model_copy(
        update={"destinationId": "missing-city"},
        deep=True,
    )
    broken_payload = payload.model_copy(
        update={
            "books": [broken_book, *payload.books[1:]],
            "pois": [broken_poi, *payload.pois[1:]],
            "itineraries": [broken_itinerary, *payload.itineraries[1:]],
        },
        deep=True,
    )

    report = validate_seed_data(broken_payload)

    assert report.valid is False
    assert any("missing-city" in error for error in report.errors)
    assert any("missing-book" in error for error in report.errors)


def test_admin_seed_export_import_and_validate(client) -> None:
    export_response = client.get("/api/admin/seed/export")

    assert export_response.status_code == 200
    payload = export_response.json()
    assert payload["destinations"]
    assert payload["books"]
    assert payload["pois"]
    assert payload["itineraries"]

    import_response = client.post("/api/admin/seed/import", json=payload)
    validate_response = client.get("/api/admin/seed/validate")

    assert import_response.status_code == 200
    assert import_response.json()["validation"]["valid"] is True
    assert validate_response.status_code == 200
    assert validate_response.json()["valid"] is True


def test_admin_seed_import_rejects_invalid_payload(client) -> None:
    payload = client.get("/api/admin/seed/export").json()
    broken = deepcopy(payload)
    broken["books"][0]["destinationIds"] = ["missing-city"]

    response = client.post("/api/admin/seed/import", json=broken)

    assert response.status_code == 200
    assert response.json()["validation"]["valid"] is False
    assert "missing-city" in response.json()["validation"]["errors"][0]


def test_admin_seed_reset_reloads_bundled_data(client) -> None:
    response = client.post("/api/admin/seed/reset")
    validation = client.get("/api/admin/seed/validate")

    assert response.status_code == 200
    assert response.json()["message"].startswith("Reset local development database")
    assert validation.status_code == 200
    assert validation.json()["valid"] is True
