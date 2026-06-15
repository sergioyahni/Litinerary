from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.domain import Book
from app.services.mock_repository import list_books


router = APIRouter(prefix="/api/books", tags=["books"])


@router.get("", response_model=list[Book])
def get_books(city_id: str | None = None, db: Session = Depends(get_db)) -> list[Book]:
    return list_books(city_id=city_id, db=db)
