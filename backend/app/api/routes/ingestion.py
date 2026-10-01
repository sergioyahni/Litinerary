from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, require_admin_user
from app.core.database import get_db
from app.core.guards import require_ingestion_admin_routes
from app.schemas.ingestion import (
    BookIngestionJob,
    BookIngestionJobCreate,
    CandidatePromotionResponse,
)
from app.schemas.itinerary_import import (
    ImportVerificationResponse,
    ItineraryImportBatchV1,
    ItineraryImportJobResponse,
)
from app.services.ingestion_service import ingestion_service
from app.services.itinerary_import_service import itinerary_import_service


router = APIRouter(
    prefix="/api/admin/ingestion",
    tags=["admin", "development", "book-ingestion", "itinerary-import"],
    dependencies=[Depends(require_ingestion_admin_routes), Depends(require_admin_user)],
)


@router.post("/jobs", response_model=BookIngestionJob, status_code=201)
def post_ingestion_job(
    request: BookIngestionJobCreate,
    db: Session = Depends(get_db),
) -> BookIngestionJob:
    """Administrator-only safe-source book-location ingestion job creation."""
    return ingestion_service.create_job(db, request)


@router.get("/jobs", response_model=list[BookIngestionJob])
def get_ingestion_jobs(db: Session = Depends(get_db)) -> list[BookIngestionJob]:
    """Administrator-only book-location ingestion job listing."""
    return ingestion_service.list_jobs(db)


@router.get("/jobs/{job_id}", response_model=BookIngestionJob)
def get_ingestion_job(
    job_id: str,
    db: Session = Depends(get_db),
) -> BookIngestionJob:
    """Administrator-only book-location ingestion job detail."""
    return ingestion_service.get_job(db, job_id)


@router.post("/jobs/{job_id}/run", response_model=BookIngestionJob)
def post_run_ingestion_job(
    job_id: str,
    db: Session = Depends(get_db),
) -> BookIngestionJob:
    """Administrator-only deterministic book-location ingestion processing."""
    return ingestion_service.run_job(db, job_id)


@router.post("/candidates/{candidate_id}/promote", response_model=CandidatePromotionResponse)
def post_promote_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
) -> CandidatePromotionResponse:
    """Administrator-only promotion of a location candidate into an unverified POI."""
    return ingestion_service.promote_candidate(db, candidate_id)


@router.post(
    "/itinerary-imports",
    response_model=ItineraryImportJobResponse,
    status_code=201,
)
def post_itinerary_import_preview(
    request: ItineraryImportBatchV1,
    current_user: CurrentUser = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ItineraryImportJobResponse:
    """Parse, validate, and preview an itinerary-import/v1 artifact without canonical mutation."""
    return itinerary_import_service.preview(db, request, admin=current_user)


@router.get(
    "/itinerary-imports",
    response_model=list[ItineraryImportJobResponse],
)
def get_itinerary_import_jobs(
    db: Session = Depends(get_db),
) -> list[ItineraryImportJobResponse]:
    return itinerary_import_service.list_jobs(db)


@router.get(
    "/itinerary-imports/{job_id}",
    response_model=ItineraryImportJobResponse,
)
def get_itinerary_import_job(
    job_id: str,
    db: Session = Depends(get_db),
) -> ItineraryImportJobResponse:
    return itinerary_import_service.get_job(db, job_id)


@router.post(
    "/itinerary-imports/{job_id}/confirm",
    response_model=ItineraryImportJobResponse,
)
def post_confirm_itinerary_import(
    job_id: str,
    current_user: CurrentUser = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ItineraryImportJobResponse:
    """Persist a previously previewed artifact as non-public canonical itineraries."""
    return itinerary_import_service.confirm(db, job_id, admin=current_user)


@router.get(
    "/itinerary-imports/{job_id}/verify",
    response_model=ImportVerificationResponse,
)
def get_verify_itinerary_import(
    job_id: str,
    db: Session = Depends(get_db),
) -> ImportVerificationResponse:
    return itinerary_import_service.verify(db, job_id)


@router.post(
    "/itinerary-imports/{job_id}/publish",
    response_model=ItineraryImportJobResponse,
)
def post_publish_itinerary_import(
    job_id: str,
    current_user: CurrentUser = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ItineraryImportJobResponse:
    """Publish eligible imported records whose contract intent is publish."""
    return itinerary_import_service.publish(db, job_id, admin=current_user)
