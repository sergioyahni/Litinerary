from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.guards import (
    require_admin_routes,
    require_admin_user_when_auth_enabled,
    require_destructive_development_action,
)
from app.schemas.seed_admin import SeedDataPayload, SeedOperationResult, SeedValidationReport
from app.services.seed_manager import (
    export_seed_data,
    import_seed_data,
    reset_dev_data,
    validate_current_seed_data,
)


router = APIRouter(
    prefix="/api/admin/seed",
    tags=["admin", "development", "seed-data"],
    dependencies=[Depends(require_admin_routes), Depends(require_admin_user_when_auth_enabled)],
)


@router.post(
    "/reset",
    response_model=SeedOperationResult,
    dependencies=[Depends(require_destructive_development_action)],
)
def post_reset_seed_data(db: Session = Depends(get_db)) -> SeedOperationResult:
    """Development-only destructive reset of local data followed by bundled reseed."""
    return reset_dev_data(db)


@router.get("/export", response_model=SeedDataPayload)
def get_export_seed_data(db: Session = Depends(get_db)) -> SeedDataPayload:
    """Development-only export of current seed-domain data."""
    return export_seed_data(db)


@router.post(
    "/import",
    response_model=SeedOperationResult,
    dependencies=[Depends(require_destructive_development_action)],
)
def post_import_seed_data(
    payload: SeedDataPayload,
    db: Session = Depends(get_db),
) -> SeedOperationResult:
    """Development-only destructive replacement of seed-domain data from JSON."""
    return import_seed_data(db, payload)


@router.get("/validate", response_model=SeedValidationReport)
def get_validate_seed_data(db: Session = Depends(get_db)) -> SeedValidationReport:
    """Development-only seed integrity validation."""
    return validate_current_seed_data(db)
