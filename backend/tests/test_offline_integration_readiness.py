import json
import re

import pytest

from app.core.config import get_settings
from app.services.mock_ai_service import get_ai_pipeline
from app.services.poi_verification import get_poi_verification_adapter
from app.services.routing_service import get_routing_provider
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
    "TICKING_API_KEY",
    "TICKETING_API_KEY",
    "AFFILIATE_PROVIDER",
    "AFFILIATE_API_KEY",
    "TTS_PROVIDER",
    "TTS_API_KEY",
    "TEXT_TO_SPEECH_API_KEY",
    "AUTH_JWT_ISSUER",
    "AUTH_JWT_AUDIENCE",
    "AUTH_JWKS_URL",
    "AUTH_PROVIDER_METADATA_URL",
]


@pytest.fixture(autouse=True)
def clear_provider_caches():
    _clear_caches()
    yield
    _clear_caches()


def test_offline_readiness_defaults_are_mock_only_and_secret_free(client, monkeypatch) -> None:
    _force_offline_env(monkeypatch, app_env="test")

    health_response = client.get("/api/health")
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    _assert_no_secret_or_raw_payload(health_response.json())

    response = client.get("/api/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["appEnv"] == "test"
    assert payload["checks"]["database"]["status"] == "ok"
    assert payload["checks"]["externalCalls"] == {
        "allowed": False,
        "integrationTestsEnabled": False,
        "stagedInternalLlmTestingEnabled": False,
        "internalAccessGateEnabled": False,
    }

    providers = payload["checks"]["providers"]
    assert providers
    for provider in providers:
        assert provider["mode"] == "mock"
        assert provider["realEnabled"] is False
        assert provider["externalCallsAllowed"] is False

    llm = _provider(providers, "llm")
    assert llm["providerName"] == "fake"
    assert llm["credentialsConfigured"] is False
    assert llm["environmentAllowed"] is False
    assert "openai_compatible" not in json.dumps(payload)
    _assert_no_secret_or_raw_payload(payload)


@pytest.mark.parametrize("app_env", ["internal", "beta", "production"])
def test_deployed_profiles_do_not_enable_live_llm_without_explicit_gates(
    client,
    monkeypatch,
    app_env: str,
) -> None:
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", app_env)
    _clear_caches()

    response = client.get("/api/readiness")

    assert response.status_code == 200
    payload = response.json()
    llm = _provider(payload["checks"]["providers"], "llm")
    assert llm["providerName"] == "fake"
    assert llm["mode"] == "mock"
    assert llm["realEnabled"] is False
    assert payload["checks"]["externalCalls"]["allowed"] is False
    assert payload["checks"]["externalCalls"]["stagedInternalLlmTestingEnabled"] is False
    assert payload["checks"]["externalCalls"]["internalAccessGateEnabled"] is False
    _assert_no_secret_or_raw_payload(payload)


def test_internal_profile_with_openai_config_still_requires_live_gates(
    client,
    monkeypatch,
) -> None:
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "internal")
    monkeypatch.setenv("LITINERARY_AI_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    _clear_caches()

    response = client.get("/api/readiness")

    assert response.status_code == 200
    payload = response.json()
    llm = _provider(payload["checks"]["providers"], "llm")
    assert llm["providerName"] == "openai_compatible"
    assert llm["mode"] == "mock"
    assert llm["realEnabled"] is False
    assert llm["credentialsConfigured"] is False
    assert payload["checks"]["externalCalls"]["allowed"] is False
    assert payload["checks"]["externalCalls"]["stagedInternalLlmTestingEnabled"] is False
    assert payload["checks"]["externalCalls"]["internalAccessGateEnabled"] is False
    _assert_no_secret_or_raw_payload(payload)


def test_seed_reset_validate_and_london_sherlock_seed_data(
    client,
    monkeypatch,
) -> None:
    _force_offline_env(monkeypatch, app_env="development")

    reset_response = client.post("/api/admin/seed/reset")
    assert reset_response.status_code == 200
    reset_payload = reset_response.json()
    assert reset_payload["counts"]["destinations"] >= 5
    assert reset_payload["counts"]["books"] >= 10
    assert reset_payload["counts"]["pois"] >= 13
    assert reset_payload["counts"]["itineraries"] >= 2

    validation_response = client.get("/api/admin/seed/validate")
    assert validation_response.status_code == 200
    validation_payload = validation_response.json()
    assert validation_payload["valid"] is True
    assert validation_payload["errors"] == []

    export_response = client.get("/api/admin/seed/export")
    assert export_response.status_code == 200
    seed_payload = export_response.json()
    assert any(destination["id"] == "london" for destination in seed_payload["destinations"])
    sherlock = _by_id(seed_payload["books"], "sherlock-holmes")
    assert "london" in sherlock["destinationIds"]
    baker_street = _by_id(seed_payload["pois"], "baker-street")
    assert baker_street["destinationId"] == "london"
    assert "sherlock-holmes" in baker_street["bookIds"]
    assert baker_street["name"] == "Baker Street"
    assert baker_street["verificationNotes"]
    assert baker_street["provenanceMetadata"]
    assert baker_street["provenanceMetadata"]["externalProviderUsed"] is False
    _assert_no_secret_or_raw_payload(seed_payload)


@pytest.mark.parametrize("app_env", ["internal", "beta", "production"])
def test_seed_admin_endpoints_are_blocked_outside_local_test_defaults(
    client,
    monkeypatch,
    app_env: str,
) -> None:
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.delenv("ENABLE_ADMIN_ROUTES", raising=False)
    _clear_caches()

    validate_response = client.get("/api/admin/seed/validate")
    reset_response = client.post("/api/admin/seed/reset")

    assert validate_response.status_code == 403
    assert reset_response.status_code == 403


def test_mocked_london_sherlock_generation_stays_offline_and_grounded(
    client,
    monkeypatch,
) -> None:
    _force_offline_env(monkeypatch, app_env="test")

    response = client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "london",
            "bookId": "sherlock-holmes",
            "durationDays": 1,
            "transportationMode": "walking",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    itinerary = payload["itinerary"]
    assert payload["matchedExisting"] is False
    assert itinerary["destinationId"] == "london"
    assert itinerary["bookId"] == "sherlock-holmes"
    assert itinerary["durationDays"] == 1
    assert itinerary["transportationMode"] == "walking"
    assert itinerary["generatedFrom"] == "new_generation"
    assert itinerary["sourceType"] == "new_mock_generation"
    assert itinerary["providerName"] == "mock_ai"
    assert itinerary["providerType"] == "llm"
    assert itinerary["generatedByService"] == "mock_ai"
    assert itinerary["provenanceMetadata"]["provider_name"] == "mock_ai"
    assert itinerary["provenanceMetadata"]["warnings"] == ["No external LLM call was made."]
    assert itinerary["days"]

    stops = [
        stop
        for day in itinerary["days"]
        for stop in day["stops"]
    ]
    assert stops
    baker_street = next(stop for stop in stops if stop["poi"]["id"] == "baker-street")
    assert baker_street["poi"]["name"] == "Baker Street"
    assert baker_street["poi"]["verificationNotes"]
    assert baker_street["poi"]["provenanceMetadata"]["externalProviderUsed"] is False

    first_day = itinerary["days"][0]
    assert first_day["routingProviderMetadata"]["provider_name"] == "mock_routing"
    assert first_day["routingProviderMetadata"]["warnings"] == [
        "No external routing provider call was made."
    ]
    assert any("Mock routing" in warning for warning in first_day["routingWarnings"])

    dumped = json.dumps(payload)
    assert "openai_compatible" not in dumped
    assert "/v1/chat/completions" not in dumped
    _assert_no_secret_or_raw_payload(payload)


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        ({"bookId": "sherlock-holmes", "durationDays": 1, "transportationMode": "walking"}, 422),
        ({"destinationId": "london", "durationDays": 1, "transportationMode": "walking"}, 422),
        (
            {
                "destinationId": "london",
                "bookId": "les-miserables",
                "durationDays": 1,
                "transportationMode": "walking",
            },
            400,
        ),
        (
            {
                "destinationId": "london",
                "bookId": "sherlock-holmes",
                "durationDays": 0,
                "transportationMode": "walking",
            },
            422,
        ),
        (
            {
                "destinationId": "london",
                "bookId": "sherlock-holmes",
                "durationDays": 1,
                "transportationMode": "hoverboard",
            },
            422,
        ),
        ({}, 422),
    ],
)
def test_invalid_itinerary_generation_requests_fail_safely(
    client,
    monkeypatch,
    payload: dict,
    expected_status: int,
) -> None:
    _force_offline_env(monkeypatch, app_env="test")

    response = client.post("/api/itinerary/generate", json=payload)

    assert response.status_code == expected_status
    _assert_no_secret_or_raw_payload(response.json())


def test_malformed_itinerary_generation_json_fails_safely(client, monkeypatch) -> None:
    _force_offline_env(monkeypatch, app_env="test")

    response = client.post(
        "/api/itinerary/generate",
        content="{",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    _assert_no_secret_or_raw_payload(response.json())


def _force_offline_env(monkeypatch: pytest.MonkeyPatch, *, app_env: str) -> None:
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("ENABLE_MOCK_SERVICES", "true")
    monkeypatch.setenv("LITINERARY_AI_PROVIDER", "fake")
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("LITINERARY_VECTOR_PROVIDER", "fake")
    monkeypatch.setenv("VECTOR_DB_PROVIDER", "fake")
    monkeypatch.setenv("LITINERARY_POI_VERIFICATION_PROVIDER", "mock")
    monkeypatch.setenv("POI_PROVIDER", "mock")
    monkeypatch.setenv("ROUTING_PROVIDER", "mock")
    monkeypatch.setenv("TICKETING_PROVIDER", "mock")
    monkeypatch.setenv("AFFILIATE_PROVIDER", "mock")
    monkeypatch.setenv("TTS_PROVIDER", "mock")
    _clear_caches()


def _clear_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in PROVIDER_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _clear_caches() -> None:
    get_settings.cache_clear()
    get_ai_pipeline.cache_clear()
    get_vector_service.cache_clear()
    get_poi_verification_adapter.cache_clear()
    get_routing_provider.cache_clear()


def _provider(providers: list[dict], provider_type: str) -> dict:
    return next(provider for provider in providers if provider["providerType"] == provider_type)


def _by_id(items: list[dict], item_id: str) -> dict:
    return next(item for item in items if item["id"] == item_id)


def _assert_no_secret_or_raw_payload(payload: object) -> None:
    dumped = json.dumps(payload, sort_keys=True)
    assert "Authorization" not in dumped
    assert "rawProviderPayload" not in dumped
    assert "raw_provider_payload" not in dumped
    for pattern in SECRET_LIKE_PATTERNS:
        assert pattern.search(dumped) is None
