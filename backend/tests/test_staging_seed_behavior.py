from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import BookModel, DestinationModel, ItineraryModel, POIModel
from app.services.seed import seed_database


def test_seed_database_is_rerunnable_without_duplicate_reference_rows(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'seed-idempotence.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        first = seed_database(db)
        second = seed_database(db)
        counts = {
            "destinations": db.query(DestinationModel).count(),
            "books": db.query(BookModel).count(),
            "pois": db.query(POIModel).count(),
            "itineraries": db.query(ItineraryModel).count(),
        }

    engine.dispose()

    assert first == {"destinations": 5, "books": 10, "pois": 13, "itineraries": 2}
    assert second == {"destinations": 0, "books": 0, "pois": 0, "itineraries": 0}
    assert counts == {"destinations": 5, "books": 10, "pois": 13, "itineraries": 2}
