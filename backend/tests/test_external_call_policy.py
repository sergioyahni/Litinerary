import pytest

from app.core.config import get_settings
from app.core.provider_guards import require_external_call_allowed
from app.services.mock_ai_service import get_ai_pipeline, validate_llm_startup
from app.services.openai_compatible_llm_adapter import (
    OpenAICompatibleLLMSettings,
    OpenAICompatibleTransport,
)
from app.services.provider_contracts import ProviderError, ProviderErrorCode, ProviderType
from app.services.qdrant_vector_store import QdrantHttpTransport, QdrantSettings
from app.services.vector_service import get_vector_service


@pytest.fixture(autouse=True)
def clear_policy_caches():
    get_settings.cache_clear()
    get_ai_pipeline.cache_clear()
    get_vector_service.cache_clear()
    yield
    get_settings.cache_clear()
    get_ai_pipeline.cache_clear()
    get_vector_service.cache_clear()


def test_standard_test_mode_blocks_external_calls_even_when_allowed(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.delenv("ENABLE_INTEGRATION_TESTS", raising=False)

    with pytest.raises(ProviderError) as exc_info:
        require_external_call_allowed(
            provider_name="openai_compatible",
            provider_type=ProviderType.LLM,
            feature_flag_name="ENABLE_REAL_LLM",
            feature_enabled=True,
            required_config={"LLM_API_KEY": "test-key"},
        )

    assert exc_info.value.code == ProviderErrorCode.EXTERNAL_CALL_BLOCKED
    assert "standard APP_ENV=test" in exc_info.value.message


def test_real_adapter_startup_fails_safely_when_external_calls_are_disabled(
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_ALLOWED_ENVIRONMENTS", "development")
    monkeypatch.delenv("ALLOW_EXTERNAL_CALLS", raising=False)

    with pytest.raises(ProviderError) as exc_info:
        validate_llm_startup()

    assert exc_info.value.code == ProviderErrorCode.EXTERNAL_CALL_BLOCKED
    assert "ALLOW_EXTERNAL_CALLS=false" in exc_info.value.message


def test_real_adapter_startup_fails_clearly_when_required_config_is_missing(
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_ALLOWED_ENVIRONMENTS", "development")
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with pytest.raises(ProviderError) as exc_info:
        validate_llm_startup()

    assert exc_info.value.code == ProviderErrorCode.NOT_CONFIGURED
    assert "LLM_API_KEY" in exc_info.value.message


def test_http_transport_guard_blocks_before_network(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_REAL_VECTOR_DB", "true")
    monkeypatch.delenv("ALLOW_EXTERNAL_CALLS", raising=False)
    transport = QdrantHttpTransport(QdrantSettings(url="https://qdrant.example.test"))

    with pytest.raises(ProviderError) as exc_info:
        transport.request("GET", "/")

    assert exc_info.value.code == ProviderErrorCode.EXTERNAL_CALL_BLOCKED


def test_mock_and_fake_providers_still_work_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ALLOW_EXTERNAL_CALLS", raising=False)
    monkeypatch.delenv("ENABLE_REAL_LLM", raising=False)
    monkeypatch.delenv("ENABLE_REAL_VECTOR_DB", raising=False)

    assert get_ai_pipeline() is not None
    assert get_vector_service() is not None


def test_integration_test_mode_is_explicit_opt_in(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("ENABLE_INTEGRATION_TESTS", "true")

    require_external_call_allowed(
        provider_name="openai_compatible",
        provider_type=ProviderType.LLM,
        feature_flag_name="ENABLE_REAL_LLM",
        feature_enabled=True,
        required_config={"LLM_API_KEY": "test-key", "LLM_MODEL_NAME": "test-model"},
    )


def test_openai_http_transport_is_guarded_without_policy_opt_in(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("ALLOW_EXTERNAL_CALLS", raising=False)
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("LLM_ALLOWED_ENVIRONMENTS", "development")
    transport = OpenAICompatibleTransport(
        OpenAICompatibleLLMSettings(api_key="test-key", model_name="test-model")
    )

    with pytest.raises(ProviderError) as exc_info:
        transport.complete_json(_minimal_grounded_request())

    assert exc_info.value.code == ProviderErrorCode.EXTERNAL_CALL_BLOCKED


def _minimal_grounded_request():
    from app.services.ai_types import GroundedLLMRequest

    return GroundedLLMRequest(task="test_guard_only")
