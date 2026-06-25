from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.data.mock_data import POIS
from app.models import domain  # noqa: F401
from app.services import database_repository
from app.services.llm_grounding import validate_poi_for_grounding
from app.services.seed import seed_database


def test_seed_database_loads_mock_catalog_and_itineraries(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'litinerary-test.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        counts = seed_database(db)

        assert counts == {
            "destinations": 5,
            "books": 10,
            "pois": 13,
            "itineraries": 2,
        }
        london_books = database_repository.list_books(db, city_id="london")
        seeded_itinerary = database_repository.get_itinerary(
            db,
            "it-london-oliver-twist-1-walking",
        )

    assert {book.id for book in london_books} == {"oliver-twist", "sherlock-holmes"}
    assert seeded_itinerary is not None
    assert seeded_itinerary.days[0].stops[0].poi.id == "smithfield-market"


def test_london_sherlock_smoke_poi_is_grounding_safe_in_seed_data() -> None:
    baker_street = next(poi for poi in POIS if poi.id == "baker-street")

    validate_poi_for_grounding(baker_street)
    assert baker_street.verificationNotes
    assert baker_street.provenanceMetadata


def test_london_sherlock_smoke_poi_is_grounding_safe_after_database_seed(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'litinerary-test.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        seed_database(db)
        pois = database_repository.list_pois_for_book(
            db,
            destination_id="london",
            book_id="sherlock-holmes",
        )

    baker_street = next(poi for poi in pois if poi.id == "baker-street")
    validate_poi_for_grounding(baker_street)
    assert baker_street.verificationNotes
    assert baker_street.provenanceMetadata
