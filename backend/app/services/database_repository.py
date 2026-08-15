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


def database_has_seed_data(db: Session) -> bool:
    try:
        return db.scalar(select(DestinationModel.id).limit(1)) is not None
    except OperationalError:
        db.rollback()
        return False


def list_destinations(db: Session) -> list[Destination]:
    rows = db.scalars(select(DestinationModel)).all()
    rows = _sort_by_mock_order(rows, [destination.id for destination in DESTINATIONS])
    return [destination_from_model(row) for row in rows]


def get_destination(db: Session, destination_id: str) -> Destination | None:
    row = db.get(DestinationModel, destination_id)
    return destination_from_model(row) if row else None


def list_books(db: Session, city_id: str | None = None) -> list[Book]:
    statement = select(BookModel).options(selectinload(BookModel.destinations))

    if city_id is not None:
        statement = statement.join(BookModel.destinations).where(DestinationModel.id == city_id)

    rows = db.scalars(statement).unique().all()
    rows = _sort_by_mock_order(rows, [book.id for book in BOOKS])
    return [book_from_model(row) for row in rows]


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
    validate_itinerary_access_invariants(db, itinerary)
    existing = db.get(ItineraryModel, itinerary.id)
    if existing is not None:
        db.delete(existing)
        db.flush()

    model = itinerary_to_model(db, itinerary)
    db.add(model)
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
    )


def itinerary_to_model(db: Session, itinerary: Itinerary) -> ItineraryModel:
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
                    if db.get(POIModel, stop.poi.id) is not None
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


def _sort_by_mock_order(rows, ordered_ids: list[str]):
    order = {item_id: index for index, item_id in enumerate(ordered_ids)}
    return sorted(rows, key=lambda row: (order.get(row.id, len(order)), row.id))


def _normalized_verification_status(status: str) -> str:
    if status == "mock":
        return "mock_verified"
    if status == "verified":
        return "provider_verified"
    return status
