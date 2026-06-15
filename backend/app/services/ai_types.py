from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from app.schemas.domain import (
    Book,
    Destination,
    Itinerary,
    ItineraryGenerationRequest,
    POI,
    TransportationMode,
)
from app.schemas.users import UserReview
from app.services.provider_contracts import ProviderMetadata


@dataclass(frozen=True)
class BookIngestionResult:
    book_id: str
    source_kind: str
    source_note: str
    safe_summary: str
    metadata: ProviderMetadata | None = None


@dataclass(frozen=True)
class LocationExtractionResult:
    book_id: str
    summary: str
    locations: list[str]
    source_note: str
    metadata: ProviderMetadata | None = None


@dataclass(frozen=True)
class POIExtractionResult:
    book_id: str
    destination_id: str
    poi_names: list[str]
    metadata: ProviderMetadata | None = None


@dataclass(frozen=True)
class POIVerificationCandidate:
    poi_id: str
    name: str
    destination_id: str
    query: str


@dataclass(frozen=True)
class JudgeValidationResult:
    approved: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    confidence_score: float | None = None
    required_fixes: list[str] = field(default_factory=list)
    metadata: ProviderMetadata | None = None


SafeSourceType = Literal[
    "public_domain_text_reference",
    "summary_document",
    "manually_curated_location_list",
    "metadata_only",
]


@dataclass(frozen=True)
class GroundingSource:
    source_id: str
    source_type: SafeSourceType
    title: str | None = None
    reference_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    source_license: str | None = None
    copyright_status: str = "unknown"
    allowed_processing_mode: str = "metadata_only"
    source_notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GroundedLLMRequest:
    task: str
    book: Book | None = None
    destination: Destination | None = None
    sources: list[GroundingSource] = field(default_factory=list)
    pois: list[POI] = field(default_factory=list)
    itinerary: Itinerary | None = None
    itinerary_request: ItineraryGenerationRequest | None = None
    review: UserReview | None = None
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReviewFeedbackResult:
    review_id: str
    sentiment: str
    improvement_signals: list[str]
    metadata: ProviderMetadata | None = None


class BookIngestionService(Protocol):
    def ingest_book(self, book: Book) -> BookIngestionResult:
        """Prepare safe source material without handling copyrighted full text."""


class SummaryLocationExtractionService(Protocol):
    def extract_summary_and_locations(
        self,
        book: Book,
        source: BookIngestionResult,
    ) -> LocationExtractionResult:
        """Extract summary and place mentions from safe source material."""


class POIExtractionService(Protocol):
    def extract_pois(
        self,
        book: Book,
        destination: Destination,
        locations: LocationExtractionResult,
        available_pois: list[POI],
    ) -> POIExtractionResult:
        """Map extracted place mentions to candidate POIs."""


class POIVerificationPreparationService(Protocol):
    def prepare_verification(self, pois: list[POI]) -> list[POIVerificationCandidate]:
        """Prepare provider-neutral POI verification queries without calling an API."""


class ItineraryGenerationService(Protocol):
    def generate_candidate_itinerary(
        self,
        destination: Destination,
        book: Book,
        pois: list[POI],
        request: ItineraryGenerationRequest,
    ) -> Itinerary:
        """Generate a candidate itinerary from local source data."""


class ItineraryAdaptationService(Protocol):
    def adapt_candidate_itinerary(
        self,
        source: Itinerary,
        request: ItineraryGenerationRequest,
    ) -> Itinerary:
        """Adapt an existing itinerary candidate."""


class LLMJudgeValidationService(Protocol):
    def validate_itinerary(self, itinerary: Itinerary) -> JudgeValidationResult:
        """Validate candidate itinerary quality before it is returned."""


class ReviewFeedbackProcessingService(Protocol):
    def process_review_feedback(self, review: UserReview) -> ReviewFeedbackResult:
        """Extract deterministic feedback signals from a user review."""


SUPPORTED_TRANSPORTATION_MODES: set[TransportationMode] = {
    "walking",
    "public_transport",
    "car_taxi",
}
