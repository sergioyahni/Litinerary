import json
import logging

import pytest

from app.core.config import Settings, get_settings
from app.core.observability import (
    EventName,
    ProviderTelemetry,
    log_event,
    record_provider_telemetry,
)
from app.core.readiness import provider_status


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
    monkeypatch.setenv("LLM_API_KEY", "super-secret-key")
    monkeypatch.setenv("TTS_API_KEY", "secret-tts-key")

    response = client.get("/api/readiness")
    body = response.text

    assert response.status_code == 200
    assert "super-secret-key" not in body
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
