from sqlalchemy.orm import Session

from app.data.mock_data import BOOKS, DESTINATIONS, ITINERARIES, POIS
from app.models import BookModel, DestinationModel, ItineraryModel, POIModel
from app.services.database_repository import itinerary_to_model


def seed_database(db: Session) -> dict[str, int]:
    destinations = _seed_destinations(db)
    db.flush()
    books = _seed_books(db)
    db.flush()
    pois = _seed_pois(db)
    db.flush()
    itineraries = _seed_itineraries(db)
    db.commit()

    return {
        "destinations": destinations,
        "books": books,
        "pois": pois,
        "itineraries": itineraries,
    }


def _seed_destinations(db: Session) -> int:
    count = 0
    for destination in DESTINATIONS:
        row = db.get(DestinationModel, destination.id)
        if row is None:
            row = DestinationModel(id=destination.id)
            db.add(row)
            count += 1

        row.name = destination.name
        row.country = destination.country
        row.region = destination.region
        row.description = destination.description
        row.latitude = destination.latitude
        row.longitude = destination.longitude
        row.image_url = destination.imageUrl
        row.supported = destination.supported

    return count


def _seed_books(db: Session) -> int:
    count = 0
    for book in BOOKS:
        row = db.get(BookModel, book.id)
        if row is None:
            row = BookModel(id=book.id)
            db.add(row)
            count += 1

        row.title = book.title
        row.author = book.author
        row.description = book.description
        row.publication_year = book.publicationYear
        row.public_domain = book.publicDomain
        row.themes = book.themes
        row.cover_url = book.coverUrl
        row.destinations = [
            destination
            for destination_id in book.destinationIds
            if (destination := db.get(DestinationModel, destination_id)) is not None
        ]

    return count


def _seed_pois(db: Session) -> int:
    count = 0
    for poi in POIS:
        row = db.get(POIModel, poi.id)
        if row is None:
            row = POIModel(id=poi.id)
            db.add(row)
            count += 1

        row.destination_id = poi.destinationId
        row.name = poi.name
        row.description = poi.description
        row.latitude = poi.latitude
        row.longitude = poi.longitude
        row.address = poi.address
        row.estimated_duration_minutes = poi.estimatedDurationMinutes
        row.ticketing_note = poi.ticketingNote
        row.literary_relevance = poi.literaryRelevance
        row.verification_status = (
            "mock_verified" if poi.verificationStatus in {"mock", "verified"} else poi.verificationStatus
        )
        row.verification_provider = "seed_data"
        row.provider_version = "bundled-seed"
        row.provider_request_id = f"seed-poi-{poi.id}"
        row.verification_confidence = 1.0
        row.verified_name = poi.name
        row.verified_address = poi.address
        row.verified_latitude = poi.latitude
        row.verified_longitude = poi.longitude
        row.opening_hours_note = None
        row.ticketing_url = None
        row.verification_notes = ["Seeded mock POI; verify with a real provider later."]
        row.last_verified_at = None
        row.manual_review_status = "not_reviewed"
        row.reviewed_by_user_id = None
        row.provenance_metadata = {
            "source": "bundled_seed_data",
            "externalProviderUsed": False,
        }
        row.books = [
            book
            for book_id in poi.bookIds
            if (book := db.get(BookModel, book_id)) is not None
        ]

    return count


def _seed_itineraries(db: Session) -> int:
    count = 0
    for itinerary in ITINERARIES:
        existing = db.get(ItineraryModel, itinerary.id)
        if existing is not None:
            db.delete(existing)
            db.flush()
        else:
            count += 1

        model = itinerary_to_model(db, itinerary)
        model.created_by_mode = "seed"
        model.provider_name = "mock_local"
        model.provider_type = "llm"
        model.provider_version = "bundled-seed"
        model.provider_request_id = f"seed-itinerary-{itinerary.id}"
        model.generated_by_service = "seed_data"
        model.confidence_score = 1.0
        model.provenance_metadata = {
            "source": "bundled_seed_data",
            "externalProviderUsed": False,
        }
        db.add(model)

    return count
