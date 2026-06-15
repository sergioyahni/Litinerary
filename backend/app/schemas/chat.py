from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.domain import Itinerary, TransportationMode


ChatMessageRole = Literal["user", "assistant", "system"]
ChatSessionStatus = Literal["active", "archived"]


class ChatSessionCreate(BaseModel):
    title: str | None = None


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ChatItineraryRefinementRequest(BaseModel):
    sourceItineraryId: str
    prompt: str = Field(min_length=1, max_length=4000)
    durationDays: int | None = Field(default=None, ge=1, le=7)
    transportationMode: TransportationMode | None = None


class ChatItineraryReference(BaseModel):
    id: str
    sessionId: str
    itineraryId: str
    sourceItineraryId: str | None = None
    refinementPrompt: str
    createdAt: str
    providerName: str | None = None
    providerType: str | None = None
    providerVersion: str | None = None
    providerRequestId: str | None = None
    confidenceScore: float | None = None
    provenanceMetadata: dict = Field(default_factory=dict)


class ChatMessage(BaseModel):
    id: str
    sessionId: str
    role: ChatMessageRole
    content: str
    createdAt: str
    providerName: str | None = None
    providerType: str | None = None
    providerVersion: str | None = None
    providerRequestId: str | None = None
    provenanceMetadata: dict = Field(default_factory=dict)


class ChatSession(BaseModel):
    id: str
    userId: str
    title: str
    status: ChatSessionStatus
    createdAt: str
    updatedAt: str
    providerName: str | None = None
    providerType: str | None = None
    providerVersion: str | None = None
    providerRequestId: str | None = None
    provenanceMetadata: dict = Field(default_factory=dict)
    messages: list[ChatMessage] = Field(default_factory=list)
    itineraryReferences: list[ChatItineraryReference] = Field(default_factory=list)


class ChatMessageResponse(BaseModel):
    session: ChatSession
    messages: list[ChatMessage]


class ChatItineraryRefinementResponse(BaseModel):
    session: ChatSession
    itinerary: Itinerary
    reference: ChatItineraryReference
    message: ChatMessage
