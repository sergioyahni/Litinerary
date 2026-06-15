from typing import Literal

from pydantic import BaseModel, Field


BookSourceType = Literal[
    "public_domain_text_reference",
    "summary_document",
    "manually_curated_location_list",
    "metadata_only",
]
CopyrightStatus = Literal["public_domain", "copyrighted", "unknown", "metadata_only"]
AllowedProcessingMode = Literal["full_text", "summary_only", "metadata_only", "manual_curation"]
BookIngestionStatus = Literal["pending", "processing", "completed", "failed"]
BookLocationCandidateStatus = Literal["candidate", "approved", "promoted", "rejected"]


class BookSourceCreate(BaseModel):
    sourceType: BookSourceType
    title: str | None = Field(default=None, max_length=255)
    referenceUrl: str | None = Field(default=None, max_length=500)
    metadata: dict = Field(default_factory=dict)
    sourceLicense: str | None = Field(default=None, max_length=120)
    copyrightStatus: CopyrightStatus = "unknown"
    allowedProcessingMode: AllowedProcessingMode = "metadata_only"
    sourceNotes: list[str] = Field(default_factory=list)


class BookIngestionJobCreate(BaseModel):
    bookId: str = Field(min_length=1, max_length=120)
    source: BookSourceCreate


class BookSource(BaseModel):
    id: str
    bookId: str
    sourceType: BookSourceType
    title: str | None = None
    referenceUrl: str | None = None
    metadata: dict
    sourceLicense: str | None = None
    copyrightStatus: CopyrightStatus = "unknown"
    allowedProcessingMode: AllowedProcessingMode = "metadata_only"
    sourceNotes: list[str] = Field(default_factory=list)
    createdAt: str


class BookLocationCandidate(BaseModel):
    id: str
    jobId: str
    bookId: str
    destinationId: str
    name: str
    description: str
    latitude: float
    longitude: float
    literaryRelevance: str
    confidence: float
    status: BookLocationCandidateStatus
    promotedPoiId: str | None = None
    createdAt: str


class BookProcessingArtifact(BaseModel):
    id: str
    jobId: str
    artifactType: str
    payload: dict
    providerName: str | None = None
    providerType: str | None = None
    providerVersion: str | None = None
    providerRequestId: str | None = None
    confidenceScore: float | None = None
    provenanceMetadata: dict = Field(default_factory=dict)
    createdAt: str


class BookIngestionJob(BaseModel):
    id: str
    bookId: str
    source: BookSource
    status: BookIngestionStatus
    extractionNotes: list[str]
    warnings: list[str]
    candidates: list[BookLocationCandidate] = Field(default_factory=list)
    artifacts: list[BookProcessingArtifact] = Field(default_factory=list)
    createdAt: str
    updatedAt: str
    completedAt: str | None = None


class CandidatePromotionResponse(BaseModel):
    candidate: BookLocationCandidate
    poiId: str
