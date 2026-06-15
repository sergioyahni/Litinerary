from functools import lru_cache

from app.core.config import get_settings
from app.core.observability import record_provider_selection
from app.core.provider_guards import require_external_call_allowed
from app.data.mock_data import MOCK_CREATED_AT
from app.schemas.domain import (
    Book,
    Destination,
    Itinerary,
    ItineraryDay,
    ItineraryGenerationRequest,
    ItineraryStop,
    POI,
    TransportationMode,
)
from app.schemas.users import UserReview
from app.services.ai_types import (
    BookIngestionResult,
    JudgeValidationResult,
    LocationExtractionResult,
    POIExtractionResult,
    POIVerificationCandidate,
    ReviewFeedbackResult,
    SUPPORTED_TRANSPORTATION_MODES,
)
from app.services.provider_contracts import ProviderMetadata, ProviderType


MOCK_LLM_METADATA = ProviderMetadata.mock(
    provider_name="mock_ai",
    provider_type=ProviderType.LLM,
    model_name="local-deterministic-mock",
    confidence_score=1.0,
    warnings=["No external LLM call was made."],
)


class MockBookIngestionService:
    def ingest_book(self, book: Book) -> BookIngestionResult:
        return BookIngestionResult(
            book_id=book.id,
            source_kind="mock_summary",
            source_note=(
                "Uses catalog summaries and mock source material only; no copyrighted "
                "full text is ingested."
            ),
            safe_summary=book.description,
            metadata=MOCK_LLM_METADATA,
        )


class MockSummaryLocationExtractionService:
    def extract_summary_and_locations(
        self,
        book: Book,
        source: BookIngestionResult,
    ) -> LocationExtractionResult:
        return LocationExtractionResult(
            book_id=book.id,
            summary=source.safe_summary,
            locations=[destination_id for destination_id in book.destinationIds],
            source_note=source.source_note,
            metadata=MOCK_LLM_METADATA,
        )


class MockPOIExtractionService:
    def extract_pois(
        self,
        book: Book,
        destination: Destination,
        locations: LocationExtractionResult,
        available_pois: list[POI],
    ) -> POIExtractionResult:
        _ = locations
        return POIExtractionResult(
            book_id=book.id,
            destination_id=destination.id,
            poi_names=sorted(poi.name for poi in available_pois),
            metadata=MOCK_LLM_METADATA,
        )


class MockPOIVerificationPreparationService:
    def prepare_verification(self, pois: list[POI]) -> list[POIVerificationCandidate]:
        return [
            POIVerificationCandidate(
                poi_id=poi.id,
                name=poi.name,
                destination_id=poi.destinationId,
                query=f"{poi.name} {poi.address or poi.destinationId}".strip(),
            )
            for poi in sorted(pois, key=lambda item: item.id)
        ]


class MockItineraryGenerationService:
    def generate_candidate_itinerary(
        self,
        destination: Destination,
        book: Book,
        pois: list[POI],
        request: ItineraryGenerationRequest,
    ) -> Itinerary:
        day_count = min(request.durationDays, max(1, len(pois)))
        days: list[ItineraryDay] = []

        for day_index in range(day_count):
            day_pois = pois[day_index::day_count]
            stops = [
                ItineraryStop(
                    id=f"stop-{poi.id}",
                    poi=poi,
                    order=stop_index + 1,
                    title=poi.name,
                    narrativeNote=poi.literaryRelevance,
                    logisticsNote=logistics_note(request.transportationMode),
                )
                for stop_index, poi in enumerate(day_pois)
            ]
            total_minutes = sum(stop.poi.estimatedDurationMinutes for stop in stops)

            days.append(
                ItineraryDay(
                    id=f"day-{destination.id}-{book.id}-{day_index + 1}",
                    dayNumber=day_index + 1,
                    title=f"{book.title}: Day {day_index + 1}",
                    summary=(
                        f"A mock {request.transportationMode.replace('_', ' ')} "
                        f"route through {destination.name}."
                    ),
                    stops=stops,
                    estimatedDurationHours=round(total_minutes / 60, 1),
                )
            )

        return Itinerary(
            id=(
                f"it-{destination.id}-{book.id}-{request.durationDays}-"
                f"{request.transportationMode}-generated"
            ),
            destinationId=destination.id,
            bookId=book.id,
            title=f"{book.title} in {destination.name}",
            summary=(
                "A deterministic mock AI pipeline itinerary built from local POI data. "
                "No LLM, vector search, routing API, or ticketing API was used."
            ),
            durationDays=request.durationDays,
            transportationMode=request.transportationMode,
            days=days,
            isPublic=True,
            visibility="public",
            generatedFrom="new_generation",
            sourceType="new_mock_generation",
            createdByMode="anonymous",
            subscriberOnly=False,
            adaptationNotes=[],
            createdAt=MOCK_CREATED_AT,
            providerName=MOCK_LLM_METADATA.provider_name,
            providerType=MOCK_LLM_METADATA.provider_type,
            providerVersion=MOCK_LLM_METADATA.provider_version,
            providerRequestId=MOCK_LLM_METADATA.request_id,
            generatedByService="mock_ai",
            confidenceScore=MOCK_LLM_METADATA.confidence_score,
            provenanceMetadata=MOCK_LLM_METADATA.public_dict(),
        )


class MockItineraryAdaptationService:
    def adapt_candidate_itinerary(
        self,
        source: Itinerary,
        request: ItineraryGenerationRequest,
    ) -> Itinerary:
        source_stops = [
            stop.model_copy(deep=True)
            for day in source.days
            for stop in day.stops
        ]

        day_count = request.durationDays
        distributed_days: list[ItineraryDay] = []
        notes: list[str] = []

        if request.durationDays < source.durationDays:
            notes.append(
                f"Trimmed from {source.durationDays} day(s) to {request.durationDays} day(s)."
            )
        elif request.durationDays > source.durationDays:
            notes.append(
                f"Expanded from {source.durationDays} day(s) to {request.durationDays} day(s) by redistributing available stops."
            )

        if request.transportationMode != source.transportationMode:
            notes.append(
                f"Transportation changed from {source.transportationMode.replace('_', ' ')} to {request.transportationMode.replace('_', ' ')}; routing is mock-adjusted only."
            )

        if not notes:
            notes.append("Adapted from a partial repository match without changing available stops.")

        for day_index in range(day_count):
            day_stops = source_stops[day_index::day_count]
            adapted_stops = [
                stop.model_copy(
                    update={
                        "id": f"stop-{source.id}-adapted-day-{day_index + 1}-{stop_index + 1}",
                        "order": stop_index + 1,
                        "logisticsNote": adapted_logistics_note(
                            request.transportationMode,
                            stop.logisticsNote,
                        ),
                    },
                    deep=True,
                )
                for stop_index, stop in enumerate(day_stops)
            ]
            total_minutes = sum(stop.poi.estimatedDurationMinutes for stop in adapted_stops)

            distributed_days.append(
                ItineraryDay(
                    id=f"day-{source.id}-adapted-{day_index + 1}",
                    dayNumber=day_index + 1,
                    title=f"{source.title}: Adapted Day {day_index + 1}",
                    summary=(
                        "A mock-adapted day based on an existing public Litinerary. "
                        "POIs and literary notes are preserved."
                    ),
                    stops=adapted_stops,
                    estimatedDurationHours=round(total_minutes / 60, 1)
                    if adapted_stops
                    else 0,
                )
            )

        return source.model_copy(
            update={
                "id": (
                    f"it-{request.destinationId}-{request.bookId}-{request.durationDays}-"
                    f"{request.transportationMode}-adapted-from-{source.id}"
                ),
                "summary": (
                    "A mock-adapted public itinerary. Literary relevance, ticketing notes, "
                    "and coordinates are preserved from the source itinerary."
                ),
                "durationDays": request.durationDays,
                "transportationMode": request.transportationMode,
                "days": distributed_days,
                "generatedFrom": "adapted",
                "sourceType": "adapted_match",
                "sourceItineraryId": source.id,
                "visibility": "public",
                "createdByMode": "anonymous",
                "subscriberOnly": False,
                "adaptationNotes": notes,
                "createdAt": MOCK_CREATED_AT,
                "updatedAt": MOCK_CREATED_AT,
                "providerName": MOCK_LLM_METADATA.provider_name,
                "providerType": MOCK_LLM_METADATA.provider_type,
                "providerVersion": MOCK_LLM_METADATA.provider_version,
                "providerRequestId": MOCK_LLM_METADATA.request_id,
                "generatedByService": "mock_ai",
                "confidenceScore": MOCK_LLM_METADATA.confidence_score,
                "provenanceMetadata": MOCK_LLM_METADATA.public_dict(),
            },
            deep=True,
        )


class MockLLMJudgeValidationService:
    def validate_itinerary(self, itinerary: Itinerary) -> JudgeValidationResult:
        reasons: list[str] = []
        warnings: list[str] = []
        if not itinerary.id:
            reasons.append("Itinerary ID is required.")
        if not itinerary.destinationId:
            reasons.append("Destination ID is required.")
        if not itinerary.bookId:
            reasons.append("Book ID is required.")
        if not itinerary.title.strip():
            reasons.append("Title is required.")
        if not itinerary.summary.strip():
            reasons.append("Summary is required.")
        if itinerary.transportationMode not in SUPPORTED_TRANSPORTATION_MODES:
            reasons.append("Transportation mode is not supported.")
        if not itinerary.days:
            reasons.append("At least one itinerary day is required.")
        if len(itinerary.days) > itinerary.durationDays:
            reasons.append("Day count cannot exceed requested duration.")

        for day in itinerary.days:
            if not day.stops:
                reasons.append(f"Day {day.dayNumber} has no stops.")
            if len(day.stops) > _max_stops_for_transport(itinerary.transportationMode):
                reasons.append(f"Day {day.dayNumber} has too many stops.")
            if day.stops and day.estimatedDistanceKm is None:
                warnings.append(f"Day {day.dayNumber} is missing route distance metadata.")
            if day.stops and day.estimatedDurationHours is None:
                warnings.append(f"Day {day.dayNumber} is missing route duration metadata.")
            if itinerary.transportationMode == "walking" and (day.estimatedDistanceKm or 0) > 12:
                reasons.append(f"Day {day.dayNumber} walking route distance is not reasonable.")
            orders = [stop.order for stop in day.stops]
            if orders != list(range(1, len(day.stops) + 1)):
                reasons.append(f"Day {day.dayNumber} stop order is malformed.")
            for stop in day.stops:
                if not stop.title.strip() or not stop.narrativeNote.strip():
                    reasons.append(f"Stop {stop.id} is missing required text.")
                if stop.poi.latitude == 0 or stop.poi.longitude == 0:
                    reasons.append(f"Stop {stop.id} has missing coordinates.")
                if stop.poi.verificationStatus == "rejected":
                    reasons.append(
                        f"Stop {stop.id} has unsupported POI verification state "
                        f"'{stop.poi.verificationStatus}'."
                    )
                if stop.poi.verificationStatus in {"mock", "verified"}:
                    warnings.append(
                        f"Stop {stop.id} uses legacy POI verification state "
                        f"'{stop.poi.verificationStatus}'."
                    )
                if (
                    stop.poi.verificationStatus == "needs_review"
                    or (stop.poi.verificationConfidence is not None and stop.poi.verificationConfidence < 0.5)
                ):
                    warnings.append(f"Stop {stop.id} uses a low-confidence or review-needed POI.")
                if (
                    not (stop.poi.verificationNotes or stop.poi.provenanceMetadata)
                    and stop.poi.verificationStatus == "mock"
                ):
                    warnings.append(f"Stop {stop.id} uses legacy mock POI data without provenance.")
                elif not (stop.poi.verificationNotes or stop.poi.provenanceMetadata):
                    reasons.append(f"Stop {stop.id} is missing grounding provenance.")
                if stop.poi.provenanceMetadata.get("copyrightStatus") == "copyrighted_full_text":
                    reasons.append(f"Stop {stop.id} uses restricted source licensing metadata.")

        return JudgeValidationResult(
            approved=not reasons,
            reasons=reasons,
            warnings=warnings,
            confidence_score=0.95 if not reasons else 0.2,
            required_fixes=_required_fixes(reasons),
            metadata=MOCK_LLM_METADATA,
        )


class MockReviewFeedbackProcessingService:
    def process_review_feedback(self, review: UserReview) -> ReviewFeedbackResult:
        rating = review.rating or 0
        sentiment = "positive" if rating >= 4 else "negative" if rating <= 2 else "neutral"
        signals = []
        comment = (review.comment or "").lower()
        for word in ("slow", "crowded", "long", "short", "great", "confusing"):
            if word in comment:
                signals.append(word)
        if not signals and review.comment:
            signals.append("general_comment")

        return ReviewFeedbackResult(
            review_id=review.id,
            sentiment=sentiment,
            improvement_signals=signals,
            metadata=MOCK_LLM_METADATA,
        )


class MockAIServicePipeline:
    def __init__(self) -> None:
        self.book_ingestion = MockBookIngestionService()
        self.summary_location_extraction = MockSummaryLocationExtractionService()
        self.poi_extraction = MockPOIExtractionService()
        self.poi_verification_preparation = MockPOIVerificationPreparationService()
        self.itinerary_generation = MockItineraryGenerationService()
        self.itinerary_adaptation = MockItineraryAdaptationService()
        self.judge = MockLLMJudgeValidationService()
        self.review_feedback_processing = MockReviewFeedbackProcessingService()

    def generate_candidate_itinerary(
        self,
        destination: Destination,
        book: Book,
        pois: list[POI],
        request: ItineraryGenerationRequest,
    ) -> Itinerary:
        source = self.book_ingestion.ingest_book(book)
        locations = self.summary_location_extraction.extract_summary_and_locations(book, source)
        self.poi_extraction.extract_pois(book, destination, locations, pois)
        self.poi_verification_preparation.prepare_verification(pois)
        return self.itinerary_generation.generate_candidate_itinerary(
            destination=destination,
            book=book,
            pois=pois,
            request=request,
        )

    def adapt_candidate_itinerary(
        self,
        source: Itinerary,
        request: ItineraryGenerationRequest,
    ) -> Itinerary:
        return self.itinerary_adaptation.adapt_candidate_itinerary(source, request)

    def validate_itinerary(self, itinerary: Itinerary) -> JudgeValidationResult:
        return self.judge.validate_itinerary(itinerary)

    def process_review_feedback(self, review: UserReview) -> ReviewFeedbackResult:
        return self.review_feedback_processing.process_review_feedback(review)


@lru_cache
def get_ai_pipeline() -> MockAIServicePipeline:
    settings = get_settings()
    if settings.ai_provider == "fake" and not settings.enable_mock_services:
        raise RuntimeError(
            "Mock AI services are disabled in this environment. "
            "Set ENABLE_MOCK_SERVICES=true only for intentional local/test use."
        )
    if settings.ai_provider != "fake" and not settings.enable_real_llm:
        raise RuntimeError(
            f"Real LLM provider '{settings.ai_provider}' is disabled by ENABLE_REAL_LLM."
        )
    if settings.ai_provider == "openai_compatible":
        record_provider_selection(
            provider_type=ProviderType.LLM.value,
            provider_name="openai_compatible",
            mode="real",
        )
        validate_llm_startup(settings)
        from app.services.openai_compatible_llm_adapter import (
            OpenAICompatibleAIPipeline,
            OpenAICompatibleLLMSettings,
        )

        return OpenAICompatibleAIPipeline(
            OpenAICompatibleLLMSettings(
                api_key=settings.llm_api_key or "",
                base_url=settings.llm_base_url,
                model_name=settings.llm_model_name,
                timeout_seconds=settings.llm_timeout_seconds,
                max_tokens=settings.llm_max_tokens,
                max_retries=settings.llm_max_retries,
                monthly_budget_usd=settings.llm_monthly_budget_usd,
                allowed_environments=settings.llm_allowed_environments,
            )
        )
    if settings.ai_provider != "fake":
        raise RuntimeError(
            f"AI provider '{settings.ai_provider}' is configured but not implemented."
        )
    record_provider_selection(
        provider_type=ProviderType.LLM.value,
        provider_name="fake",
        mode="mock",
    )
    return MockAIServicePipeline()


def validate_llm_startup(settings=None) -> None:
    resolved = settings or get_settings()
    if not resolved.enable_real_llm:
        return
    if resolved.ai_provider != "openai_compatible":
        raise RuntimeError(
            "Real LLM is enabled but only the OpenAI-compatible adapter boundary is "
            "implemented. Set LLM_PROVIDER=openai_compatible or disable ENABLE_REAL_LLM."
        )
    require_external_call_allowed(
        provider_name="openai_compatible",
        provider_type=ProviderType.LLM,
        feature_flag_name="ENABLE_REAL_LLM",
        feature_enabled=resolved.enable_real_llm,
        required_config={
            "LLM_API_KEY": resolved.llm_api_key,
            "LLM_MODEL_NAME": resolved.llm_model_name,
        },
        allowed_environments=resolved.llm_allowed_environments,
        settings=resolved,
    )
    missing = []
    integration_test_mode = resolved.app_env == "test" and resolved.enable_integration_tests
    if not integration_test_mode and resolved.app_env not in resolved.llm_allowed_environments:
        missing.append("APP_ENV is not listed in LLM_ALLOWED_ENVIRONMENTS")
    if not resolved.llm_api_key:
        missing.append("LLM_API_KEY")
    if not resolved.llm_model_name:
        missing.append("LLM_MODEL_NAME")
    if resolved.llm_timeout_seconds <= 0:
        missing.append("LLM_TIMEOUT_SECONDS must be positive")
    if resolved.llm_max_tokens <= 0:
        missing.append("LLM_MAX_TOKENS must be positive")
    if resolved.llm_max_retries < 0:
        missing.append("LLM_MAX_RETRIES cannot be negative")
    if missing:
        raise RuntimeError(
            "Real OpenAI-compatible LLM provider is enabled but configuration is incomplete: "
            + ", ".join(missing)
        )


def logistics_note(transportation_mode: TransportationMode) -> str:
    notes = {
        "walking": "Planned as a walking-friendly mock route; verify real distances later.",
        "public_transport": "Transit feasibility is not yet routed; confirm options before travel.",
        "car_taxi": "Use car or taxi transfers between stops; live routing is not connected yet.",
    }
    return notes[transportation_mode]


def adapted_logistics_note(
    transportation_mode: TransportationMode,
    original_note: str | None,
) -> str:
    base_note = logistics_note(transportation_mode)
    if original_note:
        return f"{base_note} Original note: {original_note}"
    return base_note


def _max_stops_for_transport(transportation_mode: TransportationMode) -> int:
    if transportation_mode == "walking":
        return 6
    if transportation_mode == "public_transport":
        return 8
    return 10


def _required_fixes(reasons: list[str]) -> list[str]:
    fixes = []
    for reason in reasons:
        if "coordinates" in reason:
            fixes.append("Add verified POI coordinates before presenting the route.")
        elif "verification" in reason or "confidence" in reason:
            fixes.append("Verify or manually review POIs before using them in an itinerary.")
        elif "provenance" in reason:
            fixes.append("Attach grounding provenance or candidate source notes.")
        elif "routing" in reason or "Route" in reason:
            fixes.append("Add route metadata or use mock fallback routing before approval.")
        else:
            fixes.append(reason)
    return fixes
