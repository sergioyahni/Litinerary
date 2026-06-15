from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.observability import EventName, log_event
from app.schemas.domain import (
    Itinerary,
    ItineraryAdaptationRequest,
    ItineraryGenerationRequest,
    ItineraryGenerationResponse,
    TransportationMode,
)
from app.schemas.narration import ItineraryNarrationResponse, NarrationRequest
from app.services.mock_repository import (
    adapt_itinerary,
    generate_itinerary,
    get_itinerary,
    list_itineraries,
)
from app.services.narration_service import build_itinerary_narration


router = APIRouter(tags=["itineraries"])


@router.post(
    "/api/itinerary/generate",
    response_model=ItineraryGenerationResponse,
)
def post_generate_itinerary(
    request: ItineraryGenerationRequest,
    db: Session = Depends(get_db),
) -> ItineraryGenerationResponse:
    log_event(
        EventName.ITINERARY_GENERATION_REQUESTED,
        category="itinerary",
        destination_id=request.destinationId,
        book_id=request.bookId,
        duration_days=request.durationDays,
        transportation_mode=request.transportationMode,
    )
    try:
        response = generate_itinerary(request, db=db)
    except Exception as exc:
        log_event(
            EventName.ITINERARY_GENERATION_FAILED,
            category="itinerary",
            destination_id=request.destinationId,
            book_id=request.bookId,
            error_type=exc.__class__.__name__,
        )
        raise
    log_event(
        EventName.ITINERARY_GENERATION_SUCCEEDED,
        category="itinerary",
        itinerary_id=response.itinerary.id,
        matched_existing=response.matchedExisting,
        source_itinerary_id=response.sourceItineraryId,
    )
    return response


@router.post(
    "/api/itineraries/adapt",
    response_model=ItineraryGenerationResponse,
)
def post_adapt_itinerary(
    request: ItineraryAdaptationRequest,
    db: Session = Depends(get_db),
) -> ItineraryGenerationResponse:
    return adapt_itinerary(request, db=db)


@router.get("/api/itineraries", response_model=list[Itinerary])
def get_itineraries(
    city_id: str | None = None,
    book_id: str | None = None,
    transportation_mode: TransportationMode | None = None,
    db: Session = Depends(get_db),
) -> list[Itinerary]:
    return list_itineraries(
        city_id=city_id,
        book_id=book_id,
        transportation_mode=transportation_mode,
        db=db,
    )


@router.get("/api/itineraries/{itinerary_id}", response_model=Itinerary)
def get_itinerary_by_id(
    itinerary_id: str,
    db: Session = Depends(get_db),
) -> Itinerary:
    return get_itinerary(itinerary_id, db=db)


@router.post(
    "/api/itineraries/{itinerary_id}/narration",
    response_model=ItineraryNarrationResponse,
)
def post_itinerary_narration(
    itinerary_id: str,
    request: NarrationRequest,
    db: Session = Depends(get_db),
) -> ItineraryNarrationResponse:
    itinerary = get_itinerary(itinerary_id, db=db)
    return build_itinerary_narration(itinerary, request)


@router.get(
    "/api/itineraries/{itinerary_id}/narration",
    response_model=ItineraryNarrationResponse,
)
def get_itinerary_narration(
    itinerary_id: str,
    db: Session = Depends(get_db),
) -> ItineraryNarrationResponse:
    itinerary = get_itinerary(itinerary_id, db=db)
    return build_itinerary_narration(itinerary)
