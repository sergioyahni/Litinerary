import pytest
import json
from io import BytesIO
import socket
import ssl
from urllib.error import HTTPError, URLError

from app.core.config import get_settings
from app.data.mock_data import BOOKS, DESTINATIONS, ITINERARIES, POIS
from app.schemas.domain import ItineraryGenerationRequest
from app.services.ai_types import GroundedLLMRequest, GroundingSource
from app.services.llm_grounding import validate_grounded_request, validate_source
from app.services.mock_ai_service import MockAIServicePipeline, get_ai_pipeline, validate_llm_startup
from app.services import openai_compatible_llm_adapter as adapter_module
from app.services.openai_compatible_llm_adapter import (
    OpenAICompatibleAIPipeline,
    OpenAICompatibleLLMSettings,
    OpenAICompatibleTransport,
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
    monkeypatch.setenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS", "development")

    pipeline = get_ai_pipeline()

    assert isinstance(pipeline, OpenAICompatibleAIPipeline)


def test_missing_llm_config_fails_clearly(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS", "development")
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with pytest.raises(ProviderError, match="LLM_API_KEY"):
        validate_llm_startup()


def test_missing_llm_model_name_fails_clearly(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL_NAME", "")
    monkeypatch.setenv("LLM_ALLOWED_ENVIRONMENTS", "development")
    monkeypatch.setenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS", "development")

    with pytest.raises(ProviderError, match="LLM_MODEL_NAME"):
        validate_llm_startup()


def test_real_llm_rejects_non_openai_compatible_provider(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("LLM_PROVIDER", "other_provider")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_ALLOWED_ENVIRONMENTS", "development")
    monkeypatch.setenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS", "development")

    with pytest.raises(RuntimeError, match="OpenAI-compatible"):
        validate_llm_startup()


def test_real_llm_is_blocked_in_test_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    with pytest.raises(ProviderError, match="standard APP_ENV=test"):
        validate_llm_startup()


def test_internal_live_llm_requires_staged_internal_approval(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "internal")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL_NAME", "test-model")
    monkeypatch.setenv("LLM_ALLOWED_ENVIRONMENTS", "internal")
    monkeypatch.setenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS", "internal")
    monkeypatch.delenv("ENABLE_STAGED_INTERNAL_LLM_TESTING", raising=False)

    with pytest.raises(RuntimeError, match="ENABLE_STAGED_INTERNAL_LLM_TESTING"):
        validate_llm_startup()


def test_internal_live_llm_requires_internal_access_gate(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "internal")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("ENABLE_STAGED_INTERNAL_LLM_TESTING", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL_NAME", "test-model")
    monkeypatch.setenv("LLM_ALLOWED_ENVIRONMENTS", "internal")
    monkeypatch.setenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS", "internal")
    monkeypatch.delenv("ENABLE_INTERNAL_ACCESS_GATE", raising=False)

    with pytest.raises(RuntimeError, match="ENABLE_INTERNAL_ACCESS_GATE"):
        validate_llm_startup()


def test_internal_live_llm_startup_accepts_explicit_internal_gates(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "internal")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("ENABLE_STAGED_INTERNAL_LLM_TESTING", "true")
    monkeypatch.setenv("ENABLE_INTERNAL_ACCESS_GATE", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL_NAME", "test-model")
    monkeypatch.setenv("LLM_ALLOWED_ENVIRONMENTS", "internal")
    monkeypatch.setenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS", "internal")

    validate_llm_startup()


def test_transport_success_path_uses_mocked_urlopen_without_network(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL_NAME", "test-model")
    monkeypatch.setenv("LLM_ALLOWED_ENVIRONMENTS", "development")
    monkeypatch.setenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS", "development")
    get_settings.cache_clear()
    calls = []

    class FakeResponse:
        headers = {"x-request-id": "req-offline-test"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": "{\"ok\": true}"}}]}
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr(adapter_module, "urlopen", fake_urlopen)
    transport = OpenAICompatibleTransport(
        OpenAICompatibleLLMSettings(
            api_key="test-key",
            model_name="test-model",
            base_url="https://llm.example.test/v1",
            timeout_seconds=7,
        )
    )

    response, metadata = transport.complete_json(GroundedLLMRequest(task="offline_test"))

    assert response == {"ok": True}
    assert metadata.request_id == "req-offline-test"
    assert len(calls) == 1
    assert calls[0][1] == 7
    assert calls[0][0].full_url == "https://llm.example.test/v1/chat/completions"
    request_payload = json.loads(calls[0][0].data.decode("utf-8"))
    assert request_payload["model"] == "test-model"
    assert request_payload["response_format"] == {"type": "json_object"}
    assert request_payload["max_tokens"] == 1200
    assert "max_completion_tokens" not in request_payload
    assert request_payload["messages"][0]["role"] == "system"
    assert request_payload["messages"][1]["role"] == "user"


def test_transport_can_use_max_completion_tokens_for_newer_chat_models(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL_NAME", "test-model")
    monkeypatch.setenv("LLM_ALLOWED_ENVIRONMENTS", "development")
    monkeypatch.setenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS", "development")
    get_settings.cache_clear()
    calls = []

    class FakeResponse:
        headers = {"x-request-id": "req-offline-test"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": "{\"ok\": true}"}}]}
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls.append(request)
        return FakeResponse()

    monkeypatch.setattr(adapter_module, "urlopen", fake_urlopen)
    transport = OpenAICompatibleTransport(
        OpenAICompatibleLLMSettings(
            api_key="test-key",
            model_name="test-model",
            max_tokens=321,
            output_token_parameter="max_completion_tokens",
        )
    )

    transport.complete_json(GroundedLLMRequest(task="offline_test"))

    request_payload = json.loads(calls[0].data.decode("utf-8"))
    assert request_payload["max_completion_tokens"] == 321
    assert "max_tokens" not in request_payload


def test_invalid_output_token_parameter_fails_closed() -> None:
    with pytest.raises(ProviderError) as exc_info:
        OpenAICompatibleAIPipeline(
            OpenAICompatibleLLMSettings(
                api_key="test-key",
                output_token_parameter="unsafe_parameter",
            ),
            transport=FakeLLMTransport(),
        )

    assert exc_info.value.code == ProviderErrorCode.NOT_CONFIGURED
    assert "output token parameter" in exc_info.value.message


def test_transport_provider_failure_returns_safe_error(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL_NAME", "test-model")
    monkeypatch.setenv("LLM_ALLOWED_ENVIRONMENTS", "development")
    monkeypatch.setenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS", "development")
    get_settings.cache_clear()

    def fake_urlopen(request, timeout):
        raise HTTPError(
            request.full_url,
            500,
            "provider included secret test-key in reason",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(adapter_module, "urlopen", fake_urlopen)
    transport = OpenAICompatibleTransport(
        OpenAICompatibleLLMSettings(api_key="test-key", model_name="test-model")
    )

    with pytest.raises(ProviderError) as exc_info:
        transport.complete_json(GroundedLLMRequest(task="offline_test"))

    assert exc_info.value.code == ProviderErrorCode.INVALID_RESPONSE
    assert exc_info.value.message == "LLM provider returned HTTP 500."
    assert "test-key" not in str(exc_info.value.to_dict())


def test_transport_provider_502_diagnostics_are_redacted(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "redacted-test-key-placeholder")
    monkeypatch.setenv("LLM_MODEL_NAME", "test-model")
    monkeypatch.setenv("LLM_ALLOWED_ENVIRONMENTS", "development")
    monkeypatch.setenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS", "development")
    get_settings.cache_clear()

    def fake_urlopen(request, timeout):
        body = json.dumps(
            {
                "error": {
                    "message": "raw provider text redacted-test-key-placeholder",
                    "type": "server_error",
                    "code": "bad_gateway",
                }
            }
        ).encode("utf-8")
        raise HTTPError(
            request.full_url,
            502,
            "provider included secret redacted-test-key-placeholder in reason",
            hdrs={"x-request-id": "req_502_safe"},
            fp=BytesIO(body),
        )

    monkeypatch.setattr(adapter_module, "urlopen", fake_urlopen)
    transport = OpenAICompatibleTransport(
        OpenAICompatibleLLMSettings(
            api_key="redacted-test-key-placeholder",
            model_name="test-model",
        )
    )

    with pytest.raises(ProviderError) as exc_info:
        transport.complete_json(GroundedLLMRequest(task="offline_test"))

    payload = exc_info.value.to_dict()
    warnings = payload["metadata"]["warnings"]
    assert exc_info.value.code == ProviderErrorCode.INVALID_RESPONSE
    assert payload["message"] == "LLM provider returned HTTP 502."
    assert payload["metadata"]["request_id"] == "req_502_safe"
    assert "provider_reached=true" in warnings
    assert "provider_http_status=502" in warnings
    assert "endpoint_kind=chat_completions" in warnings
    assert "endpoint_host=api.openai.com" in warnings
    assert "endpoint_path=/v1/chat/completions" in warnings
    assert "provider_error_type=server_error" in warnings
    assert "provider_error_code=bad_gateway" in warnings
    assert "redacted-test-key-placeholder" not in str(payload)
    assert "raw provider text" not in str(payload)


def test_transport_malformed_provider_response_fails_safely(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "redacted-test-key-placeholder")
    monkeypatch.setenv("LLM_MODEL_NAME", "test-model")
    monkeypatch.setenv("LLM_ALLOWED_ENVIRONMENTS", "development")
    monkeypatch.setenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS", "development")
    get_settings.cache_clear()

    class FakeMalformedResponse:
        headers = {"x-request-id": "req-malformed"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b'{"choices":[{"message":{"content":"not-json"}}]}'

    def fake_urlopen(request, timeout):
        return FakeMalformedResponse()

    monkeypatch.setattr(adapter_module, "urlopen", fake_urlopen)
    transport = OpenAICompatibleTransport(
        OpenAICompatibleLLMSettings(
            api_key="redacted-test-key-placeholder",
            model_name="test-model",
        )
    )

    with pytest.raises(ProviderError) as exc_info:
        transport.complete_json(GroundedLLMRequest(task="offline_test"))

    payload = exc_info.value.to_dict()
    assert exc_info.value.code == ProviderErrorCode.INVALID_RESPONSE
    assert payload["message"] == "LLM provider returned an invalid JSON response."
    assert payload["metadata"]["request_id"] == "req-malformed"
    assert "failure_category=response_parse_error" in payload["metadata"]["warnings"]
    assert "provider_reached=true" in payload["metadata"]["warnings"]
    assert "redacted-test-key-placeholder" not in str(payload)


def test_transport_timeout_diagnostics_are_redacted(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "redacted-test-key-placeholder")
    monkeypatch.setenv("LLM_MODEL_NAME", "test-model")
    monkeypatch.setenv("LLM_ALLOWED_ENVIRONMENTS", "development")
    monkeypatch.setenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS", "development")
    get_settings.cache_clear()

    def fake_urlopen(request, timeout):
        raise TimeoutError("timeout redacted-test-key-placeholder")

    monkeypatch.setattr(adapter_module, "urlopen", fake_urlopen)
    transport = OpenAICompatibleTransport(
        OpenAICompatibleLLMSettings(
            api_key="redacted-test-key-placeholder",
            model_name="test-model",
        )
    )

    with pytest.raises(ProviderError) as exc_info:
        transport.complete_json(GroundedLLMRequest(task="offline_test"))

    payload = exc_info.value.to_dict()
    assert exc_info.value.code == ProviderErrorCode.TIMEOUT
    assert "failure_category=timeout" in payload["metadata"]["warnings"]
    assert "provider_reached=unknown" in payload["metadata"]["warnings"]
    assert "redacted-test-key-placeholder" not in str(payload)


def test_transport_url_error_diagnostics_are_redacted(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "redacted-test-key-placeholder")
    monkeypatch.setenv("LLM_MODEL_NAME", "test-model")
    monkeypatch.setenv("LLM_ALLOWED_ENVIRONMENTS", "development")
    monkeypatch.setenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS", "development")
    get_settings.cache_clear()

    def fake_urlopen(request, timeout):
        raise URLError("proxy url error redacted-test-key-placeholder")

    monkeypatch.setattr(adapter_module, "urlopen", fake_urlopen)
    transport = OpenAICompatibleTransport(
        OpenAICompatibleLLMSettings(
            api_key="redacted-test-key-placeholder",
            model_name="test-model",
        )
    )

    with pytest.raises(ProviderError) as exc_info:
        transport.complete_json(GroundedLLMRequest(task="offline_test"))

    payload = exc_info.value.to_dict()
    assert exc_info.value.code == ProviderErrorCode.UNAVAILABLE
    assert "failure_category=url_error" in payload["metadata"]["warnings"]
    assert "provider_reached=false" in payload["metadata"]["warnings"]
    assert "url_error_reason_type=str" in payload["metadata"]["warnings"]
    assert "url_error_reason_category=proxy" in payload["metadata"]["warnings"]
    assert "redacted-test-key-placeholder" not in str(payload)


@pytest.mark.parametrize(
    ("reason", "category"),
    [
        (socket.gaierror("name or service not known"), "dns"),
        (ssl.SSLError("certificate verify failed"), "tls"),
        (TimeoutError("timed out"), "timeout"),
        (ConnectionRefusedError("connection refused"), "connection_refused"),
    ],
)
def test_transport_url_error_reason_categories_are_safe(monkeypatch, reason, category) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "redacted-test-key-placeholder")
    monkeypatch.setenv("LLM_MODEL_NAME", "test-model")
    monkeypatch.setenv("LLM_ALLOWED_ENVIRONMENTS", "development")
    monkeypatch.setenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS", "development")
    get_settings.cache_clear()

    def fake_urlopen(request, timeout):
        raise URLError(reason)

    monkeypatch.setattr(adapter_module, "urlopen", fake_urlopen)
    transport = OpenAICompatibleTransport(
        OpenAICompatibleLLMSettings(
            api_key="redacted-test-key-placeholder",
            model_name="test-model",
        )
    )

    with pytest.raises(ProviderError) as exc_info:
        transport.complete_json(GroundedLLMRequest(task="offline_test"))

    payload = exc_info.value.to_dict()
    assert f"url_error_reason_category={category}" in payload["metadata"]["warnings"]
    assert "redacted-test-key-placeholder" not in str(payload)


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


def test_london_sherlock_smoke_seed_is_grounded_for_live_adapter() -> None:
    transport = FakeLLMTransport(
        {
            "title": "A Holmes Walk Through Baker Street",
            "summary": "A concise Sherlock Holmes walk anchored on Baker Street.",
            "days": [
                {
                    "dayNumber": 1,
                    "theme": "Observation and deduction",
                    "stops": [
                        {
                            "poiId": "baker-street",
                            "title": "Begin at Baker Street",
                            "narrativeNote": "Start with the symbolic center of Holmes' London.",
                            "logisticsNote": "Public street; check nearby museum hours separately.",
                            "estimatedStartTime": "09:30",
                            "estimatedEndTime": "10:15",
                        }
                    ],
                }
            ],
        }
    )
    pipeline = OpenAICompatibleAIPipeline(
        OpenAICompatibleLLMSettings(api_key="test-key"),
        transport=transport,
    )
    destination = next(item for item in DESTINATIONS if item.id == "london")
    book = next(item for item in BOOKS if item.id == "sherlock-holmes")
    pois = [item for item in POIS if item.destinationId == "london" and book.id in item.bookIds]

    itinerary = pipeline.generate_candidate_itinerary(
        destination,
        book,
        pois,
        ItineraryGenerationRequest(
            destinationId="london",
            bookId="sherlock-holmes",
            durationDays=1,
            transportationMode="walking",
        ),
    )

    assert itinerary.days[0].stops[0].poi.id == "baker-street"
    assert len(transport.calls) == 1


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
