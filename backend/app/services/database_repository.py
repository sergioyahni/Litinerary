from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, selectinload

from app.core.auth import CurrentUser
from app.data.mock_data import BOOKS, DESTINATIONS, ITINERARIES
from app.models import (
    BookModel,
    DestinationModel,
    ItineraryDayModel,
    ItineraryModel,
    ItineraryStopModel,
    POIModel,
    UserModel,
)
from app.schemas.domain import Book, Destination, Itinerary, ItineraryDay, ItineraryStop, POI


class ItineraryPersistenceError(ValueError):
    """Raised when an itinerary cannot be saved without losing relational integrity."""


def database_has_seed_data(db: Session) -> bool:
    try:
        return db.scalar(select(DestinationModel.id).limit(1)) is not None
    except OperationalError:
        db.rollback()
        return False


def list_destinations(db: Session) -> list[Destination]:
    return search_public_destinations(db, query="")


def get_destination(db: Session, destination_id: str) -> Destination | None:
    row = db.get(DestinationModel, destination_id)
    return destination_from_model(row) if row else None


def list_books(db: Session, city_id: str | None = None) -> list[Book]:
    return search_public_books(db, query="", destination_id=city_id)


def search_public_destinations(db: Session, *, query: str = "") -> list[Destination]:
    normalized = query.strip().lower()
    itineraries = list_itineraries(db)
    by_id: dict[str, Destination] = {}
    for itinerary in itineraries:
        destination = destination_from_itinerary(itinerary)
        if normalized and normalized not in " ".join(
            [
                destination.id,
                destination.name,
                destination.country,
                destination.region or "",
            ]
        ).lower():
            continue
        by_id.setdefault(destination.id, destination)
    ordered = _sort_by_mock_order(list(by_id.values()), [destination.id for destination in DESTINATIONS])
    return ordered


def search_public_books(
    db: Session,
    *,
    query: str = "",
    destination_id: str | None = None,
) -> list[Book]:
    normalized = query.strip().lower()
    itineraries = list_itineraries(db, city_id=destination_id)
    grouped_destination_ids: dict[str, set[str]] = {}
    by_id: dict[str, Book] = {}
    for itinerary in itineraries:
        book = book_from_itinerary(itinerary)
        grouped_destination_ids.setdefault(book.id, set()).add(itinerary.destinationId)
        if normalized and normalized not in " ".join(
            [book.id, book.title, book.author, " ".join(book.themes)]
        ).lower():
            continue
        by_id.setdefault(book.id, book)
    for book_id, book in by_id.items():
        book.destinationIds[:] = sorted(grouped_destination_ids.get(book_id, set()))
    return _sort_by_mock_order(list(by_id.values()), [book.id for book in BOOKS])


def get_book(db: Session, book_id: str) -> Book | None:
    row = db.scalars(
        select(BookModel)
        .where(BookModel.id == book_id)
        .options(selectinload(BookModel.destinations))
    ).first()
    return book_from_model(row) if row else None


def list_pois_for_book(db: Session, destination_id: str, book_id: str) -> list[POI]:
    rows = db.scalars(
        select(POIModel)
        .join(POIModel.books)
        .where(POIModel.destination_id == destination_id, BookModel.id == book_id)
        .options(selectinload(POIModel.books))
    ).unique().all()
    return [poi_from_model(row) for row in rows]


def list_pois_for_destination(db: Session, destination_id: str) -> list[POI]:
    rows = db.scalars(
        select(POIModel)
        .where(POIModel.destination_id == destination_id)
        .options(selectinload(POIModel.books))
    ).unique().all()
    return [poi_from_model(row) for row in rows]


def list_itineraries(
    db: Session,
    city_id: str | None = None,
    book_id: str | None = None,
    transportation_mode: str | None = None,
) -> list[Itinerary]:
    statement = select(ItineraryModel).options(_itinerary_load_options())
    statement = statement.where(
        ItineraryModel.is_public.is_(True),
        ItineraryModel.visibility == "public",
    )

    if city_id is not None:
        statement = statement.where(ItineraryModel.destination_id == city_id)

    if book_id is not None:
        statement = statement.where(ItineraryModel.book_id == book_id)

    if transportation_mode is not None:
        statement = statement.where(ItineraryModel.transportation_mode == transportation_mode)

    rows = db.scalars(statement).unique().all()
    rows = _sort_by_mock_order(rows, [itinerary.id for itinerary in ITINERARIES])
    return [itinerary_from_model(row) for row in rows]


def has_public_itinerary_for_book(db: Session, book_id: str) -> bool:
    return (
        db.scalar(
            select(ItineraryModel.id)
            .where(
                ItineraryModel.book_id == book_id,
                ItineraryModel.is_public.is_(True),
                ItineraryModel.visibility == "public",
            )
            .limit(1)
        )
        is not None
    )


def find_exact_itinerary(
    db: Session,
    city_id: str,
    book_id: str,
    duration_days: int,
    transportation_mode: str,
) -> Itinerary | None:
    row = db.scalars(
        select(ItineraryModel)
        .where(
            ItineraryModel.destination_id == city_id,
            ItineraryModel.book_id == book_id,
            ItineraryModel.duration_days == duration_days,
            ItineraryModel.transportation_mode == transportation_mode,
            ItineraryModel.is_public.is_(True),
            ItineraryModel.visibility == "public",
        )
        .options(_itinerary_load_options())
        .limit(1)
    ).first()
    return itinerary_from_model(row) if row else None


def find_partial_itinerary(db: Session, city_id: str, book_id: str) -> Itinerary | None:
    row = db.scalars(
        select(ItineraryModel)
        .where(
            ItineraryModel.destination_id == city_id,
            ItineraryModel.book_id == book_id,
            ItineraryModel.is_public.is_(True),
            ItineraryModel.visibility == "public",
        )
        .options(_itinerary_load_options())
        .order_by(ItineraryModel.created_at, ItineraryModel.id)
        .limit(1)
    ).first()
    return itinerary_from_model(row) if row else None


def get_itinerary(db: Session, itinerary_id: str) -> Itinerary | None:
    row = db.scalars(
        select(ItineraryModel)
        .where(ItineraryModel.id == itinerary_id)
        .options(_itinerary_load_options())
    ).first()
    return itinerary_from_model(row) if row else None


def get_accessible_itinerary(
    db: Session,
    itinerary_id: str,
    current_user: CurrentUser | None = None,
) -> Itinerary | None:
    row = get_accessible_itinerary_model(db, itinerary_id, current_user=current_user)
    return itinerary_from_model(row) if row else None


def get_accessible_itinerary_model(
    db: Session,
    itinerary_id: str,
    current_user: CurrentUser | None = None,
) -> ItineraryModel | None:
    row = db.scalars(
        select(ItineraryModel)
        .where(ItineraryModel.id == itinerary_id)
        .options(_itinerary_load_options())
    ).first()
    if row is None or not itinerary_row_is_accessible(row, current_user=current_user):
        return None
    return row


def itinerary_row_is_accessible(
    row: ItineraryModel,
    current_user: CurrentUser | None = None,
) -> bool:
    if itinerary_row_is_public_repository(row):
        return True
    if current_user is None:
        return False
    return current_user.is_admin or row.owner_user_id == current_user.id


def itinerary_is_accessible(
    itinerary: Itinerary,
    current_user: CurrentUser | None = None,
) -> bool:
    if itinerary.isPublic and itinerary.visibility == "public":
        return True
    if current_user is None:
        return False
    return current_user.is_admin or itinerary.ownerUserId == current_user.id


def itinerary_row_is_public_repository(row: ItineraryModel) -> bool:
    return row.is_public and row.visibility == "public"


def save_itinerary(db: Session, itinerary: Itinerary) -> None:
    try:
        validate_itinerary_access_invariants(db, itinerary)
        validate_itinerary_persistence_references(db, itinerary)
        existing = db.get(ItineraryModel, itinerary.id)
        if existing is not None:
            db.delete(existing)
            db.flush()

        model = itinerary_to_model(db, itinerary)
        db.add(model)
        db.flush()
    except Exception:
        db.rollback()
        raise
    db.commit()


def validate_itinerary_access_invariants(db: Session, itinerary: Itinerary) -> None:
    if itinerary.visibility == "public" and not itinerary.isPublic:
        raise ValueError("Public itinerary visibility requires isPublic=true.")
    if itinerary.visibility != "public" and itinerary.isPublic:
        raise ValueError("Private or unlisted itinerary visibility requires isPublic=false.")
    if itinerary.subscriberOnly and (
        itinerary.visibility != "private" or itinerary.isPublic or not itinerary.ownerUserId
    ):
        raise ValueError("Subscriber-only itineraries must be private and owner-bound.")
    if itinerary.ownerUserId and db.get(UserModel, itinerary.ownerUserId) is None:
        raise ValueError(f"Unknown itinerary owner: {itinerary.ownerUserId}")


def validate_itinerary_persistence_references(db: Session, itinerary: Itinerary) -> None:
    errors: list[str] = []
    if db.get(DestinationModel, itinerary.destinationId) is None:
        errors.append(f"Unknown itinerary destination: {itinerary.destinationId}")
    book = db.scalars(
        select(BookModel)
        .where(BookModel.id == itinerary.bookId)
        .options(selectinload(BookModel.destinations))
    ).first()
    external_book_metadata = itinerary.bookSourceType == "external" or bool(itinerary.bookProviderId)
    if book is None and not external_book_metadata:
        errors.append(
            f"Unknown itinerary book: {itinerary.bookId}. "
            "External books must be persisted on the itinerary metadata, not as placeholder books."
        )
    elif book is not None and itinerary.destinationId not in {destination.id for destination in book.destinations}:
        errors.append(
            f"Itinerary book '{itinerary.bookId}' is not linked to destination "
            f"'{itinerary.destinationId}'."
        )

    missing_poi_ids: list[str] = []
    wrong_destination_ids: list[str] = []
    wrong_book_ids: list[str] = []
    for day in itinerary.days:
        for stop in day.stops:
            poi = db.scalars(
                select(POIModel)
                .where(POIModel.id == stop.poi.id)
                .options(selectinload(POIModel.books))
            ).first()
            if poi is None:
                missing_poi_ids.append(stop.poi.id)
                continue
            if poi.destination_id != itinerary.destinationId:
                wrong_destination_ids.append(stop.poi.id)
            if book is not None and itinerary.bookId not in {book.id for book in poi.books}:
                wrong_book_ids.append(stop.poi.id)

    if missing_poi_ids:
        errors.append(
            "Itinerary references unknown POI(s): " + ", ".join(sorted(set(missing_poi_ids)))
        )
    if wrong_destination_ids:
        errors.append(
            "Itinerary references POI(s) outside destination "
            f"'{itinerary.destinationId}': "
            + ", ".join(sorted(set(wrong_destination_ids)))
        )
    if wrong_book_ids:
        errors.append(
            "Itinerary references POI(s) not linked to book "
            f"'{itinerary.bookId}': "
            + ", ".join(sorted(set(wrong_book_ids)))
        )
    if errors:
        raise ItineraryPersistenceError(" ".join(errors))


def destination_from_model(row: DestinationModel) -> Destination:
    return Destination(
        id=row.id,
        name=row.name,
        country=row.country,
        region=row.region,
        description=row.description,
        latitude=row.latitude,
        longitude=row.longitude,
        imageUrl=row.image_url,
        supported=row.supported,
        sourceType="repository",
    )


def book_from_model(row: BookModel) -> Book:
    return Book(
        id=row.id,
        destinationIds=[destination.id for destination in row.destinations],
        title=row.title,
        author=row.author,
        description=row.description,
        publicationYear=row.publication_year,
        publicDomain=row.public_domain,
        themes=row.themes or [],
        coverUrl=row.cover_url,
        sourceType="repository",
    )


def poi_from_model(row: POIModel) -> POI:
    return POI(
        id=row.id,
        destinationId=row.destination_id,
        bookIds=[book.id for book in row.books],
        name=row.name,
        description=row.description,
        latitude=row.latitude,
        longitude=row.longitude,
        address=row.address,
        estimatedDurationMinutes=row.estimated_duration_minutes,
        ticketingNote=row.ticketing_note,
        literaryRelevance=row.literary_relevance,
        verificationStatus=_normalized_verification_status(row.verification_status),
        verificationProvider=row.verification_provider,
        providerVersion=row.provider_version,
        providerRequestId=row.provider_request_id,
        verificationConfidence=row.verification_confidence,
        verifiedName=row.verified_name,
        verifiedAddress=row.verified_address,
        verifiedLatitude=row.verified_latitude,
        verifiedLongitude=row.verified_longitude,
        openingHoursNote=row.opening_hours_note,
        ticketingUrl=row.ticketing_url,
        verificationNotes=row.verification_notes or [],
        lastVerifiedAt=row.last_verified_at,
        manualReviewStatus=row.manual_review_status,
        reviewedByUserId=row.reviewed_by_user_id,
        provenanceMetadata=row.provenance_metadata or {},
    )


def itinerary_from_model(row: ItineraryModel) -> Itinerary:
    return Itinerary(
        id=row.id,
        destinationId=row.destination_id,
        bookId=row.book_id,
        title=row.title,
        summary=row.summary,
        durationDays=row.duration_days,
        transportationMode=row.transportation_mode,
        days=[
            ItineraryDay(
                id=day.id,
                dayNumber=day.day_number,
                title=day.title,
                summary=day.summary,
                estimatedDistanceKm=day.estimated_distance_km,
                estimatedDurationHours=day.estimated_duration_hours,
                routeGeometry=day.route_geometry or [],
                routingProviderMetadata=day.routing_provider_metadata,
                routingWarnings=day.routing_warnings or [],
                stops=[
                    ItineraryStop(
                        id=stop.id,
                        poi=poi_from_model(stop.poi),
                        order=stop.order,
                        title=stop.title,
                        narrativeNote=stop.narrative_note,
                        logisticsNote=stop.logistics_note,
                        estimatedStartTime=stop.estimated_start_time,
                        estimatedEndTime=stop.estimated_end_time,
                    )
                    for stop in day.stops
                ],
            )
            for day in row.days
        ],
        isPublic=row.is_public,
        ownerUserId=row.owner_user_id,
        visibility=row.visibility,
        generatedFrom=row.generated_from,
        sourceType=row.source_type,
        sourceItineraryId=row.source_itinerary_id,
        createdByMode=row.created_by_mode,
        createdByUserId=row.created_by_user_id,
        subscriberOnly=row.subscriber_only,
        adaptationNotes=row.adaptation_notes or [],
        createdAt=row.created_at,
        updatedAt=row.updated_at,
        providerName=row.provider_name,
        providerType=row.provider_type,
        providerVersion=row.provider_version,
        providerRequestId=row.provider_request_id,
        generatedByService=row.generated_by_service,
        confidenceScore=row.confidence_score,
        provenanceMetadata=row.provenance_metadata or {},
        bookTitle=row.book_title,
        bookAuthor=row.book_author,
        bookDescription=row.book_description,
        bookPublicationYear=row.book_publication_year,
        bookPublicDomain=row.book_public_domain,
        bookThemes=row.book_themes or [],
        bookCoverUrl=row.book_cover_url,
        bookSourceType=row.book_source_type,
        bookProviderId=row.book_provider_id,
        bookProvenanceMetadata=row.book_provenance_metadata or {},
        destinationName=row.destination_name,
        destinationCountry=row.destination_country,
        destinationRegion=row.destination_region,
        destinationDescription=row.destination_description,
        destinationLatitude=row.destination_latitude,
        destinationLongitude=row.destination_longitude,
        destinationImageUrl=row.destination_image_url,
        destinationSourceType=row.destination_source_type,
        destinationProviderId=row.destination_provider_id,
        destinationProvenanceMetadata=row.destination_provenance_metadata or {},
    )


def itinerary_to_model(db: Session, itinerary: Itinerary) -> ItineraryModel:
    seed_book = get_book_from_seed(itinerary.bookId)
    seed_destination = get_destination_from_seed(itinerary.destinationId)
    return ItineraryModel(
        id=itinerary.id,
        destination_id=itinerary.destinationId,
        book_id=itinerary.bookId,
        title=itinerary.title,
        summary=itinerary.summary,
        duration_days=itinerary.durationDays,
        transportation_mode=itinerary.transportationMode,
        is_public=itinerary.isPublic,
        owner_user_id=itinerary.ownerUserId,
        visibility=itinerary.visibility,
        generated_from=itinerary.generatedFrom,
        source_type=itinerary.sourceType,
        source_itinerary_id=itinerary.sourceItineraryId,
        created_by_mode=itinerary.createdByMode,
        created_by_user_id=itinerary.createdByUserId,
        subscriber_only=itinerary.subscriberOnly,
        adaptation_notes=itinerary.adaptationNotes,
        created_at=itinerary.createdAt,
        updated_at=itinerary.updatedAt,
        provider_name=itinerary.providerName,
        provider_type=itinerary.providerType,
        provider_version=itinerary.providerVersion,
        provider_request_id=itinerary.providerRequestId,
        generated_by_service=itinerary.generatedByService,
        confidence_score=itinerary.confidenceScore,
        provenance_metadata=itinerary.provenanceMetadata,
        book_title=itinerary.bookTitle or (seed_book.title if seed_book else None),
        book_author=itinerary.bookAuthor or (seed_book.author if seed_book else None),
        book_description=itinerary.bookDescription or (seed_book.description if seed_book else None),
        book_publication_year=itinerary.bookPublicationYear
        if itinerary.bookPublicationYear is not None
        else (seed_book.publicationYear if seed_book else None),
        book_public_domain=itinerary.bookPublicDomain
        if itinerary.bookPublicDomain is not None
        else (seed_book.publicDomain if seed_book else None),
        book_themes=itinerary.bookThemes or (seed_book.themes if seed_book else []),
        book_cover_url=itinerary.bookCoverUrl or (seed_book.coverUrl if seed_book else None),
        book_source_type=itinerary.bookSourceType or ("repository" if seed_book else None),
        book_provider_id=itinerary.bookProviderId,
        book_provenance_metadata=itinerary.bookProvenanceMetadata,
        destination_name=itinerary.destinationName
        or (seed_destination.name if seed_destination else None),
        destination_country=itinerary.destinationCountry
        or (seed_destination.country if seed_destination else None),
        destination_region=itinerary.destinationRegion
        or (seed_destination.region if seed_destination else None),
        destination_description=itinerary.destinationDescription
        or (seed_destination.description if seed_destination else None),
        destination_latitude=itinerary.destinationLatitude
        if itinerary.destinationLatitude is not None
        else (seed_destination.latitude if seed_destination else None),
        destination_longitude=itinerary.destinationLongitude
        if itinerary.destinationLongitude is not None
        else (seed_destination.longitude if seed_destination else None),
        destination_image_url=itinerary.destinationImageUrl
        or (seed_destination.imageUrl if seed_destination else None),
        destination_source_type=itinerary.destinationSourceType
        or ("repository" if seed_destination else None),
        destination_provider_id=itinerary.destinationProviderId,
        destination_provenance_metadata=itinerary.destinationProvenanceMetadata,
        days=[
            ItineraryDayModel(
                id=day.id,
                day_number=day.dayNumber,
                title=day.title,
                summary=day.summary,
                estimated_distance_km=day.estimatedDistanceKm,
                estimated_duration_hours=day.estimatedDurationHours,
                route_geometry=day.routeGeometry,
                routing_provider_metadata=day.routingProviderMetadata,
                routing_warnings=day.routingWarnings,
                stops=[
                    ItineraryStopModel(
                        id=stop.id,
                        poi_id=stop.poi.id,
                        order=stop.order,
                        title=stop.title,
                        narrative_note=stop.narrativeNote,
                        logistics_note=stop.logisticsNote,
                        estimated_start_time=stop.estimatedStartTime,
                        estimated_end_time=stop.estimatedEndTime,
                    )
                    for stop in day.stops
                ],
            )
            for day in itinerary.days
        ],
    )


def _itinerary_load_options():
    return (
        selectinload(ItineraryModel.days)
        .selectinload(ItineraryDayModel.stops)
        .selectinload(ItineraryStopModel.poi)
        .selectinload(POIModel.books)
    )


def book_from_itinerary(itinerary: Itinerary) -> Book:
    catalog_book = get_book_from_seed(itinerary.bookId)
    return Book(
        id=itinerary.bookId,
        destinationIds=[itinerary.destinationId],
        title=itinerary.bookTitle or (catalog_book.title if catalog_book else itinerary.bookId),
        author=itinerary.bookAuthor or (catalog_book.author if catalog_book else "Unknown"),
        description=itinerary.bookDescription
        or (catalog_book.description if catalog_book else itinerary.summary),
        publicationYear=itinerary.bookPublicationYear
        if itinerary.bookPublicationYear is not None
        else (catalog_book.publicationYear if catalog_book else None),
        publicDomain=itinerary.bookPublicDomain
        if itinerary.bookPublicDomain is not None
        else (catalog_book.publicDomain if catalog_book else False),
        themes=itinerary.bookThemes or (catalog_book.themes if catalog_book else []),
        coverUrl=itinerary.bookCoverUrl or (catalog_book.coverUrl if catalog_book else None),
        sourceType=itinerary.bookSourceType or ("repository" if catalog_book else "itinerary_snapshot"),
        providerId=itinerary.bookProviderId,
        provenanceMetadata=itinerary.bookProvenanceMetadata,
    )


def destination_from_itinerary(itinerary: Itinerary) -> Destination:
    catalog_destination = get_destination_from_seed(itinerary.destinationId)
    return Destination(
        id=itinerary.destinationId,
        name=itinerary.destinationName
        or (catalog_destination.name if catalog_destination else itinerary.destinationId),
        country=itinerary.destinationCountry
        or (catalog_destination.country if catalog_destination else "Unknown"),
        region=itinerary.destinationRegion
        or (catalog_destination.region if catalog_destination else None),
        description=itinerary.destinationDescription
        or (catalog_destination.description if catalog_destination else itinerary.summary),
        latitude=itinerary.destinationLatitude
        if itinerary.destinationLatitude is not None
        else (catalog_destination.latitude if catalog_destination else 0),
        longitude=itinerary.destinationLongitude
        if itinerary.destinationLongitude is not None
        else (catalog_destination.longitude if catalog_destination else 0),
        imageUrl=itinerary.destinationImageUrl
        or (catalog_destination.imageUrl if catalog_destination else None),
        supported=True,
        sourceType=itinerary.destinationSourceType
        or ("repository" if catalog_destination else "itinerary_snapshot"),
        providerId=itinerary.destinationProviderId,
        provenanceMetadata=itinerary.destinationProvenanceMetadata,
    )


def get_book_from_seed(book_id: str) -> Book | None:
    return next((book for book in BOOKS if book.id == book_id), None)


def get_destination_from_seed(destination_id: str) -> Destination | None:
    return next((destination for destination in DESTINATIONS if destination.id == destination_id), None)


def _sort_by_mock_order(rows, ordered_ids: list[str]):
    order = {item_id: index for index, item_id in enumerate(ordered_ids)}
    return sorted(rows, key=lambda row: (order.get(row.id, len(order)), row.id))


def _normalized_verification_status(status: str) -> str:
    if status == "mock":
        return "mock_verified"
    if status == "verified":
        return "provider_verified"
    return status
