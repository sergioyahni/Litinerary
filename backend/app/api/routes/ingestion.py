from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.guards import require_admin_routes
from app.schemas.ingestion import (
    BookIngestionJob,
    BookIngestionJobCreate,
    CandidatePromotionResponse,
)
from app.services.ingestion_service import ingestion_service


router = APIRouter(
    prefix="/api/admin/ingestion",
    tags=["admin", "development", "book-ingestion"],
    dependencies=[Depends(require_admin_routes)],
)


@router.post("/jobs", response_model=BookIngestionJob, status_code=201)
def post_ingestion_job(
    request: BookIngestionJobCreate,
    db: Session = Depends(get_db),
) -> BookIngestionJob:
    """Development-only safe-source ingestion job creation."""
    return ingestion_service.create_job(db, request)


@router.get("/jobs", response_model=list[BookIngestionJob])
def get_ingestion_jobs(db: Session = Depends(get_db)) -> list[BookIngestionJob]:
    """Development-only ingestion job listing."""
    return ingestion_service.list_jobs(db)


@router.get("/jobs/{job_id}", response_model=BookIngestionJob)
def get_ingestion_job(
    job_id: str,
    db: Session = Depends(get_db),
) -> BookIngestionJob:
    """Development-only ingestion job detail."""
    return ingestion_service.get_job(db, job_id)


@router.post("/jobs/{job_id}/run", response_model=BookIngestionJob)
def post_run_ingestion_job(
    job_id: str,
    db: Session = Depends(get_db),
) -> BookIngestionJob:
    """Development-only deterministic mock ingestion processing."""
    return ingestion_service.run_job(db, job_id)


@router.post("/candidates/{candidate_id}/promote", response_model=CandidatePromotionResponse)
def post_promote_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
) -> CandidatePromotionResponse:
    """Development-only promotion of a mock location candidate into an unverified POI."""
    return ingestion_service.promote_candidate(db, candidate_id)
