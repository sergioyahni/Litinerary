from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    BookIngestionJobModel,
    BookLocationCandidateModel,
    BookModel,
    BookProcessingArtifactModel,
    BookSourceModel,
    DestinationModel,
    EmbeddingRecordModel,
    ItineraryDayModel,
    ItineraryModel,
    ItineraryStopModel,
    POIModel,
    UserModel,
    UserPreferenceModel,
    UserReviewModel,
    book_destinations,
    poi_books,
    user_bookmarks,
)
from app.schemas.domain import Book, Destination, Itinerary, POI
from app.schemas.seed_admin import SeedDataPayload, SeedOperationResult, SeedValidationReport
from app.services.database_repository import (
    book_from_model,
    destination_from_model,
    itinerary_from_model,
    itinerary_to_model,
    poi_from_model,
)
from app.services.seed import seed_database


SUPPORTED_TRANSPORTATION_MODES = {"walking", "public_transport", "car_taxi"}


def load_seed_data(db: Session) -> SeedOperationResult:
    counts = seed_database(db)
    return SeedOperationResult(message="Loaded bundled development seed data.", counts=counts)


def reset_dev_data(db: Session) -> SeedOperationResult:
    _clear_development_data(db)
    counts = seed_database(db)
    return SeedOperationResult(
        message="Reset local development database and reloaded bundled seed data.",
        counts=counts,
    )


def export_seed_data(db: Session) -> SeedDataPayload:
    destinations = [
        destination_from_model(row)
        for row in db.scalars(select(DestinationModel).order_by(DestinationModel.id)).all()
    ]
    books = [
        book_from_model(row)
        for row in db.scalars(
            select(BookModel)
            .options(selectinload(BookModel.destinations))
            .order_by(BookModel.id)
        ).unique().all()
    ]
    pois = [
        poi_from_model(row)
        for row in db.scalars(
            select(POIModel)
            .options(selectinload(POIModel.books))
            .order_by(POIModel.id)
        ).unique().all()
    ]
    itineraries = [
        itinerary_from_model(row)
        for row in db.scalars(
            select(ItineraryModel)
            .options(_itinerary_load_options())
            .order_by(ItineraryModel.id)
        ).unique().all()
    ]
    return SeedDataPayload(
        destinations=destinations,
        books=books,
        pois=pois,
        itineraries=itineraries,
    )


def import_seed_data(db: Session, payload: SeedDataPayload) -> SeedOperationResult:
    validation = validate_seed_data(payload)
    if not validation.valid:
        return SeedOperationResult(
            message="Seed data import rejected because validation failed.",
            validation=validation,
        )

    _clear_seed_domain_data(db)
    _import_destinations(db, payload.destinations)
    db.flush()
    _import_books(db, payload.books)
    db.flush()
    _import_pois(db, payload.pois)
    db.flush()
    _import_itineraries(db, payload.itineraries)
    db.commit()

    return SeedOperationResult(
        message="Imported development seed data.",
        counts=validation.counts,
        validation=validation,
    )


def validate_current_seed_data(db: Session) -> SeedValidationReport:
    return validate_seed_data(export_seed_data(db))


def validate_seed_data(payload: SeedDataPayload) -> SeedValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    destination_ids = {destination.id for destination in payload.destinations}
    book_ids = {book.id for book in payload.books}
    poi_ids = {poi.id for poi in payload.pois}

    _check_unique("destination", [destination.id for destination in payload.destinations], errors)
    _check_unique("book", [book.id for book in payload.books], errors)
    _check_unique("poi", [poi.id for poi in payload.pois], errors)
    _check_unique("itinerary", [item.id for item in payload.itineraries], errors)

    for destination in payload.destinations:
        if not destination.name or not destination.country or not destination.description:
            errors.append(f"Destination '{destination.id}' is missing required text fields.")
        if not _has_coordinates(destination.latitude, destination.longitude):
            errors.append(f"Destination '{destination.id}' is missing map coordinates.")

    for book in payload.books:
        if not book.title or not book.author or not book.description:
            errors.append(f"Book '{book.id}' is missing required text fields.")
        if not book.destinationIds:
            errors.append(f"Book '{book.id}' is not linked to any destination.")
        for destination_id in book.destinationIds:
            if destination_id not in destination_ids:
                errors.append(
                    f"Book '{book.id}' references unknown destination '{destination_id}'."
                )

    for poi in payload.pois:
        if poi.destinationId not in destination_ids:
            errors.append(f"POI '{poi.id}' references unknown destination '{poi.destinationId}'.")
        for book_id in poi.bookIds:
            if book_id not in book_ids:
                errors.append(f"POI '{poi.id}' references unknown book '{book_id}'.")
        if not poi.name or not poi.description or not poi.literaryRelevance:
            errors.append(f"POI '{poi.id}' is missing required text fields.")
        if not _has_coordinates(poi.latitude, poi.longitude):
            errors.append(f"POI '{poi.id}' is missing map coordinates.")
        if not poi.verificationNotes and not poi.provenanceMetadata:
            errors.append(
                f"POI '{poi.id}' is missing grounding provenance or candidate source notes."
            )

    for itinerary in payload.itineraries:
        if itinerary.destinationId not in destination_ids:
            errors.append(
                f"Itinerary '{itinerary.id}' references unknown destination '{itinerary.destinationId}'."
            )
        if itinerary.bookId not in book_ids:
            errors.append(f"Itinerary '{itinerary.id}' references unknown book '{itinerary.bookId}'.")
        else:
            book = next(book for book in payload.books if book.id == itinerary.bookId)
            if itinerary.destinationId not in book.destinationIds:
                errors.append(
                    f"Itinerary '{itinerary.id}' book '{book.id}' is not linked to destination '{itinerary.destinationId}'."
                )
        if itinerary.transportationMode not in SUPPORTED_TRANSPORTATION_MODES:
            errors.append(
                f"Itinerary '{itinerary.id}' uses unsupported transportation mode '{itinerary.transportationMode}'."
            )
        if not itinerary.days:
            errors.append(f"Itinerary '{itinerary.id}' has no days.")
        for day in itinerary.days:
            orders = [stop.order for stop in day.stops]
            if orders != list(range(1, len(day.stops) + 1)):
                errors.append(
                    f"Itinerary '{itinerary.id}' day {day.dayNumber} stops are not ordered from 1."
                )
            if not day.stops:
                warnings.append(f"Itinerary '{itinerary.id}' day {day.dayNumber} has no stops.")
            for stop in day.stops:
                if stop.poi.id not in poi_ids:
                    errors.append(
                        f"Itinerary '{itinerary.id}' stop '{stop.id}' references unknown POI '{stop.poi.id}'."
                    )
                if not _has_coordinates(stop.poi.latitude, stop.poi.longitude):
                    errors.append(
                        f"Itinerary '{itinerary.id}' stop '{stop.id}' POI is missing map coordinates."
                    )

    counts = {
        "destinations": len(payload.destinations),
        "books": len(payload.books),
        "pois": len(payload.pois),
        "itineraries": len(payload.itineraries),
    }
    return SeedValidationReport(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        counts=counts,
    )


def _import_destinations(db: Session, destinations: list[Destination]) -> None:
    for destination in destinations:
        db.add(
            DestinationModel(
                id=destination.id,
                name=destination.name,
                country=destination.country,
                region=destination.region,
                description=destination.description,
                latitude=destination.latitude,
                longitude=destination.longitude,
                image_url=destination.imageUrl,
                supported=destination.supported,
            )
        )


def _import_books(db: Session, books: list[Book]) -> None:
    for book in books:
        row = BookModel(
            id=book.id,
            title=book.title,
            author=book.author,
            description=book.description,
            publication_year=book.publicationYear,
            public_domain=book.publicDomain,
            themes=book.themes,
            cover_url=book.coverUrl,
        )
        row.destinations = [
            destination
            for destination_id in book.destinationIds
            if (destination := db.get(DestinationModel, destination_id)) is not None
        ]
        db.add(row)


def _import_pois(db: Session, pois: list[POI]) -> None:
    for poi in pois:
        row = POIModel(
            id=poi.id,
            destination_id=poi.destinationId,
            name=poi.name,
            description=poi.description,
            latitude=poi.latitude,
            longitude=poi.longitude,
            address=poi.address,
            estimated_duration_minutes=poi.estimatedDurationMinutes,
            ticketing_note=poi.ticketingNote,
            literary_relevance=poi.literaryRelevance,
            verification_status=poi.verificationStatus,
            verification_provider=poi.verificationProvider,
            provider_version=poi.providerVersion,
            provider_request_id=poi.providerRequestId,
            verification_confidence=poi.verificationConfidence,
            verified_name=poi.verifiedName,
            verified_address=poi.verifiedAddress,
            verified_latitude=poi.verifiedLatitude,
            verified_longitude=poi.verifiedLongitude,
            opening_hours_note=poi.openingHoursNote,
            ticketing_url=poi.ticketingUrl,
            verification_notes=poi.verificationNotes,
            last_verified_at=poi.lastVerifiedAt,
            manual_review_status=poi.manualReviewStatus,
            reviewed_by_user_id=poi.reviewedByUserId,
            provenance_metadata=poi.provenanceMetadata,
        )
        row.books = [
            book
            for book_id in poi.bookIds
            if (book := db.get(BookModel, book_id)) is not None
        ]
        db.add(row)


def _import_itineraries(db: Session, itineraries: list[Itinerary]) -> None:
    for itinerary in itineraries:
        db.add(itinerary_to_model(db, itinerary))


def _clear_development_data(db: Session) -> None:
    _clear_user_data(db)
    _clear_seed_domain_data(db)


def _clear_user_data(db: Session) -> None:
    db.execute(delete(user_bookmarks))
    db.execute(delete(UserReviewModel))
    db.execute(delete(UserPreferenceModel))
    db.execute(delete(UserModel))
    db.flush()


def _clear_seed_domain_data(db: Session) -> None:
    db.execute(delete(BookProcessingArtifactModel))
    db.execute(delete(EmbeddingRecordModel))
    db.execute(delete(BookLocationCandidateModel))
    db.execute(delete(BookIngestionJobModel))
    db.execute(delete(BookSourceModel))
    db.execute(delete(ItineraryStopModel))
    db.execute(delete(ItineraryDayModel))
    db.execute(delete(ItineraryModel))
    db.execute(delete(poi_books))
    db.execute(delete(POIModel))
    db.execute(delete(book_destinations))
    db.execute(delete(BookModel))
    db.execute(delete(DestinationModel))
    db.flush()


def _check_unique(label: str, ids: list[str], errors: list[str]) -> None:
    seen: set[str] = set()
    for item_id in ids:
        if item_id in seen:
            errors.append(f"Duplicate {label} ID '{item_id}'.")
        seen.add(item_id)


def _has_coordinates(latitude: float | None, longitude: float | None) -> bool:
    if latitude is None or longitude is None:
        return False
    if latitude == 0 or longitude == 0:
        return False
    return -90 <= latitude <= 90 and -180 <= longitude <= 180


def _itinerary_load_options():
    return (
        selectinload(ItineraryModel.days)
        .selectinload(ItineraryDayModel.stops)
        .selectinload(ItineraryStopModel.poi)
        .selectinload(POIModel.books)
    )
