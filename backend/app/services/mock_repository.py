from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.config import get_settings
from app.core.errors import mock_judge_rejected, not_found, not_found_detail, validation_error
from app.data.mock_data import BOOKS, DESTINATIONS, ITINERARIES, POIS
from app.schemas.domain import (
    Book,
    Destination,
    Itinerary,
    ItineraryAdaptationRequest,
    ItineraryGenerationRequest,
    ItineraryGenerationResponse,
    POI,
    TransportationMode,
)
from app.services import database_repository as db_repository
from app.services.mock_ai_service import get_ai_pipeline
from app.services.openai_compatible_llm_adapter import live_llm_request_scope
from app.services.routing_service import enrich_itinerary_routes
from app.services.usage_policy import get_usage_guard


def _use_database(db: Session | None) -> bool:
    if db is None:
        return False
    if get_settings().is_deployed_environment:
        return True
    return db_repository.database_has_seed_data(db)


def list_destinations(db: Session | None = None) -> list[Destination]:
    if _use_database(db):
        return db_repository.list_destinations(db)
    return DESTINATIONS


def get_destination(destination_id: str, db: Session | None = None) -> Destination:
    if _use_database(db):
        destination = db_repository.get_destination(db, destination_id)
        if destination is not None:
            return destination
        raise not_found("destination", destination_id)

    for destination in DESTINATIONS:
        if destination.id == destination_id:
            return destination
    raise not_found("destination", destination_id)


def get_book(book_id: str, db: Session | None = None) -> Book:
    if _use_database(db):
        book = db_repository.get_book(db, book_id)
        if book is not None:
            return book
        raise not_found("book", book_id)

    for book in BOOKS:
        if book.id == book_id:
            return book
    raise not_found("book", book_id)


def list_books(city_id: str | None = None, db: Session | None = None) -> list[Book]:
    if _use_database(db):
        if city_id is not None and db_repository.get_destination(db, city_id) is None:
            raise not_found("destination", city_id)
        return db_repository.list_books(db, city_id=city_id)

    if city_id is None:
        return BOOKS

    get_destination(city_id, db=db)
    return [book for book in BOOKS if city_id in book.destinationIds]


def list_itineraries(
    city_id: str | None = None,
    book_id: str | None = None,
    transportation_mode: TransportationMode | None = None,
    db: Session | None = None,
) -> list[Itinerary]:
    if _use_database(db):
        if city_id is not None and db_repository.get_destination(db, city_id) is None:
            raise not_found("destination", city_id)
        if book_id is not None and db_repository.get_book(db, book_id) is None:
            raise not_found("book", book_id)
        return db_repository.list_itineraries(
            db,
            city_id=city_id,
            book_id=book_id,
            transportation_mode=transportation_mode,
        )

    if city_id is not None:
        get_destination(city_id, db=db)

    if book_id is not None:
        get_book(book_id, db=db)

    itineraries = [item for item in ITINERARIES if _is_public_repository_itinerary(item)]

    if city_id is not None:
        itineraries = [item for item in itineraries if item.destinationId == city_id]

    if book_id is not None:
        itineraries = [item for item in itineraries if item.bookId == book_id]

    if transportation_mode is not None:
        itineraries = [
            item for item in itineraries if item.transportationMode == transportation_mode
        ]

    return itineraries


def get_itinerary(
    itinerary_id: str,
    db: Session | None = None,
    current_user: CurrentUser | None = None,
) -> Itinerary:
    if _use_database(db):
        itinerary = db_repository.get_accessible_itinerary(
            db,
            itinerary_id,
            current_user=current_user,
        )
        if itinerary is not None:
            return itinerary
        raise not_found("itinerary", itinerary_id)

    for itinerary in ITINERARIES:
        if itinerary.id == itinerary_id and db_repository.itinerary_is_accessible(
            itinerary,
            current_user=current_user,
        ):
            return itinerary
    raise not_found("itinerary", itinerary_id)


def generate_itinerary(
    request: ItineraryGenerationRequest,
    db: Session | None = None,
    user_id: str | None = None,
    anonymous_session_key: str | None = "anonymous",
) -> ItineraryGenerationResponse:
    usage_guard = get_usage_guard()
    usage_guard.guard_itinerary_request_bounds(duration_days=request.durationDays)
    destination = get_destination(request.destinationId, db=db)
    book = get_book(request.bookId, db=db)

    if request.destinationId not in book.destinationIds:
        raise validation_error(
            f"Book '{request.bookId}' is not available for destination '{request.destinationId}'"
        )
    usage_guard.guard_itinerary_generation(
        user_id=user_id,
        anonymous_session_key=anonymous_session_key,
    )

    exact_match = _find_exact_itinerary(request, db=db)
    if exact_match is not None:
        itinerary = exact_match.model_copy(
            update={
                "generatedFrom": "exact_match",
                "sourceType": "exact_match",
                "sourceItineraryId": exact_match.id,
                "adaptationNotes": [],
            },
            deep=True,
        )
        return ItineraryGenerationResponse(
            itinerary=itinerary,
            matchedExisting=True,
            sourceItineraryId=itinerary.sourceItineraryId,
            message="Returned an exact mock public itinerary match.",
        )

    partial_match = _find_partial_itinerary(request, db=db)
    if partial_match is not None:
        with live_llm_request_scope():
            itinerary = _adapt_itinerary(partial_match, request)
            itinerary = enrich_itinerary_routes(itinerary)
            _ensure_ai_approved(itinerary)
        _save_itinerary_once(itinerary, db=db)
        return ItineraryGenerationResponse(
            itinerary=itinerary,
            matchedExisting=True,
            sourceItineraryId=partial_match.id,
            message="Adapted a partial mock public itinerary match.",
        )

    candidate_pois = _pois_for(destination.id, book.id, db=db)
    if not candidate_pois:
        raise not_found_detail(
            f"No mock POIs are available for book '{book.id}' in destination '{destination.id}'"
        )

    ai_pipeline = get_ai_pipeline()
    with live_llm_request_scope():
        itinerary = ai_pipeline.generate_candidate_itinerary(
            destination=destination,
            book=book,
            pois=candidate_pois,
            request=request,
        )
        itinerary = enrich_itinerary_routes(itinerary)
        _ensure_ai_approved(itinerary)
    _save_itinerary_once(itinerary, db=db)

    return ItineraryGenerationResponse(
        itinerary=itinerary,
        matchedExisting=False,
        message="Generated a deterministic mock itinerary from local POI data.",
    )


def adapt_itinerary(
    request: ItineraryAdaptationRequest,
    db: Session | None = None,
) -> ItineraryGenerationResponse:
    get_usage_guard().guard_itinerary_request_bounds(duration_days=request.durationDays)
    source = get_itinerary(request.sourceItineraryId, db=db)
    generation_request = ItineraryGenerationRequest(
        destinationId=source.destinationId,
        bookId=source.bookId,
        durationDays=request.durationDays,
        transportationMode=request.transportationMode,
    )
    with live_llm_request_scope():
        itinerary = _adapt_itinerary(source, generation_request)
        itinerary = enrich_itinerary_routes(itinerary)
        _ensure_ai_approved(itinerary)
    _save_itinerary_once(itinerary, db=db)

    return ItineraryGenerationResponse(
        itinerary=itinerary,
        matchedExisting=True,
        sourceItineraryId=source.id,
        message="Adapted the requested mock public itinerary.",
    )


def _find_exact_itinerary(
    request: ItineraryGenerationRequest,
    db: Session | None = None,
) -> Itinerary | None:
    if _use_database(db):
        return db_repository.find_exact_itinerary(
            db,
            city_id=request.destinationId,
            book_id=request.bookId,
            duration_days=request.durationDays,
            transportation_mode=request.transportationMode,
        )

    for itinerary in ITINERARIES:
        if (
            itinerary.destinationId == request.destinationId
            and itinerary.bookId == request.bookId
            and itinerary.durationDays == request.durationDays
            and itinerary.transportationMode == request.transportationMode
            and _is_public_repository_itinerary(itinerary)
        ):
            return itinerary
    return None


def _find_partial_itinerary(
    request: ItineraryGenerationRequest,
    db: Session | None = None,
) -> Itinerary | None:
    if _use_database(db):
        return db_repository.find_partial_itinerary(
            db,
            city_id=request.destinationId,
            book_id=request.bookId,
        )

    for itinerary in ITINERARIES:
        if (
            itinerary.destinationId == request.destinationId
            and itinerary.bookId == request.bookId
            and _is_public_repository_itinerary(itinerary)
        ):
            return itinerary
    return None


def _pois_for(destination_id: str, book_id: str, db: Session | None = None) -> list[POI]:
    if _use_database(db):
        return db_repository.list_pois_for_book(db, destination_id=destination_id, book_id=book_id)

    return [
        poi
        for poi in POIS
        if poi.destinationId == destination_id and book_id in poi.bookIds
    ]


def _adapt_itinerary(
    source: Itinerary,
    request: ItineraryGenerationRequest,
) -> Itinerary:
    return get_ai_pipeline().adapt_candidate_itinerary(source, request)


def _save_itinerary_once(itinerary: Itinerary, db: Session | None = None) -> None:
    for index, existing in enumerate(ITINERARIES):
        if existing.id == itinerary.id:
            ITINERARIES[index] = itinerary
            if _use_database(db):
                db_repository.save_itinerary(db, itinerary)
            return
    ITINERARIES.append(itinerary)
    if _use_database(db):
        db_repository.save_itinerary(db, itinerary)


def _ensure_ai_approved(itinerary: Itinerary) -> None:
    result = get_ai_pipeline().validate_itinerary(itinerary)
    if result.approved:
        return

    raise mock_judge_rejected(
        result.reasons,
        warnings=result.warnings,
        confidence_score=result.confidence_score,
        required_fixes=result.required_fixes,
    )


def _is_public_repository_itinerary(itinerary: Itinerary) -> bool:
    return itinerary.isPublic and itinerary.visibility == "public"
