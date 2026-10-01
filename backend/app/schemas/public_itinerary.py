from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.domain import (
    GeneratedFrom,
    Itinerary,
    ItinerarySourceType,
    ItineraryVisibility,
    TransportationMode,
    VerificationStatus,
)


INTERNAL_ITINERARY_FIELDS = {
    "ownerUserId",
    "createdByMode",
    "createdByUserId",
    "subscriberOnly",
    "providerRequestId",
    "generatedByService",
}

INTERNAL_METADATA_KEYS = {
    "artifactHash",
    "batchSource",
    "contractVersion",
    "importBatchIdentity",
    "importContractVersion",
    "importJobId",
    "initiatedByUserId",
    "manualReviewStatus",
    "providerRequestId",
    "reviewedByUserId",
    "sourceAttribution",
    "sourceContentHash",
    "stableSourceIdentity",
}


class PublicPOI(BaseModel):
    """Public place data without provider correlation or manual-review audit state."""

    model_config = ConfigDict(extra="forbid")

    id: str
    destinationId: str
    bookIds: list[str]
    name: str
    description: str
    latitude: float
    longitude: float
    address: str | None = None
    estimatedDurationMinutes: int
    ticketingNote: str | None = None
    literaryRelevance: str
    verificationStatus: VerificationStatus
    verificationProvider: str | None = None
    providerVersion: str | None = None
    verificationConfidence: float | None = None
    verifiedName: str | None = None
    verifiedAddress: str | None = None
    verifiedLatitude: float | None = None
    verifiedLongitude: float | None = None
    openingHoursNote: str | None = None
    ticketingUrl: str | None = None
    verificationNotes: list[str] = Field(default_factory=list)
    lastVerifiedAt: str | None = None
    provenanceMetadata: dict[str, Any] = Field(default_factory=dict)


class PublicItineraryStop(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    poi: PublicPOI
    order: int = Field(ge=1)
    title: str
    narrativeNote: str
    logisticsNote: str | None = None
    estimatedStartTime: str | None = None
    estimatedEndTime: str | None = None


class PublicItineraryDay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    dayNumber: int = Field(ge=1)
    title: str
    summary: str
    stops: list[PublicItineraryStop]
    estimatedDistanceKm: float | None = None
    estimatedDurationHours: float | None = None
    routeGeometry: list[list[float]] = Field(default_factory=list)
    routingProviderMetadata: dict[str, Any] | None = None
    routingWarnings: list[str] = Field(default_factory=list)


class PublicItinerary(BaseModel):
    """Product-facing itinerary DTO without ownership or import-audit metadata."""

    model_config = ConfigDict(extra="forbid")

    id: str
    destinationId: str
    bookId: str
    title: str
    summary: str
    durationDays: int = Field(ge=1, le=7)
    transportationMode: TransportationMode
    days: list[PublicItineraryDay]
    isPublic: bool
    visibility: ItineraryVisibility = "public"
    generatedFrom: GeneratedFrom
    sourceType: ItinerarySourceType | None = None
    sourceItineraryId: str | None = None
    adaptationNotes: list[str] = Field(default_factory=list)
    createdAt: str
    updatedAt: str | None = None
    providerName: str | None = None
    providerType: str | None = None
    providerVersion: str | None = None
    confidenceScore: float | None = None
    provenanceMetadata: dict[str, Any] = Field(default_factory=dict)
    bookTitle: str | None = None
    bookAuthor: str | None = None
    bookDescription: str | None = None
    bookPublicationYear: int | None = None
    bookPublicDomain: bool | None = None
    bookThemes: list[str] = Field(default_factory=list)
    bookCoverUrl: str | None = None
    bookSourceType: str | None = None
    bookProviderId: str | None = None
    bookProvenanceMetadata: dict[str, Any] = Field(default_factory=dict)
    destinationName: str | None = None
    destinationCountry: str | None = None
    destinationRegion: str | None = None
    destinationDescription: str | None = None
    destinationLatitude: float | None = None
    destinationLongitude: float | None = None
    destinationImageUrl: str | None = None
    destinationSourceType: str | None = None
    destinationProviderId: str | None = None
    destinationProvenanceMetadata: dict[str, Any] = Field(default_factory=dict)


def project_public_itinerary(itinerary: Itinerary) -> PublicItinerary:
    payload = itinerary.model_dump(mode="python", exclude=INTERNAL_ITINERARY_FIELDS)
    return PublicItinerary.model_validate(_without_internal_metadata(payload))


def _without_internal_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_internal_metadata(item)
            for key, item in value.items()
            if key not in INTERNAL_METADATA_KEYS
        }
    if isinstance(value, list):
        return [_without_internal_metadata(item) for item in value]
    return value
