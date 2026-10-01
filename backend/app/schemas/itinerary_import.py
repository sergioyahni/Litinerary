from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.domain import TransportationMode


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
    records: list[ItineraryImportRecordV1] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def source_identities_are_unique(self) -> Self:
        identities = [record.sourceIdentity for record in self.records]
        if len(identities) != len(set(identities)):
            raise ValueError("records must use unique sourceIdentity values within a batch.")
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
