from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.domain import TransportationMode, VerificationStatus


IMPORT_CONTRACT_VERSION = "litinerary-import/v1"


class ImportModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ImportSourceV1(ImportModel):
    name: str = Field(min_length=1, max_length=255)
    attribution: str | None = Field(default=None, max_length=1000)
    metadata: dict = Field(default_factory=dict)


class ImportDestinationV1(ImportModel):
    id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=255)
    country: str = Field(min_length=1, max_length=255)
    region: str | None = Field(default=None, max_length=255)
    description: str = Field(min_length=1)
    latitude: float
    longitude: float
    imageUrl: str | None = Field(default=None, max_length=500)


class ImportPOIV1(ImportModel):
    id: str = Field(min_length=1, max_length=120)
    destinationId: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    latitude: float
    longitude: float
    address: str | None = Field(default=None, max_length=500)
    estimatedDurationMinutes: int = Field(default=45, ge=1)
    ticketingNote: str | None = None
    literaryRelevance: str = Field(min_length=1)
    verificationStatus: VerificationStatus = "unverified"
    verificationProvider: str | None = Field(default=None, max_length=80)
    providerVersion: str | None = Field(default=None, max_length=120)
    providerRequestId: str | None = Field(default=None, max_length=180)
    verificationConfidence: float | None = Field(default=None, ge=0, le=1)
    verifiedName: str | None = Field(default=None, max_length=255)
    verifiedAddress: str | None = Field(default=None, max_length=500)
    verifiedLatitude: float | None = None
    verifiedLongitude: float | None = None
    openingHoursNote: str | None = None
    ticketingUrl: str | None = Field(default=None, max_length=500)
    verificationNotes: list[str] = Field(default_factory=list)
    lastVerifiedAt: str | None = Field(default=None, max_length=80)
    manualReviewStatus: str = Field(default="not_reviewed", max_length=40)
    repositoryBookIds: list[str] = Field(default_factory=list)
    provenanceMetadata: dict = Field(default_factory=dict)


class ImportBookV1(ImportModel):
    semantics: Literal["repository", "external_snapshot"]
    id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    publicationYear: int | None = None
    publicDomain: bool = False
    themes: list[str] = Field(default_factory=list)
    coverUrl: str | None = Field(default=None, max_length=500)
    sourceType: str | None = Field(default=None, max_length=80)
    providerId: str | None = Field(default=None, max_length=180)
    provenanceMetadata: dict = Field(default_factory=dict)


class ImportStopV1(ImportModel):
    poiId: str = Field(min_length=1, max_length=120)
    order: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=255)
    narrativeNote: str = Field(min_length=1)
    logisticsNote: str | None = None
    estimatedStartTime: str | None = Field(default=None, max_length=40)
    estimatedEndTime: str | None = Field(default=None, max_length=40)


class ImportDayV1(ImportModel):
    dayNumber: int = Field(ge=1, le=7)
    title: str = Field(min_length=1, max_length=255)
    summary: str = Field(min_length=1)
    stops: list[ImportStopV1] = Field(min_length=1)
    estimatedDistanceKm: float | None = Field(default=None, ge=0)
    estimatedDurationHours: float | None = Field(default=None, ge=0)


class ImportItineraryV1(ImportModel):
    id: str | None = Field(default=None, min_length=1, max_length=180)
    title: str = Field(min_length=1, max_length=255)
    summary: str = Field(min_length=1)
    durationDays: int = Field(ge=1, le=7)
    transportationMode: TransportationMode
    days: list[ImportDayV1] = Field(min_length=1, max_length=7)


class ItineraryImportRecordV1(ImportModel):
    sourceIdentity: str = Field(min_length=1, max_length=180)
    sourceAttribution: dict = Field(default_factory=dict)
    destination: ImportDestinationV1
    book: ImportBookV1
    itinerary: ImportItineraryV1
    publicationIntent: Literal["draft", "publish"] = "draft"


class ItineraryImportBatchV1(ImportModel):
    version: Literal["litinerary-import/v1"]
    batchIdentity: str = Field(min_length=1, max_length=180)
    source: ImportSourceV1
    pois: list[ImportPOIV1] = Field(default_factory=list, max_length=1000)
    records: list[ItineraryImportRecordV1] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def identities_and_catalog_are_consistent(self) -> Self:
        identities = [record.sourceIdentity for record in self.records]
        if len(identities) != len(set(identities)):
            raise ValueError("records must use unique sourceIdentity values within a batch.")

        poi_ids = [poi.id for poi in self.pois]
        if len(poi_ids) != len(set(poi_ids)):
            raise ValueError("pois must use unique id values within a batch.")

        destinations: dict[str, dict] = {}
        for record in self.records:
            value = record.destination.model_dump(mode="json")
            prior = destinations.setdefault(record.destination.id, value)
            if prior != value:
                raise ValueError(
                    "records using the same destination id must use identical destination snapshots."
                )

        destination_ids = set(destinations)
        for poi in self.pois:
            if poi.destinationId not in destination_ids:
                raise ValueError(
                    f"POI '{poi.id}' references destination '{poi.destinationId}' not used by any record."
                )
            if len(poi.repositoryBookIds) != len(set(poi.repositoryBookIds)):
                raise ValueError(
                    f"POI '{poi.id}' must use unique repositoryBookIds values."
                )
        return self


class ImportRecordPreview(ImportModel):
    sourceIdentity: str
    outcome: Literal["new", "already_imported", "conflict", "invalid"]
    contentHash: str
    projectedItineraryId: str | None = None
    publicationIntent: Literal["draft", "publish"]
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ImportPreviewSummary(ImportModel):
    totalRecords: int
    validRecords: int
    invalidRecords: int
    newRecords: int
    alreadyImportedRecords: int
    conflicts: int
    warnings: int
    projectedMutations: int
    projectedCatalogMutations: int = 0
    publicationIntentCount: int
    records: list[ImportRecordPreview]


class ItineraryImportJobResponse(ImportModel):
    id: str
    batchIdentity: str
    contractVersion: str
    initiatedByUserId: str
    dryRun: bool
    status: str
    artifactHash: str
    preview: ImportPreviewSummary | None = None
    persistedItineraryIds: list[str] = Field(default_factory=list)
    publishedItineraryIds: list[str] = Field(default_factory=list)
    errors: dict = Field(default_factory=dict)
    createdAt: str
    updatedAt: str
    completedAt: str | None = None


class ImportVerificationRecord(ImportModel):
    sourceIdentity: str
    itineraryId: str
    exists: bool
    provenanceMatches: bool
    publicationState: str


class ImportVerificationResponse(ImportModel):
    jobId: str
    verified: bool
    records: list[ImportVerificationRecord]
