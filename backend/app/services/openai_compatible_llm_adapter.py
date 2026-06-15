from dataclasses import dataclass
import json
from time import monotonic
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.data.mock_data import MOCK_CREATED_AT
from app.schemas.domain import Book, Destination, Itinerary, ItineraryGenerationRequest, POI
from app.schemas.users import UserReview
from app.services.ai_types import (
    BookIngestionResult,
    GroundedLLMRequest,
    GroundingSource,
    JudgeValidationResult,
    LocationExtractionResult,
    POIExtractionResult,
    POIVerificationCandidate,
    ReviewFeedbackResult,
)
from app.services.llm_grounding import validate_grounded_request
from app.services.provider_contracts import (
    ProviderError,
    ProviderErrorCode,
    ProviderMetadata,
    ProviderType,
    utc_now_iso,
)


class LLMTransport(Protocol):
    def complete_json(self, request: GroundedLLMRequest) -> tuple[dict[str, Any], ProviderMetadata]:
        """Return provider-normalized JSON without exposing raw payloads."""


@dataclass(frozen=True)
class OpenAICompatibleLLMSettings:
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4.1-mini"
    timeout_seconds: float = 20.0
    max_tokens: int = 1200
    max_retries: int = 0
    monthly_budget_usd: float | None = None
    allowed_environments: list[str] | None = None


class OpenAICompatibleTransport:
    provider_name = "openai_compatible"
    provider_version = "chat-completions-v1"

    def __init__(self, settings: OpenAICompatibleLLMSettings) -> None:
        self.settings = settings
        self.base_url = settings.base_url.rstrip("/")

    def complete_json(self, request: GroundedLLMRequest) -> tuple[dict[str, Any], ProviderMetadata]:
        payload = {
            "model": self.settings.model_name,
            "response_format": {"type": "json_object"},
            "max_tokens": self.settings.max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Litinerary's grounded planning adapter. Return only JSON. "
                        "Use only supplied structured grounding context."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(_provider_request_payload(request)),
                },
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        http_request = Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = monotonic()
        try:
            with urlopen(http_request, timeout=self.settings.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
                request_id = response.headers.get("x-request-id")
        except HTTPError as exc:
            if exc.code == 429:
                raise _provider_error(
                    ProviderErrorCode.RATE_LIMITED,
                    "LLM provider rate limit was exceeded.",
                ) from exc
            raise _provider_error(
                ProviderErrorCode.INVALID_RESPONSE,
                f"LLM provider returned HTTP {exc.code}.",
            ) from exc
        except TimeoutError as exc:
            raise _provider_error(ProviderErrorCode.TIMEOUT, "LLM provider request timed out.") from exc
        except URLError as exc:
            raise _provider_error(ProviderErrorCode.UNAVAILABLE, "LLM provider is unavailable.") from exc

        latency_ms = round((monotonic() - started) * 1000)
        try:
            payload = json.loads(response_body)
            content = payload["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise _provider_error(
                ProviderErrorCode.INVALID_RESPONSE,
                "LLM provider returned an invalid JSON response.",
                latency_ms=latency_ms,
            ) from exc

        return parsed, _metadata(
            provider_name=self.provider_name,
            model_name=self.settings.model_name,
            request_id=request_id,
            latency_ms=latency_ms,
            warnings=["LLM response normalized; raw provider payload was not exposed."],
        )


class OpenAICompatibleAIPipeline:
    provider_name = "openai_compatible"

    def __init__(
        self,
        settings: OpenAICompatibleLLMSettings,
        transport: LLMTransport | None = None,
    ) -> None:
        if not settings.api_key:
            raise _provider_error(
                ProviderErrorCode.NOT_CONFIGURED,
                "LLM API key is required when real LLM is enabled.",
            )
        if settings.timeout_seconds <= 0:
            raise _provider_error(ProviderErrorCode.NOT_CONFIGURED, "LLM timeout must be positive.")
        if settings.max_tokens <= 0:
            raise _provider_error(ProviderErrorCode.NOT_CONFIGURED, "LLM max tokens must be positive.")
        if settings.max_retries < 0:
            raise _provider_error(ProviderErrorCode.NOT_CONFIGURED, "LLM max retries cannot be negative.")
        self.settings = settings
        self.transport = transport or OpenAICompatibleTransport(settings)
        self.book_ingestion = self
        self.summary_location_extraction = self
        self.poi_extraction = self
        self.poi_verification_preparation = self
        self.itinerary_generation = self
        self.itinerary_adaptation = self
        self.judge = self
        self.review_feedback_processing = self

    def ingest_book(self, book: Book) -> BookIngestionResult:
        return BookIngestionResult(
            book_id=book.id,
            source_kind="metadata_only",
            source_note="Real LLM ingestion requires explicit GroundingSource records.",
            safe_summary=book.description,
            metadata=self._metadata(
                confidence_score=0.5,
                warnings=["Book metadata only; no provider call was made."],
            ),
        )

    def extract_summary_and_locations(
        self,
        book: Book,
        source: BookIngestionResult,
    ) -> LocationExtractionResult:
        grounded = GroundedLLMRequest(
            task="summary_location_extraction",
            book=book,
            sources=[
                GroundingSource(
                    source_id=f"book-{book.id}-summary",
                    source_type="summary_document",
                    metadata={"summary": source.safe_summary},
                    copyright_status="copyrighted",
                    allowed_processing_mode="summary_only",
                    source_notes=[source.source_note],
                )
            ],
        )
        response, metadata = self._complete(grounded)
        return LocationExtractionResult(
            book_id=book.id,
            summary=str(response.get("summary") or source.safe_summary),
            locations=[str(item) for item in response.get("locations") or []],
            source_note=source.source_note,
            metadata=metadata,
        )

    def extract_pois(
        self,
        book: Book,
        destination: Destination,
        locations: LocationExtractionResult,
        available_pois: list[POI],
    ) -> POIExtractionResult:
        grounded = GroundedLLMRequest(
            task="poi_extraction",
            book=book,
            destination=destination,
            sources=[
                GroundingSource(
                    source_id=f"locations-{book.id}-{destination.id}",
                    source_type="metadata_only",
                    metadata={"locations": locations.locations},
                    copyright_status="metadata_only",
                    allowed_processing_mode="metadata_only",
                    source_notes=[locations.source_note],
                )
            ],
            pois=available_pois,
        )
        response, metadata = self._complete(grounded)
        return POIExtractionResult(
            book_id=book.id,
            destination_id=destination.id,
            poi_names=[str(item) for item in response.get("poi_names") or []],
            metadata=metadata,
        )

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

    def generate_candidate_itinerary(
        self,
        destination: Destination,
        book: Book,
        pois: list[POI],
        request: ItineraryGenerationRequest,
    ) -> Itinerary:
        grounded = GroundedLLMRequest(
            task="itinerary_generation",
            book=book,
            destination=destination,
            pois=pois,
            itinerary_request=request,
            sources=[_book_summary_source(book)],
            constraints={"output_schema": "Itinerary"},
        )
        response, metadata = self._complete(grounded)
        return _itinerary_from_response(response, destination, book, request, pois, metadata)

    def adapt_candidate_itinerary(
        self,
        source: Itinerary,
        request: ItineraryGenerationRequest,
    ) -> Itinerary:
        grounded = GroundedLLMRequest(
            task="itinerary_adaptation",
            itinerary=source,
            pois=[stop.poi for day in source.days for stop in day.stops],
            itinerary_request=request,
            sources=[
                GroundingSource(
                    source_id=f"itinerary-{source.id}",
                    source_type="metadata_only",
                    metadata={"source_itinerary_id": source.id},
                    copyright_status="metadata_only",
                    allowed_processing_mode="metadata_only",
                    source_notes=source.adaptationNotes or ["Existing itinerary metadata."],
                )
            ],
        )
        response, metadata = self._complete(grounded)
        title = str(response.get("title") or source.title)
        summary = str(response.get("summary") or source.summary)
        return source.model_copy(
            update={
                "title": title,
                "summary": summary,
                "durationDays": request.durationDays,
                "transportationMode": request.transportationMode,
                "generatedFrom": "adapted",
                "sourceType": "adapted_match",
                "sourceItineraryId": source.id,
                "providerName": metadata.provider_name,
                "providerType": metadata.provider_type,
                "providerVersion": metadata.provider_version,
                "providerRequestId": metadata.request_id,
                "generatedByService": self.provider_name,
                "confidenceScore": metadata.confidence_score,
                "provenanceMetadata": metadata.public_dict(),
                "updatedAt": MOCK_CREATED_AT,
            },
            deep=True,
        )

    def validate_itinerary(self, itinerary: Itinerary) -> JudgeValidationResult:
        from app.services.mock_ai_service import MockLLMJudgeValidationService

        local = MockLLMJudgeValidationService().validate_itinerary(itinerary)
        if not local.approved:
            return local
        grounded = GroundedLLMRequest(
            task="judge_validation",
            itinerary=itinerary,
            pois=[stop.poi for day in itinerary.days for stop in day.stops],
        )
        response, metadata = self._complete(grounded)
        approved = bool(response.get("approved", local.approved))
        return JudgeValidationResult(
            approved=approved,
            reasons=[str(item) for item in response.get("reasons") or []],
            warnings=[str(item) for item in response.get("warnings") or local.warnings],
            confidence_score=float(response.get("confidence_score") or 0.75),
            required_fixes=[str(item) for item in response.get("required_fixes") or []],
            metadata=metadata,
        )

    def process_review_feedback(self, review: UserReview) -> ReviewFeedbackResult:
        grounded = GroundedLLMRequest(
            task="review_feedback_synthesis",
            review=review,
            constraints={"allowed_outputs": ["positive", "neutral", "negative"]},
        )
        response, metadata = self._complete(grounded)
        return ReviewFeedbackResult(
            review_id=review.id,
            sentiment=str(response.get("sentiment") or "neutral"),
            improvement_signals=[str(item) for item in response.get("improvement_signals") or []],
            metadata=metadata,
        )

    def _complete(self, request: GroundedLLMRequest) -> tuple[dict[str, Any], ProviderMetadata]:
        validate_grounded_request(request)
        return self.transport.complete_json(request)

    def _metadata(
        self,
        *,
        confidence_score: float | None = None,
        warnings: list[str] | None = None,
    ) -> ProviderMetadata:
        return _metadata(
            provider_name=self.provider_name,
            model_name=self.settings.model_name,
            confidence_score=confidence_score,
            warnings=warnings,
        )


def _book_summary_source(book: Book) -> GroundingSource:
    return GroundingSource(
        source_id=f"book-{book.id}-catalog-summary",
        source_type="summary_document",
        title=book.title,
        metadata={"summary": book.description},
        copyright_status="copyrighted",
        allowed_processing_mode="summary_only",
        source_notes=["Catalog summary only; no full text included."],
    )


def _itinerary_from_response(
    response: dict[str, Any],
    destination: Destination,
    book: Book,
    request: ItineraryGenerationRequest,
    pois: list[POI],
    metadata: ProviderMetadata,
) -> Itinerary:
    from app.schemas.domain import ItineraryDay, ItineraryStop

    stop_ids = [str(item) for item in response.get("poi_ids") or [poi.id for poi in pois]]
    poi_by_id = {poi.id: poi for poi in pois}
    stops = [
        ItineraryStop(
            id=f"stop-{poi_id}",
            poi=poi_by_id[poi_id],
            order=index + 1,
            title=poi_by_id[poi_id].name,
            narrativeNote=poi_by_id[poi_id].literaryRelevance,
            logisticsNote="Generated from grounded LLM output; verify route details.",
        )
        for index, poi_id in enumerate(stop_ids)
        if poi_id in poi_by_id
    ]
    day = ItineraryDay(
        id=f"day-{destination.id}-{book.id}-1",
        dayNumber=1,
        title=str(response.get("day_title") or f"{book.title}: Day 1"),
        summary=str(response.get("day_summary") or response.get("summary") or ""),
        stops=stops,
    )
    return Itinerary(
        id=f"it-{destination.id}-{book.id}-{request.durationDays}-{request.transportationMode}-llm",
        destinationId=destination.id,
        bookId=book.id,
        title=str(response.get("title") or f"{book.title} in {destination.name}"),
        summary=str(response.get("summary") or "Grounded LLM itinerary candidate."),
        durationDays=request.durationDays,
        transportationMode=request.transportationMode,
        days=[day],
        isPublic=True,
        visibility="public",
        generatedFrom="new_generation",
        sourceType="new_mock_generation",
        createdByMode="anonymous",
        subscriberOnly=False,
        adaptationNotes=[],
        createdAt=MOCK_CREATED_AT,
        providerName=metadata.provider_name,
        providerType=metadata.provider_type,
        providerVersion=metadata.provider_version,
        providerRequestId=metadata.request_id,
        generatedByService="openai_compatible",
        confidenceScore=metadata.confidence_score,
        provenanceMetadata=metadata.public_dict(),
    )


def _provider_request_payload(request: GroundedLLMRequest) -> dict[str, Any]:
    return {
        "task": request.task,
        "book": request.book.model_dump() if request.book else None,
        "destination": request.destination.model_dump() if request.destination else None,
        "sources": [source.__dict__ for source in request.sources],
        "pois": [poi.model_dump() for poi in request.pois],
        "itinerary": request.itinerary.model_dump() if request.itinerary else None,
        "itinerary_request": (
            request.itinerary_request.model_dump() if request.itinerary_request else None
        ),
        "review": request.review.model_dump() if request.review else None,
        "constraints": request.constraints,
    }


def _metadata(
    *,
    provider_name: str,
    model_name: str | None = None,
    request_id: str | None = None,
    confidence_score: float | None = None,
    latency_ms: int | None = None,
    warnings: list[str] | None = None,
) -> ProviderMetadata:
    return ProviderMetadata(
        provider_name=provider_name,
        provider_type=ProviderType.LLM.value,
        provider_version="openai-compatible-v1",
        request_id=request_id,
        confidence_score=confidence_score,
        generated_at=utc_now_iso(),
        model_name=model_name,
        cost_estimate=0.0,
        latency_ms=latency_ms,
        warnings=warnings or [],
    )


def _provider_error(
    code: ProviderErrorCode,
    message: str,
    *,
    latency_ms: int | None = None,
) -> ProviderError:
    return ProviderError(
        code,
        message,
        metadata=ProviderMetadata(
            provider_name="openai_compatible",
            provider_type=ProviderType.LLM.value,
            provider_version="openai-compatible-v1",
            generated_at=utc_now_iso(),
            latency_ms=latency_ms,
        ),
    )
