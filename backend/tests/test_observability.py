import json
import logging

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.observability import (
    EventName,
    ProviderTelemetry,
    log_event,
    record_provider_telemetry,
)
from app.core.readiness import provider_status
from app.main import app, provider_error_handler
from app.services.provider_contracts import (
    ProviderError,
    ProviderErrorCode,
    ProviderMetadata,
    ProviderType,
)


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _json_messages(caplog):
    messages = []
    for record in caplog.records:
        try:
            messages.append(json.loads(record.message))
        except json.JSONDecodeError:
            continue
    return messages


def test_health_endpoint_returns_request_id_header(client) -> None:
    response = client.get("/api/health", headers={"X-Request-ID": "req-test-123"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "req-test-123"


def test_readiness_endpoint_reports_database_and_provider_modes(client) -> None:
    response = client.get("/api/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["checks"]["database"]["status"] == "ok"
    provider = next(
        item for item in payload["checks"]["providers"] if item["providerType"] == "llm"
    )
    assert provider["mode"] == "mock"
    assert "credentialsConfigured" in provider


def test_readiness_redacts_sensitive_provider_configuration(monkeypatch, client) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_API_KEY", "redacted-test-key-placeholder")
    monkeypatch.setenv("TTS_API_KEY", "secret-tts-key")

    response = client.get("/api/readiness")
    body = response.text

    assert response.status_code == 200
    assert "redacted-test-key-placeholder" not in body
    assert "secret-tts-key" not in body
    assert "credentialsConfigured" in body


def test_provider_status_exposes_booleans_not_secret_values() -> None:
    status = provider_status(
        Settings(
            llm_provider="openai_compatible",
            enable_real_llm=True,
            llm_api_key="do-not-leak",
        )
    )

    llm = next(item for item in status if item["providerType"] == "llm")
    assert llm["credentialsConfigured"] is True
    assert llm["requiredConfigPresent"] is True
    assert "do-not-leak" not in json.dumps(status)


def test_llm_readiness_reports_gate_state_without_secret_values() -> None:
    status = provider_status(
        Settings(
            app_env="development",
            llm_provider="openai_compatible",
            enable_real_llm=True,
            allow_external_calls=True,
            llm_api_key="do-not-leak",
            llm_model_name="test-model",
            llm_allowed_environments=["development"],
            external_call_allowed_environments=["production"],
        )
    )

    llm = next(item for item in status if item["providerType"] == "llm")

    assert llm["providerName"] == "openai_compatible"
    assert llm["realEnabled"] is True
    assert llm["externalCallsAllowed"] is True
    assert llm["credentialsConfigured"] is True
    assert llm["requiredConfigPresent"] is True
    assert llm["environmentAllowed"] is False
    assert "do-not-leak" not in json.dumps(status)


def test_structured_log_redacts_sensitive_fields(caplog) -> None:
    caplog.set_level(logging.INFO, logger="litinerary")

    log_event(
        "redaction_test",
        api_key="secret",
        token="secret-token",
        safe_value="visible",
    )

    payload = _json_messages(caplog)[-1]
    assert payload["api_key"] == "[redacted]"
    assert payload["token"] == "[redacted]"
    assert payload["safe_value"] == "visible"
    assert payload["app_env"] in {
        "development",
        "test",
        "internal",
        "beta",
        "staging",
        "production",
    }


def test_api_exception_produces_correlated_failure_event(caplog, db_session) -> None:
    caplog.set_level(logging.INFO, logger="litinerary")
    path = "/api/test-observability-failure"
    if not any(route.path == path for route in app.routes):

        @app.get(path)
        def test_observability_failure_route() -> None:
            raise RuntimeError("synthetic failure with token=redacted-test-token")

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.get(path, headers={"X-Request-ID": "req-incident-drill"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    events = _json_messages(caplog)
    failure = next(item for item in events if item["event"] == EventName.API_REQUEST_FAILED)
    assert failure["request_id"] == "req-incident-drill"
    assert failure["status_code"] == 500
    assert failure["success"] is False
    assert failure["error_type"] == "RuntimeError"
    assert "redacted-test-token" not in "\n".join(record.message for record in caplog.records)


def test_structured_log_redacts_nested_sentinel_values(caplog) -> None:
    caplog.set_level(logging.INFO, logger="litinerary")
    sentinel = "redacted-test-key-placeholder"

    log_event(
        "nested_redaction_test",
        provider_payload={
            "authorization": f"Bearer {sentinel}",
            "promptText": f"private prompt {sentinel}",
            "safe_value": "visible",
        },
        raw_response={"body": sentinel},
    )

    raw_messages = "\n".join(record.message for record in caplog.records)
    payload = _json_messages(caplog)[-1]
    assert sentinel not in raw_messages
    assert payload["provider_payload"]["authorization"] == "[redacted]"
    assert payload["provider_payload"]["promptText"] == "[redacted]"
    assert payload["provider_payload"]["safe_value"] == "visible"
    assert payload["raw_response"] == "[redacted]"


def test_provider_telemetry_hook_logs_success_and_failure(caplog) -> None:
    caplog.set_level(logging.INFO, logger="litinerary")

    record_provider_telemetry(
        ProviderTelemetry(
            provider_type="llm",
            provider_name="fake",
            operation="itinerary_generation",
            success=True,
            latency_ms=12,
            warning_count=1,
            request_id="req-telemetry",
        )
    )
    record_provider_telemetry(
        ProviderTelemetry(
            provider_type="llm",
            provider_name="fake",
            operation="itinerary_generation",
            success=False,
            error_type="rate_limited",
            request_id="req-telemetry",
        )
    )

    events = _json_messages(caplog)
    assert any(item["event"] == EventName.PROVIDER_CALL_SUCCEEDED for item in events)
    failure = next(item for item in events if item["event"] == EventName.PROVIDER_CALL_FAILED)
    assert failure["error_type"] == "rate_limited"
    assert failure["request_id"] == "req-telemetry"


def _request(path: str = "/api/itinerary/generate") -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [],
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("testclient", 123),
        }
    )


def _diagnostic_provider_error() -> ProviderError:
    return ProviderError(
        ProviderErrorCode.INVALID_RESPONSE,
        "LLM provider returned HTTP 502.",
        metadata=ProviderMetadata(
            provider_name="openai_compatible",
            provider_type=ProviderType.LLM.value,
            request_id="req_safe_502",
            warnings=[
                "endpoint_kind=chat_completions",
                "endpoint_host=api.openai.com",
                "endpoint_path=/v1/chat/completions",
                "provider_reached=true",
                "provider_http_status=502",
                "provider_error_type=server_error",
                "provider_error_code=bad_gateway",
                "failure_category=http_error",
                "raw_prompt=redacted-test-key-placeholder",
                "authorization=Bearer placeholder",
            ],
        ),
    )


def test_provider_error_handler_exposes_redacted_diagnostics_in_development(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()

    response = provider_error_handler(_request(), _diagnostic_provider_error())
    body = json.loads(response.body)
    header = response.headers["X-Litinerary-Provider-Diagnostics"]

    assert response.status_code == 502
    assert body["detail"]["diagnostics"]["provider_reached"] == "true"
    assert body["detail"]["diagnostics"]["provider_http_status"] == "502"
    assert body["detail"]["diagnostics"]["endpoint_kind"] == "chat_completions"
    assert body["detail"]["diagnostics"]["endpoint_host"] == "api.openai.com"
    assert body["detail"]["diagnostics"]["endpoint_path"] == "/v1/chat/completions"
    assert body["detail"]["diagnostics"]["provider_error_type"] == "server_error"
    assert body["detail"]["diagnostics"]["provider_error_code"] == "bad_gateway"
    assert "redacted-test-key-placeholder" not in response.body.decode("utf-8")
    assert "redacted-test-key-placeholder" not in header
    assert "raw_prompt" not in header
    assert "authorization" not in header


def test_provider_error_handler_keeps_extra_diagnostics_out_of_beta(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "beta")
    get_settings.cache_clear()

    response = provider_error_handler(_request(), _diagnostic_provider_error())
    body = json.loads(response.body)

    assert response.status_code == 502
    assert "diagnostics" not in body["detail"]
    assert "X-Litinerary-Provider-Diagnostics" not in response.headers
    assert "redacted-test-key-placeholder" not in response.body.decode("utf-8")
