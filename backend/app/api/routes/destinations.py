from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.domain import Destination, DiscoverySearchResponse
from app.services.capability_policy import require_external_discovery_capability
from app.services.discovery_service import search_destinations
from app.services.mock_repository import list_destinations


router = APIRouter(tags=["destinations"])


@router.get("/api/destinations", response_model=list[Destination])
def get_destinations(q: str = "", db: Session = Depends(get_db)) -> list[Destination]:
    return list_destinations(db=db, query=q)


@router.get(
    "/api/discovery/destinations",
    response_model=DiscoverySearchResponse,
    dependencies=[Depends(require_external_discovery_capability)],
)
def get_destination_discovery(q: str, db: Session = Depends(get_db)) -> DiscoverySearchResponse:
    results, external_used = search_destinations(q, db=db, include_external=True)
    return DiscoverySearchResponse(
        results=results,
        repositoryOnly=not external_used,
        externalDiscoveryUsed=external_used,
    )
