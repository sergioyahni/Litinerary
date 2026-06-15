import pytest

from app.core.config import get_settings
from app.data.mock_data import BOOKS, DESTINATIONS, ITINERARIES, POIS
from app.schemas.domain import ItineraryGenerationRequest
from app.services.ai_types import GroundedLLMRequest, GroundingSource
from app.services.llm_grounding import validate_grounded_request, validate_source
from app.services.mock_ai_service import MockAIServicePipeline, get_ai_pipeline, validate_llm_startup
from app.services.openai_compatible_llm_adapter import (
    OpenAICompatibleAIPipeline,
    OpenAICompatibleLLMSettings,
)
from app.services.provider_contracts import ProviderError, ProviderErrorCode, ProviderMetadata, ProviderType


class FakeLLMTransport:
    def __init__(
        self,
        response: dict | None = None,
        error: ProviderError | None = None,
    ) -> None:
        self.response = response or {"summary": "Safe summary.", "locations": ["london"]}
        self.error = error
        self.calls: list[GroundedLLMRequest] = []

    def complete_json(self, request: GroundedLLMRequest):
        self.calls.append(request)
        if self.error:
            raise self.error
        return self.response, ProviderMetadata(
            provider_name="openai_compatible",
            provider_type=ProviderType.LLM.value,
            provider_version="openai-compatible-v1",
            request_id="fake-llm-request",
            confidence_score=0.86,
            generated_at="2026-06-14T00:00:00+00:00",
            model_name="fake-model",
            cost_estimate=0.0,
            warnings=["fake transport"],
        )


@pytest.fixture(autouse=True)
def clear_ai_cache():
    get_settings.cache_clear()
    get_ai_pipeline.cache_clear()
    yield
    get_settings.cache_clear()
    get_ai_pipeline.cache_clear()


def test_mock_ai_remains_default(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_REAL_LLM", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LITINERARY_AI_PROVIDER", raising=False)

    pipeline = get_ai_pipeline()

    assert isinstance(pipeline, MockAIServicePipeline)


def test_openai_compatible_selection_requires_real_llm_flag(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.delenv("ENABLE_REAL_LLM", raising=False)

    with pytest.raises(RuntimeError, match="ENABLE_REAL_LLM"):
        get_ai_pipeline()


def test_openai_compatible_selection_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_ALLOWED_ENVIRONMENTS", "development")

    pipeline = get_ai_pipeline()

    assert isinstance(pipeline, OpenAICompatibleAIPipeline)


def test_missing_llm_config_fails_clearly(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with pytest.raises(ProviderError, match="LLM_API_KEY"):
        validate_llm_startup()


def test_real_llm_is_blocked_in_test_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    with pytest.raises(ProviderError, match="standard APP_ENV=test"):
        validate_llm_startup()


def test_unsafe_full_text_source_is_rejected_before_provider_call() -> None:
    transport = FakeLLMTransport()
    pipeline = OpenAICompatibleAIPipeline(
        OpenAICompatibleLLMSettings(api_key="test-key"),
        transport=transport,
    )
    book = next(item for item in BOOKS if item.id == "oliver-twist")
    source = GroundingSource(
        source_id="unsafe",
        source_type="summary_document",
        metadata={"fullText": "Do not send this."},
        copyright_status="copyrighted",
        allowed_processing_mode="summary_only",
    )

    with pytest.raises(ProviderError) as exc_info:
        pipeline._complete(GroundedLLMRequest(task="summary_location_extraction", book=book, sources=[source]))

    assert exc_info.value.code == ProviderErrorCode.UNSAFE_INPUT
    assert transport.calls == []


def test_grounding_requires_license_or_known_copyright_for_summary() -> None:
    source = GroundingSource(
        source_id="unknown-summary",
        source_type="summary_document",
        metadata={"summary": "A safe summary."},
        copyright_status="unknown",
        allowed_processing_mode="summary_only",
    )

    with pytest.raises(ProviderError) as exc_info:
        validate_source(source)

    assert exc_info.value.code == ProviderErrorCode.UNSAFE_INPUT


def test_itinerary_generation_requires_poi_provenance_before_call() -> None:
    transport = FakeLLMTransport()
    pipeline = OpenAICompatibleAIPipeline(
        OpenAICompatibleLLMSettings(api_key="test-key"),
        transport=transport,
    )
    destination = next(item for item in DESTINATIONS if item.id == "london")
    book = next(item for item in BOOKS if item.id == "oliver-twist")
    poi = next(item for item in POIS if item.id == "smithfield-market").model_copy(
        update={"verificationNotes": [], "provenanceMetadata": {}},
        deep=True,
    )

    with pytest.raises(ProviderError) as exc_info:
        pipeline.generate_candidate_itinerary(
            destination,
            book,
            [poi],
            ItineraryGenerationRequest(
                destinationId="london",
                bookId="oliver-twist",
                durationDays=1,
                transportationMode="walking",
            ),
        )

    assert exc_info.value.code == ProviderErrorCode.UNSAFE_INPUT
    assert transport.calls == []


def test_provider_response_is_normalized_for_summary_extraction() -> None:
    transport = FakeLLMTransport({"summary": "Grounded summary.", "locations": ["london"]})
    pipeline = OpenAICompatibleAIPipeline(
        OpenAICompatibleLLMSettings(api_key="test-key"),
        transport=transport,
    )
    book = next(item for item in BOOKS if item.id == "oliver-twist")
    source = pipeline.ingest_book(book)

    result = pipeline.extract_summary_and_locations(book, source)

    assert result.summary == "Grounded summary."
    assert result.locations == ["london"]
    assert result.metadata is not None
    assert result.metadata.request_id == "fake-llm-request"
    assert len(transport.calls) == 1


def test_provider_errors_are_normalized() -> None:
    error = ProviderError(ProviderErrorCode.RATE_LIMITED, "rate limited")
    pipeline = OpenAICompatibleAIPipeline(
        OpenAICompatibleLLMSettings(api_key="test-key"),
        transport=FakeLLMTransport(error=error),
    )
    book = next(item for item in BOOKS if item.id == "oliver-twist")
    source = pipeline.ingest_book(book)

    with pytest.raises(ProviderError) as exc_info:
        pipeline.extract_summary_and_locations(book, source)

    assert exc_info.value.code == ProviderErrorCode.RATE_LIMITED


def test_judge_rejects_hallucination_prone_missing_provenance() -> None:
    itinerary = ITINERARIES[0]
    stop = itinerary.days[0].stops[0]
    bad_stop = stop.model_copy(
        update={
            "poi": stop.poi.model_copy(
                update={
                    "verificationStatus": "provider_verified",
                    "verificationNotes": [],
                    "provenanceMetadata": {},
                },
                deep=True,
            )
        },
        deep=True,
    )
    bad_day = itinerary.days[0].model_copy(update={"stops": [bad_stop]}, deep=True)
    result = MockAIServicePipeline().validate_itinerary(
        itinerary.model_copy(update={"days": [bad_day]}, deep=True)
    )

    assert result.approved is False
    assert any("grounding provenance" in reason for reason in result.reasons)
    assert result.required_fixes


@pytest.mark.skip(reason="Live LLM integration requires explicit credentials and opt-in.")
def test_live_llm_integration_skipped_by_default() -> None:
    pass
