import json
import re
import socket
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app
from app.services import openai_compatible_llm_adapter as llm_adapter_module
from app.services.affiliate_service import get_affiliate_provider
from app.services.mock_ai_service import get_ai_pipeline
from app.services.narration_service import get_narration_service
from app.services.poi_verification import get_poi_verification_adapter
from app.services.routing_service import get_routing_provider
from app.services.ticketing_service import get_ticketing_provider
from app.services.vector_service import get_vector_service


SECRET_LIKE_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}", re.IGNORECASE),
    re.compile(r"AKIA[A-Z0-9]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"AIza[A-Za-z0-9_-]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
]

PROVIDER_ENV_KEYS = [
    "APP_ENV",
    "ALLOW_EXTERNAL_CALLS",
    "ENABLE_INTEGRATION_TESTS",
    "ENABLE_STAGED_INTERNAL_LLM_TESTING",
    "ENABLE_INTERNAL_ACCESS_GATE",
    "ENABLE_REAL_LLM",
    "ENABLE_REAL_VECTOR_DB",
    "ENABLE_REAL_POI_PROVIDER",
    "ENABLE_REAL_ROUTING",
    "ENABLE_REAL_TICKETING",
    "ENABLE_REAL_TTS",
    "ENABLE_AFFILIATE_LINKS",
    "ENABLE_AUTH",
    "LITINERARY_AI_PROVIDER",
    "LLM_PROVIDER",
    "LLM_API_KEY",
    "OPENAI_API_KEY",
    "LLM_MODEL_NAME",
    "LLM_ALLOWED_ENVIRONMENTS",
    "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS",
    "LITINERARY_VECTOR_PROVIDER",
    "VECTOR_DB_PROVIDER",
    "VECTOR_DB_API_KEY",
    "QDRANT_API_KEY",
    "QDRANT_URL",
    "LITINERARY_POI_VERIFICATION_PROVIDER",
    "POI_PROVIDER",
    "POI_VERIFICATION_PROVIDER",
    "POI_PROVIDER_API_KEY",
    "GOOGLE_PLACES_API_KEY",
    "POI_VERIFICATION_API_KEY",
    "ROUTING_PROVIDER",
    "ROUTING_API_KEY",
    "OPENROUTESERVICE_API_KEY",
    "TICKETING_PROVIDER",
    "TICKETING_API_KEY",
    "AFFILIATE_PROVIDER",
    "AFFILIATE_API_KEY",
    "TTS_PROVIDER",
    "TTS_API_KEY",
    "TEXT_TO_SPEECH_API_KEY",
    "AUTH_PROVIDER",
    "AUTH_JWT_ISSUER",
    "AUTH_JWT_AUDIENCE",
    "AUTH_JWKS_URL",
    "AUTH_PROVIDER_METADATA_URL",
]


@pytest.fixture(autouse=True)
def clear_provider_caches_and_block_network(monkeypatch: pytest.MonkeyPatch):
    _clear_caches()
    original_connect = socket.socket.connect

    def guard_socket_connect(sock, address):  # noqa: ANN001
        host = address[0] if isinstance(address, tuple) and address else None
        if host in {"127.0.0.1", "::1", "localhost"}:
            return original_connect(sock, address)
        raise AssertionError("Network access is forbidden in Batch 2 provider-gate tests.")

    def fail_provider_urlopen(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise AssertionError("Provider HTTP access is forbidden in Batch 2 provider-gate tests.")

    monkeypatch.setattr(socket.socket, "connect", guard_socket_connect)
    monkeypatch.setattr(llm_adapter_module, "urlopen", fail_provider_urlopen)
    yield
    _clear_caches()


@pytest.fixture
def non_raising_client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("case_name", "env", "expected_status", "readiness_assertion"),
    [
        (
            "real_llm_without_external_calls",
            {
                "APP_ENV": "development",
                "ENABLE_REAL_LLM": "true",
                "LITINERARY_AI_PROVIDER": "openai_compatible",
                "LLM_PROVIDER": "openai_compatible",
                "LLM_API_KEY": "offline-test-key",
                "LLM_MODEL_NAME": "offline-test-model",
                "LLM_ALLOWED_ENVIRONMENTS": "development",
                "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS": "development",
            },
            503,
            lambda llm, payload: (
                llm["realEnabled"] is True
                and llm["externalCallsAllowed"] is False
                and payload["checks"]["externalCalls"]["allowed"] is False
            ),
        ),
        (
            "external_calls_without_real_llm",
            {
                "APP_ENV": "development",
                "ALLOW_EXTERNAL_CALLS": "true",
                "LITINERARY_AI_PROVIDER": "openai_compatible",
                "LLM_PROVIDER": "openai_compatible",
                "LLM_API_KEY": "offline-test-key",
                "LLM_MODEL_NAME": "offline-test-model",
                "LLM_ALLOWED_ENVIRONMENTS": "development",
                "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS": "development",
            },
            500,
            lambda llm, payload: llm["realEnabled"] is False,
        ),
        (
            "global_environment_not_allowlisted",
            {
                "APP_ENV": "development",
                "ALLOW_EXTERNAL_CALLS": "true",
                "ENABLE_REAL_LLM": "true",
                "LITINERARY_AI_PROVIDER": "openai_compatible",
                "LLM_PROVIDER": "openai_compatible",
                "LLM_API_KEY": "offline-test-key",
                "LLM_MODEL_NAME": "offline-test-model",
                "LLM_ALLOWED_ENVIRONMENTS": "development",
                "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS": "production",
            },
            503,
            lambda llm, payload: llm["environmentAllowed"] is False,
        ),
        (
            "llm_environment_not_allowlisted",
            {
                "APP_ENV": "development",
                "ALLOW_EXTERNAL_CALLS": "true",
                "ENABLE_REAL_LLM": "true",
                "LITINERARY_AI_PROVIDER": "openai_compatible",
                "LLM_PROVIDER": "openai_compatible",
                "LLM_API_KEY": "offline-test-key",
                "LLM_MODEL_NAME": "offline-test-model",
                "LLM_ALLOWED_ENVIRONMENTS": "production",
                "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS": "development",
            },
            503,
            lambda llm, payload: llm["environmentAllowed"] is False,
        ),
        (
            "missing_llm_api_key",
            {
                "APP_ENV": "development",
                "ALLOW_EXTERNAL_CALLS": "true",
                "ENABLE_REAL_LLM": "true",
                "LITINERARY_AI_PROVIDER": "openai_compatible",
                "LLM_PROVIDER": "openai_compatible",
                "LLM_MODEL_NAME": "offline-test-model",
                "LLM_ALLOWED_ENVIRONMENTS": "development",
                "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS": "development",
            },
            503,
            lambda llm, payload: llm["requiredConfigPresent"] is False,
        ),
        (
            "missing_llm_model_name",
            {
                "APP_ENV": "development",
                "ALLOW_EXTERNAL_CALLS": "true",
                "ENABLE_REAL_LLM": "true",
                "LITINERARY_AI_PROVIDER": "openai_compatible",
                "LLM_PROVIDER": "openai_compatible",
                "LLM_API_KEY": "offline-test-key",
                "LLM_MODEL_NAME": "",
                "LLM_ALLOWED_ENVIRONMENTS": "development",
                "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS": "development",
            },
            503,
            lambda llm, payload: llm["requiredConfigPresent"] is False,
        ),
        (
            "unsupported_llm_provider",
            {
                "APP_ENV": "development",
                "ALLOW_EXTERNAL_CALLS": "true",
                "ENABLE_REAL_LLM": "true",
                "LLM_PROVIDER": "unsupported_llm",
                "LLM_API_KEY": "offline-test-key",
                "LLM_MODEL_NAME": "offline-test-model",
                "LLM_ALLOWED_ENVIRONMENTS": "development",
                "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS": "development",
            },
            500,
            lambda llm, payload: llm["providerName"] == "unsupported_llm",
        ),
        (
            "unsupported_ai_provider",
            {
                "APP_ENV": "development",
                "ALLOW_EXTERNAL_CALLS": "true",
                "ENABLE_REAL_LLM": "true",
                "LITINERARY_AI_PROVIDER": "unsupported_ai",
                "LLM_PROVIDER": "openai_compatible",
                "LLM_API_KEY": "offline-test-key",
                "LLM_MODEL_NAME": "offline-test-model",
                "LLM_ALLOWED_ENVIRONMENTS": "development",
                "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS": "development",
            },
            500,
            lambda llm, payload: llm["providerName"] == "openai_compatible",
        ),
        (
            "conflicting_provider_env_keeps_generation_mock",
            {
                "APP_ENV": "development",
                "ALLOW_EXTERNAL_CALLS": "true",
                "ENABLE_REAL_LLM": "true",
                "LITINERARY_AI_PROVIDER": "fake",
                "LLM_PROVIDER": "openai_compatible",
                "LLM_API_KEY": "offline-test-key",
                "LLM_MODEL_NAME": "offline-test-model",
                "LLM_ALLOWED_ENVIRONMENTS": "development",
                "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS": "development",
            },
            200,
            lambda llm, payload: llm["providerName"] == "openai_compatible",
        ),
        (
            "beta_environment_not_live_allowlisted",
            {
                "APP_ENV": "beta",
                "ALLOW_EXTERNAL_CALLS": "true",
                "ENABLE_REAL_LLM": "true",
                "LITINERARY_AI_PROVIDER": "openai_compatible",
                "LLM_PROVIDER": "openai_compatible",
                "LLM_API_KEY": "offline-test-key",
                "LLM_MODEL_NAME": "offline-test-model",
                "LLM_ALLOWED_ENVIRONMENTS": "development",
                "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS": "development",
            },
            503,
            lambda llm, payload: llm["environmentAllowed"] is False,
        ),
        (
            "internal_environment_missing_staged_gate",
            {
                "APP_ENV": "internal",
                "ALLOW_EXTERNAL_CALLS": "true",
                "ENABLE_REAL_LLM": "true",
                "LITINERARY_AI_PROVIDER": "openai_compatible",
                "LLM_PROVIDER": "openai_compatible",
                "LLM_API_KEY": "offline-test-key",
                "LLM_MODEL_NAME": "offline-test-model",
                "LLM_ALLOWED_ENVIRONMENTS": "internal",
                "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS": "internal",
            },
            500,
            lambda llm, payload: (
                payload["checks"]["externalCalls"]["stagedInternalLlmTestingEnabled"] is False
                and payload["checks"]["externalCalls"]["internalAccessGateEnabled"] is False
            ),
        ),
        (
            "internal_environment_missing_internal_access_gate",
            {
                "APP_ENV": "internal",
                "ALLOW_EXTERNAL_CALLS": "true",
                "ENABLE_REAL_LLM": "true",
                "ENABLE_STAGED_INTERNAL_LLM_TESTING": "true",
                "LITINERARY_AI_PROVIDER": "openai_compatible",
                "LLM_PROVIDER": "openai_compatible",
                "LLM_API_KEY": "offline-test-key",
                "LLM_MODEL_NAME": "offline-test-model",
                "LLM_ALLOWED_ENVIRONMENTS": "internal",
                "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS": "internal",
            },
            500,
            lambda llm, payload: (
                payload["checks"]["externalCalls"]["stagedInternalLlmTestingEnabled"] is True
                and payload["checks"]["externalCalls"]["internalAccessGateEnabled"] is False
            ),
        ),
    ],
)
def test_llm_live_gate_negative_paths_fail_closed_at_endpoint_level(
    non_raising_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    case_name: str,
    env: dict[str, str],
    expected_status: int,
    readiness_assertion,
) -> None:
    _apply_env(monkeypatch, env)

    readiness = non_raising_client.get("/api/readiness")
    assert readiness.status_code == 200
    readiness_payload = readiness.json()
    llm = _provider(readiness_payload["checks"]["providers"], "llm")
    assert readiness_assertion(llm, readiness_payload), case_name
    _assert_no_secret_or_raw_payload(readiness_payload)

    response = _generate_london_sherlock(non_raising_client)

    assert response.status_code == expected_status
    payload = _safe_response_payload(response)
    _assert_no_secret_or_raw_payload(payload)
    if response.status_code == 200:
        itinerary = payload["itinerary"]
        assert itinerary["providerName"] == "mock_ai"
        assert itinerary["generatedByService"] == "mock_ai"
        assert itinerary["provenanceMetadata"]["warnings"] == ["No external LLM call was made."]
    else:
        assert "/v1/chat/completions" not in _dump(payload)


@pytest.mark.parametrize(
    ("case_name", "env"),
    [
        ("enable_real_llm_only", {"ENABLE_REAL_LLM": "true"}),
        (
            "provider_selection_only",
            {
                "LITINERARY_AI_PROVIDER": "openai_compatible",
                "LLM_PROVIDER": "openai_compatible",
            },
        ),
        ("external_calls_only", {"ALLOW_EXTERNAL_CALLS": "true"}),
        (
            "credentials_only",
            {
                "LLM_API_KEY": "offline-test-key",
                "LLM_MODEL_NAME": "offline-test-model",
            },
        ),
        (
            "environment_allowlists_only",
            {
                "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS": "development",
                "LLM_ALLOWED_ENVIRONMENTS": "development",
            },
        ),
        (
            "real_flag_and_provider_without_external_policy",
            {
                "ENABLE_REAL_LLM": "true",
                "LITINERARY_AI_PROVIDER": "openai_compatible",
                "LLM_PROVIDER": "openai_compatible",
            },
        ),
        (
            "provider_and_external_policy_without_real_flag",
            {
                "ALLOW_EXTERNAL_CALLS": "true",
                "LITINERARY_AI_PROVIDER": "openai_compatible",
                "LLM_PROVIDER": "openai_compatible",
            },
        ),
        (
            "real_flag_and_external_policy_without_provider_selection",
            {
                "ENABLE_REAL_LLM": "true",
                "ALLOW_EXTERNAL_CALLS": "true",
            },
        ),
        (
            "provider_credentials_and_allowlists_without_real_flag",
            {
                "LITINERARY_AI_PROVIDER": "openai_compatible",
                "LLM_PROVIDER": "openai_compatible",
                "LLM_API_KEY": "offline-test-key",
                "LLM_MODEL_NAME": "offline-test-model",
                "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS": "development",
                "LLM_ALLOWED_ENVIRONMENTS": "development",
            },
        ),
    ],
)
def test_partial_llm_live_gate_combinations_do_not_activate_live_generation(
    non_raising_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    case_name: str,
    env: dict[str, str],
) -> None:
    _apply_env(monkeypatch, {"APP_ENV": "development", **env})

    readiness = non_raising_client.get("/api/readiness")
    assert readiness.status_code == 200
    _assert_no_secret_or_raw_payload(readiness.json())

    response = _generate_london_sherlock(non_raising_client)

    assert response.status_code in {200, 500, 503}, case_name
    payload = _safe_response_payload(response)
    _assert_no_secret_or_raw_payload(payload)
    if response.status_code == 200:
        itinerary = payload["itinerary"]
        assert itinerary["providerName"] == "mock_ai"
        assert itinerary["generatedByService"] == "mock_ai"
        assert itinerary["provenanceMetadata"]["provider_name"] == "mock_ai"
    else:
        assert "openai_compatible-v1" not in _dump(payload)


@pytest.mark.parametrize(
    ("provider_type", "env"),
    [
        (
            "vector_db",
            {
                "LITINERARY_VECTOR_PROVIDER": "qdrant",
                "VECTOR_DB_PROVIDER": "qdrant",
                "QDRANT_URL": "https://qdrant.example.test",
            },
        ),
        (
            "poi_verification",
            {
                "LITINERARY_POI_VERIFICATION_PROVIDER": "google_places",
                "POI_PROVIDER": "google_places",
                "POI_VERIFICATION_PROVIDER": "google_places",
                "POI_PROVIDER_API_KEY": "offline-test-key",
            },
        ),
        (
            "routing",
            {
                "ROUTING_PROVIDER": "openrouteservice",
                "ROUTING_API_KEY": "offline-test-key",
            },
        ),
        (
            "ticketing",
            {
                "TICKETING_PROVIDER": "real_ticketing",
                "TICKETING_API_KEY": "offline-test-key",
            },
        ),
        (
            "affiliate",
            {
                "AFFILIATE_PROVIDER": "real_affiliate",
                "AFFILIATE_API_KEY": "offline-test-key",
            },
        ),
        (
            "tts",
            {
                "TTS_PROVIDER": "real_tts",
                "TTS_API_KEY": "offline-test-key",
            },
        ),
        (
            "auth",
            {
                "AUTH_PROVIDER": "oidc",
                "AUTH_JWT_ISSUER": "https://auth.example.test/",
                "AUTH_JWT_AUDIENCE": "litinerary-api",
                "AUTH_JWKS_URL": "https://auth.example.test/.well-known/jwks.json",
            },
        ),
    ],
)
def test_other_provider_selection_alone_remains_disabled_in_readiness(
    non_raising_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    provider_type: str,
    env: dict[str, str],
) -> None:
    _apply_env(monkeypatch, {"APP_ENV": "development", **env})

    response = non_raising_client.get("/api/readiness")

    assert response.status_code == 200
    payload = response.json()
    provider = _provider(payload["checks"]["providers"], provider_type)
    assert provider["mode"] == "mock"
    assert provider["realEnabled"] is False
    assert provider["externalCallsAllowed"] is False
    assert provider["status"] == "mock"
    _assert_no_secret_or_raw_payload(payload)


@pytest.mark.parametrize(
    ("provider_type", "env", "expected_status_fragment"),
    [
        (
            "vector_db",
            {
                "ENABLE_REAL_VECTOR_DB": "true",
                "LITINERARY_VECTOR_PROVIDER": "qdrant",
                "VECTOR_DB_PROVIDER": "qdrant",
            },
            "requiredConfigPresent",
        ),
        (
            "poi_verification",
            {
                "ENABLE_REAL_POI_PROVIDER": "true",
                "LITINERARY_POI_VERIFICATION_PROVIDER": "google_places",
                "POI_PROVIDER": "google_places",
                "POI_VERIFICATION_PROVIDER": "google_places",
            },
            "requiredConfigPresent",
        ),
        (
            "routing",
            {
                "ENABLE_REAL_ROUTING": "true",
                "ROUTING_PROVIDER": "openrouteservice",
            },
            "requiredConfigPresent",
        ),
        (
            "ticketing",
            {
                "ENABLE_REAL_TICKETING": "true",
                "TICKETING_PROVIDER": "real_ticketing",
            },
            "requiredConfigPresent",
        ),
        (
            "affiliate",
            {
                "ENABLE_AFFILIATE_LINKS": "true",
                "AFFILIATE_PROVIDER": "real_affiliate",
            },
            "requiredConfigPresent",
        ),
        (
            "tts",
            {
                "ENABLE_REAL_TTS": "true",
                "TTS_PROVIDER": "real_tts",
            },
            "requiredConfigPresent",
        ),
        (
            "auth",
            {
                "ENABLE_AUTH": "true",
                "AUTH_PROVIDER": "oidc",
            },
            "requiredConfigPresent",
        ),
    ],
)
def test_other_provider_real_flags_without_policy_or_config_are_visible_but_not_callable(
    non_raising_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    provider_type: str,
    env: dict[str, str],
    expected_status_fragment: str,
) -> None:
    _apply_env(monkeypatch, {"APP_ENV": "development", **env})

    response = non_raising_client.get("/api/readiness")

    assert response.status_code == 200
    payload = response.json()
    provider = _provider(payload["checks"]["providers"], provider_type)
    assert provider["realEnabled"] is True
    assert provider["externalCallsAllowed"] is False
    assert provider[expected_status_fragment] is False
    _assert_no_secret_or_raw_payload(payload)


def test_provider_fail_closed_integration_no_network_guard_allows_mock_generation(
    non_raising_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _apply_env(monkeypatch, {"APP_ENV": "test"})

    response = _generate_london_sherlock(non_raising_client)

    assert response.status_code == 200
    payload = response.json()
    assert payload["itinerary"]["providerName"] == "mock_ai"
    assert payload["itinerary"]["days"][0]["routingProviderMetadata"]["provider_name"] == (
        "mock_routing"
    )
    _assert_no_secret_or_raw_payload(payload)


def _apply_env(monkeypatch: pytest.MonkeyPatch, env: dict[str, str]) -> None:
    for key in PROVIDER_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("APP_ENV", env.get("APP_ENV", "test"))
    monkeypatch.setenv("ENABLE_MOCK_SERVICES", env.get("ENABLE_MOCK_SERVICES", "true"))
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    _clear_caches()


def _clear_caches() -> None:
    get_settings.cache_clear()
    get_ai_pipeline.cache_clear()
    get_vector_service.cache_clear()
    get_poi_verification_adapter.cache_clear()
    get_routing_provider.cache_clear()
    get_ticketing_provider.cache_clear()
    get_affiliate_provider.cache_clear()
    get_narration_service.cache_clear()


def _generate_london_sherlock(client: TestClient):
    return client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "london",
            "bookId": "sherlock-holmes",
            "durationDays": 1,
            "transportationMode": "walking",
        },
    )


def _provider(providers: list[dict], provider_type: str) -> dict:
    return next(provider for provider in providers if provider["providerType"] == provider_type)


def _safe_response_payload(response) -> object:  # noqa: ANN001
    try:
        return response.json()
    except json.JSONDecodeError:
        return response.text


def _assert_no_secret_or_raw_payload(payload: object) -> None:
    dumped = _dump(payload)
    assert "Authorization" not in dumped
    assert "rawProviderPayload" not in dumped
    assert "raw_provider_payload" not in dumped
    assert "raw_provider_reference" not in dumped
    assert "raw provider payload" not in dumped.lower()
    for pattern in SECRET_LIKE_PATTERNS:
        assert pattern.search(dumped) is None


def _dump(payload: object) -> str:
    if isinstance(payload, str):
        return payload
    return json.dumps(payload, sort_keys=True)
