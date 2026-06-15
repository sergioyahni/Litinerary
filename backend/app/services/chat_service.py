from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import CurrentUser
from app.models import (
    ChatItineraryReferenceModel,
    ChatMessageModel,
    ChatSessionModel,
    UserModel,
)
from app.schemas.chat import (
    ChatItineraryReference,
    ChatItineraryRefinementRequest,
    ChatItineraryRefinementResponse,
    ChatMessage,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSession,
    ChatSessionCreate,
)
from app.schemas.domain import Itinerary, ItineraryGenerationRequest
from app.services import database_repository
from app.services.mock_ai_service import MOCK_LLM_METADATA, get_ai_pipeline
from app.services.mock_repository import get_itinerary
from app.services.provider_contracts import utc_now_iso
from app.services.routing_service import enrich_itinerary_routes
from app.services.usage_policy import get_usage_guard


def create_chat_session(
    db: Session,
    user: CurrentUser,
    request: ChatSessionCreate,
) -> ChatSession:
    _ensure_user(db, user)
    now = utc_now_iso()
    session = ChatSessionModel(
        id=f"chat-{uuid4().hex}",
        user_id=user.id,
        title=request.title or "Literary travel chat",
        status="active",
        created_at=now,
        updated_at=now,
        provider_name=MOCK_LLM_METADATA.provider_name,
        provider_type=MOCK_LLM_METADATA.provider_type,
        provider_version=MOCK_LLM_METADATA.provider_version,
        provider_request_id=MOCK_LLM_METADATA.request_id,
        provenance_metadata=_mock_chat_metadata(),
    )
    welcome = ChatMessageModel(
        id=f"chatmsg-{uuid4().hex}",
        session_id=session.id,
        role="assistant",
        content=(
            "Welcome to subscriber chat. I can refine an existing Litinerary using "
            "mock AI only; no real LLM provider is connected."
        ),
        created_at=now,
        provider_name=MOCK_LLM_METADATA.provider_name,
        provider_type=MOCK_LLM_METADATA.provider_type,
        provider_version=MOCK_LLM_METADATA.provider_version,
        provider_request_id=MOCK_LLM_METADATA.request_id,
        provenance_metadata=_mock_chat_metadata(),
    )
    session.messages.append(welcome)
    db.add(session)
    db.commit()
    db.refresh(session)
    return chat_session_from_model(_load_session(db, session.id, user.id))


def list_chat_sessions(db: Session, user: CurrentUser) -> list[ChatSession]:
    _ensure_user(db, user)
    rows = db.scalars(
        select(ChatSessionModel)
        .where(ChatSessionModel.user_id == user.id)
        .options(*_session_load_options())
        .order_by(ChatSessionModel.updated_at.desc(), ChatSessionModel.created_at.desc())
    ).unique().all()
    return [chat_session_from_model(row) for row in rows]


def get_chat_session(db: Session, user: CurrentUser, session_id: str) -> ChatSession:
    _ensure_user(db, user)
    return chat_session_from_model(_load_session(db, session_id, user.id))


def add_chat_message(
    db: Session,
    user: CurrentUser,
    session_id: str,
    request: ChatMessageCreate,
) -> ChatMessageResponse:
    get_usage_guard().guard_subscriber_chat(user_id=user.id)
    session = _load_session(db, session_id, user.id)
    now = utc_now_iso()
    user_message = ChatMessageModel(
        id=f"chatmsg-{uuid4().hex}",
        session_id=session.id,
        role="user",
        content=request.content.strip(),
        created_at=now,
        provenance_metadata={"source": "subscriber"},
    )
    assistant_message = ChatMessageModel(
        id=f"chatmsg-{uuid4().hex}",
        session_id=session.id,
        role="assistant",
        content=_mock_chat_reply(request.content),
        created_at=utc_now_iso(),
        provider_name=MOCK_LLM_METADATA.provider_name,
        provider_type=MOCK_LLM_METADATA.provider_type,
        provider_version=MOCK_LLM_METADATA.provider_version,
        provider_request_id=MOCK_LLM_METADATA.request_id,
        provenance_metadata=_mock_chat_metadata(),
    )
    session.updated_at = assistant_message.created_at
    session.messages.extend([user_message, assistant_message])
    db.commit()
    refreshed = _load_session(db, session_id, user.id)
    return ChatMessageResponse(
        session=chat_session_from_model(refreshed),
        messages=[
            chat_message_from_model(user_message),
            chat_message_from_model(assistant_message),
        ],
    )


def refine_itinerary_from_chat(
    db: Session,
    user: CurrentUser,
    session_id: str,
    request: ChatItineraryRefinementRequest,
) -> ChatItineraryRefinementResponse:
    get_usage_guard().guard_subscriber_chat(user_id=user.id)
    session = _load_session(db, session_id, user.id)
    source = get_itinerary(request.sourceItineraryId, db=db)
    generation_request = ItineraryGenerationRequest(
        destinationId=source.destinationId,
        bookId=source.bookId,
        durationDays=request.durationDays or source.durationDays,
        transportationMode=request.transportationMode or source.transportationMode,
    )
    itinerary = get_ai_pipeline().adapt_candidate_itinerary(source, generation_request)
    itinerary = enrich_itinerary_routes(itinerary)
    itinerary = _subscriber_itinerary(itinerary, user, session.id, request.prompt)
    _ensure_ai_approved(itinerary)
    database_repository.save_itinerary(db, itinerary)

    now = utc_now_iso()
    reference = ChatItineraryReferenceModel(
        id=f"chatref-{uuid4().hex}",
        session_id=session.id,
        itinerary_id=itinerary.id,
        source_itinerary_id=source.id,
        refinement_prompt=request.prompt.strip(),
        created_at=now,
        provider_name=MOCK_LLM_METADATA.provider_name,
        provider_type=MOCK_LLM_METADATA.provider_type,
        provider_version=MOCK_LLM_METADATA.provider_version,
        provider_request_id=MOCK_LLM_METADATA.request_id,
        confidence_score=MOCK_LLM_METADATA.confidence_score,
        provenance_metadata=_mock_chat_metadata(),
    )
    assistant_message = ChatMessageModel(
        id=f"chatmsg-{uuid4().hex}",
        session_id=session.id,
        role="assistant",
        content=(
            "I created a private mock refinement for subscribers. "
            f"Reference: {itinerary.id}."
        ),
        created_at=now,
        provider_name=MOCK_LLM_METADATA.provider_name,
        provider_type=MOCK_LLM_METADATA.provider_type,
        provider_version=MOCK_LLM_METADATA.provider_version,
        provider_request_id=MOCK_LLM_METADATA.request_id,
        provenance_metadata=_mock_chat_metadata(),
    )
    session.updated_at = now
    session.itinerary_references.append(reference)
    session.messages.append(assistant_message)
    db.commit()
    refreshed = _load_session(db, session.id, user.id)
    return ChatItineraryRefinementResponse(
        session=chat_session_from_model(refreshed),
        itinerary=itinerary,
        reference=chat_itinerary_reference_from_model(reference),
        message=chat_message_from_model(assistant_message),
    )


def chat_session_from_model(row: ChatSessionModel) -> ChatSession:
    return ChatSession(
        id=row.id,
        userId=row.user_id,
        title=row.title,
        status=row.status,
        createdAt=row.created_at,
        updatedAt=row.updated_at,
        providerName=row.provider_name,
        providerType=row.provider_type,
        providerVersion=row.provider_version,
        providerRequestId=row.provider_request_id,
        provenanceMetadata=row.provenance_metadata or {},
        messages=[chat_message_from_model(message) for message in row.messages],
        itineraryReferences=[
            chat_itinerary_reference_from_model(reference)
            for reference in row.itinerary_references
        ],
    )


def chat_message_from_model(row: ChatMessageModel) -> ChatMessage:
    return ChatMessage(
        id=row.id,
        sessionId=row.session_id,
        role=row.role,
        content=row.content,
        createdAt=row.created_at,
        providerName=row.provider_name,
        providerType=row.provider_type,
        providerVersion=row.provider_version,
        providerRequestId=row.provider_request_id,
        provenanceMetadata=row.provenance_metadata or {},
    )


def chat_itinerary_reference_from_model(
    row: ChatItineraryReferenceModel,
) -> ChatItineraryReference:
    return ChatItineraryReference(
        id=row.id,
        sessionId=row.session_id,
        itineraryId=row.itinerary_id,
        sourceItineraryId=row.source_itinerary_id,
        refinementPrompt=row.refinement_prompt,
        createdAt=row.created_at,
        providerName=row.provider_name,
        providerType=row.provider_type,
        providerVersion=row.provider_version,
        providerRequestId=row.provider_request_id,
        confidenceScore=row.confidence_score,
        provenanceMetadata=row.provenance_metadata or {},
    )


def _load_session(db: Session, session_id: str, user_id: str) -> ChatSessionModel:
    row = db.scalars(
        select(ChatSessionModel)
        .where(ChatSessionModel.id == session_id, ChatSessionModel.user_id == user_id)
        .options(*_session_load_options())
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown chat session.")
    return row


def _session_load_options():
    return (
        selectinload(ChatSessionModel.messages),
        selectinload(ChatSessionModel.itinerary_references),
    )


def _ensure_user(db: Session, user: CurrentUser) -> None:
    if db.get(UserModel, user.id) is not None:
        return
    now = utc_now_iso()
    db.add(
        UserModel(
            id=user.id,
            auth_provider=user.auth_provider,
            auth_subject=user.auth_subject,
            role="admin" if user.is_admin else "subscriber" if user.is_subscriber else "user",
            subscription_status=user.subscription_status,
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()


def _subscriber_itinerary(
    itinerary: Itinerary,
    user: CurrentUser,
    session_id: str,
    prompt: str,
) -> Itinerary:
    suffix = uuid4().hex[:10]
    itinerary_id = f"sub-{itinerary.id}-{suffix}"
    return itinerary.model_copy(
        update={
            "id": itinerary_id,
            "title": f"{itinerary.title}: Subscriber Refinement",
            "summary": (
                f"{itinerary.summary} Subscriber chat note: {prompt.strip()} "
                "This was produced by the mock AI pipeline only."
            ),
            "days": [
                day.model_copy(
                    update={
                        "id": f"{itinerary_id}-day-{day.dayNumber}",
                        "stops": [
                            stop.model_copy(
                                update={
                                    "id": (
                                        f"{itinerary_id}-day-{day.dayNumber}-"
                                        f"stop-{stop.order}"
                                    )
                                },
                                deep=True,
                            )
                            for stop in day.stops
                        ],
                    },
                    deep=True,
                )
                for day in itinerary.days
            ],
            "isPublic": False,
            "visibility": "private",
            "ownerUserId": user.id,
            "createdByMode": "subscriber",
            "createdByUserId": user.id,
            "subscriberOnly": True,
            "generatedByService": "mock_ai_subscriber_chat",
            "provenanceMetadata": {
                **itinerary.provenanceMetadata,
                "chatSessionId": session_id,
                "mockOnly": True,
            },
        },
        deep=True,
    )


def _ensure_ai_approved(itinerary: Itinerary) -> None:
    result = get_ai_pipeline().validate_itinerary(itinerary)
    if result.approved:
        return
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "message": "Mock judge rejected the chat refinement.",
            "reasons": result.reasons,
            "warnings": result.warnings,
            "confidenceScore": result.confidence_score,
            "requiredFixes": result.required_fixes,
        },
    )


def _mock_chat_reply(content: str) -> str:
    trimmed = content.strip()
    return (
        "Mock subscriber assistant noted your preference: "
        f"'{trimmed}'. Use refine itinerary to generate a private mock adaptation."
    )


def _mock_chat_metadata() -> dict:
    return {
        **MOCK_LLM_METADATA.public_dict(),
        "mockOnly": True,
        "realLlmConnected": False,
    }
