from pydantic import BaseModel, Field

from app.schemas.domain import POI
from app.schemas.ingestion import BookLocationCandidate


class POIVerificationResultResponse(BaseModel):
    status: str
    provider: str
    confidence: float
    verifiedName: str | None = None
    verifiedAddress: str | None = None
    verifiedLatitude: float | None = None
    verifiedLongitude: float | None = None
    openingHoursNote: str | None = None
    ticketingUrl: str | None = None
    notes: list[str]
    providerVersion: str | None = None
    providerRequestId: str | None = None
    verifiedAt: str | None = None
    warnings: list[str] = Field(default_factory=list)


class CandidateVerificationResponse(BaseModel):
    candidate: BookLocationCandidate
    verification: POIVerificationResultResponse


class POIVerificationResponse(BaseModel):
    poi: POI
    verification: POIVerificationResultResponse
