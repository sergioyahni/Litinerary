from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, require_subscriber_user
from app.core.database import get_db
from app.schemas.chat import (
    ChatItineraryRefinementRequest,
    ChatItineraryRefinementResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSession,
    ChatSessionCreate,
)
from app.services.chat_service import (
    add_chat_message,
    create_chat_session,
    get_chat_session,
    list_chat_sessions,
    refine_itinerary_from_chat,
)


router = APIRouter(
    prefix="/api/subscribers/chat",
    tags=["subscriber-chat"],
)


@router.post("/sessions", response_model=ChatSession, status_code=201)
def post_chat_session(
    request: ChatSessionCreate,
    current_user: CurrentUser = Depends(require_subscriber_user),
    db: Session = Depends(get_db),
) -> ChatSession:
    return create_chat_session(db, current_user, request)


@router.get("/sessions", response_model=list[ChatSession])
def get_chat_sessions(
    current_user: CurrentUser = Depends(require_subscriber_user),
    db: Session = Depends(get_db),
) -> list[ChatSession]:
    return list_chat_sessions(db, current_user)


@router.get("/sessions/{session_id}", response_model=ChatSession)
def get_chat_session_by_id(
    session_id: str,
    current_user: CurrentUser = Depends(require_subscriber_user),
    db: Session = Depends(get_db),
) -> ChatSession:
    return get_chat_session(db, current_user, session_id)


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
def post_chat_message(
    session_id: str,
    request: ChatMessageCreate,
    current_user: CurrentUser = Depends(require_subscriber_user),
    db: Session = Depends(get_db),
) -> ChatMessageResponse:
    return add_chat_message(db, current_user, session_id, request)


@router.post(
    "/sessions/{session_id}/refine-itinerary",
    response_model=ChatItineraryRefinementResponse,
)
def post_chat_itinerary_refinement(
    session_id: str,
    request: ChatItineraryRefinementRequest,
    current_user: CurrentUser = Depends(require_subscriber_user),
    db: Session = Depends(get_db),
) -> ChatItineraryRefinementResponse:
    return refine_itinerary_from_chat(db, current_user, session_id, request)
