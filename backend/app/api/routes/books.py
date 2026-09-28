from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.domain import Book, DiscoverySearchResponse
from app.services.capability_policy import require_external_discovery_capability
from app.services.discovery_service import search_books
from app.services.mock_repository import list_books


router = APIRouter(tags=["books"])


@router.get("/api/books", response_model=list[Book])
def get_books(
    city_id: str | None = None,
    q: str = "",
    db: Session = Depends(get_db),
) -> list[Book]:
    return list_books(city_id=city_id, query=q, db=db)


@router.get(
    "/api/discovery/books",
    response_model=DiscoverySearchResponse,
    dependencies=[Depends(require_external_discovery_capability)],
)
def get_book_discovery(
    q: str,
    city_id: str | None = None,
    db: Session = Depends(get_db),
) -> DiscoverySearchResponse:
    results, external_used = search_books(
        q,
        destination_id=city_id,
        db=db,
        include_external=True,
    )
    return DiscoverySearchResponse(
        results=results,
        repositoryOnly=not external_used,
        externalDiscoveryUsed=external_used,
    )
