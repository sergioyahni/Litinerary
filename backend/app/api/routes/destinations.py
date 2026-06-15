from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.domain import Destination
from app.services.mock_repository import list_destinations


router = APIRouter(prefix="/api/destinations", tags=["destinations"])


@router.get("", response_model=list[Destination])
def get_destinations(db: Session = Depends(get_db)) -> list[Destination]:
    return list_destinations(db=db)
