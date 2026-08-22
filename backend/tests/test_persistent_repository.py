from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app
from app.models import ItineraryStopModel, POIModel, domain  # noqa: F401
from app.services import database_repository
from app.services.database_repository import ItineraryPersistenceError
from app.services.seed import seed_database


def test_adapted_itinerary_is_saved_to_database(client, db_session) -> None:
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
    itinerary = response.json()["itinerary"]
    saved = database_repository.get_itinerary(db_session, itinerary["id"])

    assert saved is not None
    assert saved.sourceType == "adapted_match"
    assert saved.sourceItineraryId == "it-london-oliver-twist-1-walking"
    assert saved.isPublic is True
    assert saved.adaptationNotes


def test_new_mock_generation_is_saved_to_database(client, db_session) -> None:
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
    saved = database_repository.get_itinerary(db_session, payload["itinerary"]["id"])

    assert payload["matchedExisting"] is False
    assert saved is not None
    assert saved.sourceType == "new_mock_generation"
    assert saved.sourceItineraryId is None
    assert saved.isPublic is True


def test_saved_itinerary_can_be_returned_as_later_exact_match(client) -> None:
    first_response = client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "paris",
            "bookId": "les-miserables",
            "durationDays": 2,
            "transportationMode": "walking",
        },
    )
    second_response = client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "paris",
            "bookId": "les-miserables",
            "durationDays": 2,
            "transportationMode": "walking",
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["matchedExisting"] is False
    assert second_response.json()["matchedExisting"] is True
    assert second_response.json()["sourceItineraryId"] == first_response.json()["itinerary"]["id"]
    assert second_response.json()["itinerary"]["sourceType"] == "exact_match"


def test_generated_itinerary_survives_new_test_client_with_same_database(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'persistent-repository.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as seed_session:
        seed_database(seed_session)

    def override_get_db():
        with TestingSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as first_client:
            generated = first_client.post(
                "/api/itinerary/generate",
                json={
                    "destinationId": "paris",
                    "bookId": "les-miserables",
                    "durationDays": 2,
                    "transportationMode": "walking",
                },
            ).json()["itinerary"]

        with TestClient(app) as restarted_client:
            detail = restarted_client.get(f"/api/itineraries/{generated['id']}")
            listing = restarted_client.get(
                "/api/itineraries",
                params={"city_id": "paris", "book_id": "les-miserables"},
            )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert detail.status_code == 200
    assert detail.json()["id"] == generated["id"]
    assert listing.status_code == 200
    assert generated["id"] in {itinerary["id"] for itinerary in listing.json()}


def test_legacy_missing_poi_filter_would_silently_drop_stop(db_session) -> None:
    source = database_repository.get_itinerary(db_session, "it-london-oliver-twist-1-walking")
    assert source is not None
    broken = _itinerary_variant_with_missing_poi(source, itinerary_id="it-legacy-drop-demo")
    intended_stop_count = _stop_count(broken)

    legacy_persisted_stop_count = sum(
        1
        for day in broken.days
        for stop in day.stops
        if db_session.get(POIModel, stop.poi.id) is not None
    )

    assert intended_stop_count > 0
    assert legacy_persisted_stop_count < intended_stop_count


def test_save_itinerary_with_existing_pois_persists_all_stops(db_session) -> None:
    source = database_repository.get_itinerary(db_session, "it-london-oliver-twist-1-walking")
    assert source is not None
    clone = _clone_itinerary(source, itinerary_id="it-persistence-existing-pois")

    database_repository.save_itinerary(db_session, clone)
    saved = database_repository.get_itinerary(db_session, clone.id)

    assert saved is not None
    assert _stop_count(saved) == _stop_count(clone)
    stop_rows = (
        db_session.query(ItineraryStopModel)
        .join(ItineraryStopModel.poi)
        .filter(ItineraryStopModel.id.in_(_stop_ids(clone)))
        .all()
    )
    assert len(stop_rows) == _stop_count(clone)


def test_save_itinerary_with_missing_poi_is_rejected_transactionally(db_session) -> None:
    source = database_repository.get_itinerary(db_session, "it-london-oliver-twist-1-walking")
    assert source is not None
    broken = _itinerary_variant_with_missing_poi(source, itinerary_id="it-missing-poi-rejected")

    try:
        database_repository.save_itinerary(db_session, broken)
    except ItineraryPersistenceError as exc:
        assert "unknown POI" in str(exc)
    else:
        raise AssertionError("save_itinerary accepted a missing POI")

    assert database_repository.get_itinerary(db_session, broken.id) is None
    assert db_session.query(ItineraryStopModel).filter(
        ItineraryStopModel.id.in_(_stop_ids(broken))
    ).count() == 0


def test_save_itinerary_with_mixed_pois_does_not_partially_persist(db_session) -> None:
    source = database_repository.get_itinerary(db_session, "it-london-oliver-twist-1-walking")
    assert source is not None
    broken = _itinerary_variant_with_missing_poi(source, itinerary_id="it-mixed-poi-rejected")

    try:
        database_repository.save_itinerary(db_session, broken)
    except ItineraryPersistenceError:
        pass
    else:
        raise AssertionError("save_itinerary accepted mixed valid and missing POIs")

    assert database_repository.get_itinerary(db_session, broken.id) is None
    assert db_session.query(ItineraryStopModel).filter(
        ItineraryStopModel.id.in_(_stop_ids(broken))
    ).count() == 0


def test_replacement_failure_preserves_existing_itinerary(db_session) -> None:
    source = database_repository.get_itinerary(db_session, "it-london-oliver-twist-1-walking")
    assert source is not None
    replacement_id = "it-replacement-atomicity"
    original = _clone_itinerary(source, itinerary_id=replacement_id)
    database_repository.save_itinerary(db_session, original)
    original_stop_count = _stop_count(original)

    broken_replacement = _itinerary_variant_with_missing_poi(
        original.model_copy(update={"title": "Broken replacement"}, deep=True),
        itinerary_id=replacement_id,
    )
    try:
        database_repository.save_itinerary(db_session, broken_replacement)
    except ItineraryPersistenceError:
        pass
    else:
        raise AssertionError("save_itinerary replaced an itinerary with missing POIs")

    saved = database_repository.get_itinerary(db_session, replacement_id)
    assert saved is not None
    assert saved.title == original.title
    assert _stop_count(saved) == original_stop_count


def test_save_itinerary_rejects_cross_destination_poi(db_session) -> None:
    source = database_repository.get_itinerary(db_session, "it-london-oliver-twist-1-walking")
    assert source is not None
    paris_poi = db_session.query(POIModel).filter(POIModel.destination_id == "paris").first()
    assert paris_poi is not None
    bad_poi = source.days[0].stops[0].poi.model_copy(update={"id": paris_poi.id})
    bad_stop = source.days[0].stops[0].model_copy(update={"poi": bad_poi}, deep=True)
    bad_day = source.days[0].model_copy(update={"stops": [bad_stop]}, deep=True)
    bad = source.model_copy(
        update={"id": "it-cross-destination-rejected", "days": [bad_day]},
        deep=True,
    )

    try:
        database_repository.save_itinerary(db_session, bad)
    except ItineraryPersistenceError as exc:
        assert "outside destination" in str(exc)
    else:
        raise AssertionError("save_itinerary accepted a cross-destination POI")


def _clone_itinerary(source, *, itinerary_id: str):
    return source.model_copy(
        update={
            "id": itinerary_id,
            "title": f"{source.title} persistence clone",
            "sourceItineraryId": source.id,
            "days": [
                day.model_copy(
                    update={
                        "id": f"{itinerary_id}-day-{day.dayNumber}",
                        "stops": [
                            stop.model_copy(
                                update={
                                    "id": (
                                        f"{itinerary_id}-day-{day.dayNumber}-"
                                        f"stop-{stop.order}"
                                    )
                                },
                                deep=True,
                            )
                            for stop in day.stops
                        ],
                    },
                    deep=True,
                )
                for day in source.days
            ],
        },
        deep=True,
    )


def _itinerary_variant_with_missing_poi(source, *, itinerary_id: str):
    clone = _clone_itinerary(source, itinerary_id=itinerary_id)
    first_day = clone.days[0]
    first_stop = first_day.stops[0]
    missing_poi = first_stop.poi.model_copy(
        update={"id": f"{itinerary_id}-missing-poi"},
        deep=True,
    )
    replacement_stop = first_stop.model_copy(update={"poi": missing_poi}, deep=True)
    replacement_day = first_day.model_copy(
        update={"stops": [replacement_stop, *first_day.stops[1:]]},
        deep=True,
    )
    return clone.model_copy(
        update={"days": [replacement_day, *clone.days[1:]]},
        deep=True,
    )


def _stop_count(itinerary) -> int:
    return sum(len(day.stops) for day in itinerary.days)


def _stop_ids(itinerary) -> list[str]:
    return [stop.id for day in itinerary.days for stop in day.stops]
