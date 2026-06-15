from typing import Literal

from pydantic import BaseModel, Field


TransportationMode = Literal["walking", "public_transport", "car_taxi"]
VerificationStatus = Literal[
    "mock",
    "unverified",
    "verified",
    "mock_verified",
    "provider_verified",
    "needs_review",
    "rejected",
]
GeneratedFrom = Literal["mock", "exact_match", "adapted", "new_generation"]
ItinerarySourceType = Literal[
    "exact_match", "adapted_match", "new_mock_generation"
]
ItineraryVisibility = Literal["public", "private", "unlisted"]
ItineraryCreatedByMode = Literal["anonymous", "registered_user", "subscriber", "admin", "seed"]


class Destination(BaseModel):
    id: str
    name: str
    country: str
    region: str | None = None
    description: str
    latitude: float
    longitude: float
    imageUrl: str | None = None
    supported: bool


class AffiliateLink(BaseModel):
    title: str
    sourceUrl: str
    providerName: str | None = None
    providerType: str = "affiliate"
    affiliate: bool = False
    lastCheckedAt: str | None = None
    relevanceScore: float | None = None


class Book(BaseModel):
    id: str
    destinationIds: list[str]
    title: str
    author: str
    description: str
    publicationYear: int | None = None
    publicDomain: bool
    themes: list[str]
    coverUrl: str | None = None
    affiliateLinks: list[AffiliateLink] = Field(default_factory=list)


class POI(BaseModel):
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
    providerRequestId: str | None = None
    verificationConfidence: float | None = None
    verifiedName: str | None = None
    verifiedAddress: str | None = None
    verifiedLatitude: float | None = None
    verifiedLongitude: float | None = None
    openingHoursNote: str | None = None
    ticketingUrl: str | None = None
    verificationNotes: list[str] = Field(default_factory=list)
    lastVerifiedAt: str | None = None
    manualReviewStatus: str = "not_reviewed"
    reviewedByUserId: str | None = None
    provenanceMetadata: dict = Field(default_factory=dict)


class ItineraryStop(BaseModel):
    id: str
    poi: POI
    order: int = Field(ge=1)
    title: str
    narrativeNote: str
    logisticsNote: str | None = None
    estimatedStartTime: str | None = None
    estimatedEndTime: str | None = None


class ItineraryDay(BaseModel):
    id: str
    dayNumber: int = Field(ge=1)
    title: str
    summary: str
    stops: list[ItineraryStop]
    estimatedDistanceKm: float | None = None
    estimatedDurationHours: float | None = None
    routeGeometry: list[list[float]] = Field(default_factory=list)
    routingProviderMetadata: dict | None = None
    routingWarnings: list[str] = Field(default_factory=list)


class Itinerary(BaseModel):
    id: str
    destinationId: str
    bookId: str
    title: str
    summary: str
    durationDays: int = Field(ge=1, le=7)
    transportationMode: TransportationMode
    days: list[ItineraryDay]
    isPublic: bool
    ownerUserId: str | None = None
    visibility: ItineraryVisibility = "public"
    generatedFrom: GeneratedFrom
    sourceType: ItinerarySourceType | None = None
    sourceItineraryId: str | None = None
    createdByMode: ItineraryCreatedByMode = "anonymous"
    createdByUserId: str | None = None
    subscriberOnly: bool = False
    adaptationNotes: list[str] = Field(default_factory=list)
    createdAt: str
    updatedAt: str | None = None
    providerName: str | None = None
    providerType: str | None = None
    providerVersion: str | None = None
    providerRequestId: str | None = None
    generatedByService: str | None = None
    confidenceScore: float | None = None
    provenanceMetadata: dict = Field(default_factory=dict)


class ItineraryGenerationRequest(BaseModel):
    destinationId: str
    bookId: str
    durationDays: int = Field(ge=1, le=7)
    transportationMode: TransportationMode


class ItineraryGenerationResponse(BaseModel):
    itinerary: Itinerary
    matchedExisting: bool
    sourceItineraryId: str | None = None
    message: str


class ItineraryAdaptationRequest(BaseModel):
    sourceItineraryId: str
    durationDays: int = Field(ge=1, le=7)
    transportationMode: TransportationMode
