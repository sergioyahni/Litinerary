from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.guards import require_admin_routes, require_admin_user_when_auth_enabled
from app.schemas.domain import POI
from app.schemas.poi_verification import (
    CandidateVerificationResponse,
    POIVerificationResponse,
)
from app.services.poi_verification import (
    list_unverified_poi_schemas,
    mark_poi_reviewed_schema,
    verify_candidate_response,
    verify_poi_response,
)


router = APIRouter(
    prefix="/api/admin/poi",
    tags=["admin", "development", "poi-verification"],
    dependencies=[Depends(require_admin_routes), Depends(require_admin_user_when_auth_enabled)],
)


@router.post("/verify-candidate/{candidate_id}", response_model=CandidateVerificationResponse)
def post_verify_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
) -> CandidateVerificationResponse:
    """Development-only mock verification for an ingestion location candidate."""
    return verify_candidate_response(db, candidate_id)


@router.post("/verify/{poi_id}", response_model=POIVerificationResponse)
def post_verify_poi(
    poi_id: str,
    db: Session = Depends(get_db),
) -> POIVerificationResponse:
    """Development-only mock verification for a POI."""
    return verify_poi_response(db, poi_id)


@router.get("/unverified", response_model=list[POI])
def get_unverified_pois(db: Session = Depends(get_db)) -> list[POI]:
    """Development-only list of POIs that need verification/review."""
    return list_unverified_poi_schemas(db)


@router.post("/{poi_id}/mark-reviewed", response_model=POI)
def post_mark_poi_reviewed(
    poi_id: str,
    db: Session = Depends(get_db),
) -> POI:
    """Development-only manual review marker."""
    return mark_poi_reviewed_schema(db, poi_id)
