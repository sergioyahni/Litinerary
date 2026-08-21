import pytest

from app.core.config import get_settings
from app.core.readiness import provider_status
from app.services.mock_ai_service import get_ai_pipeline
from app.services.poi_verification import get_poi_verification_adapter
from app.services.vector_service import get_vector_service


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    get_ai_pipeline.cache_clear()
    get_vector_service.cache_clear()
    get_poi_verification_adapter.cache_clear()
    yield
    get_settings.cache_clear()
    get_ai_pipeline.cache_clear()
    get_vector_service.cache_clear()
    get_poi_verification_adapter.cache_clear()


def test_admin_routes_work_in_development_by_default(client, monkeypatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENABLE_ADMIN_ROUTES", raising=False)
    get_settings.cache_clear()

    response = client.get("/api/admin/seed/validate")

    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_admin_routes_are_blocked_in_production_by_default(client, monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ENABLE_ADMIN_ROUTES", raising=False)
    get_settings.cache_clear()

    response = client.get("/api/admin/seed/validate")

    assert response.status_code == 403
    assert "disabled" in response.json()["detail"]


def test_non_destructive_admin_route_can_be_explicitly_enabled_in_production(
    client,
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENABLE_ADMIN_ROUTES", "true")
    get_settings.cache_clear()

    response = client.get("/api/admin/seed/validate")

    assert response.status_code == 200


def test_destructive_seed_routes_are_blocked_in_production_even_when_admin_enabled(
    client,
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENABLE_ADMIN_ROUTES", "true")
    get_settings.cache_clear()

    reset_response = client.post("/api/admin/seed/reset")
    export_response = client.get("/api/admin/seed/export")

    assert reset_response.status_code == 403
    assert "Destructive" in reset_response.json()["detail"]
    assert export_response.status_code == 200


def test_debug_routes_are_blocked_in_production_by_default(client, monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ENABLE_DEBUG_ROUTES", raising=False)
    get_settings.cache_clear()

    response = client.get("/api/users/dev-reader/recommendations/mock")

    assert response.status_code == 403
    assert "Debug endpoints are disabled" in response.json()["detail"]


def test_beta_environment_defaults_are_deployment_safe(client, monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "beta")
    monkeypatch.delenv("ENABLE_ADMIN_ROUTES", raising=False)
    monkeypatch.delenv("ENABLE_DEBUG_ROUTES", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)
    get_settings.cache_clear()

    settings = get_settings()
    admin_response = client.get("/api/admin/seed/validate")
    debug_response = client.get("/api/users/dev-reader/recommendations/mock")

    assert settings.app_env == "beta"
    assert settings.debug is False
    assert settings.enable_admin_routes is False
    assert settings.enable_debug_routes is False
    assert settings.enable_mock_services is False
    assert admin_response.status_code == 403
    assert debug_response.status_code == 403


def test_internal_environment_defaults_are_deployment_safe(client, monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "internal")
    monkeypatch.delenv("ENABLE_ADMIN_ROUTES", raising=False)
    monkeypatch.delenv("ENABLE_DEBUG_ROUTES", raising=False)
    monkeypatch.delenv("ENABLE_STAGED_INTERNAL_LLM_TESTING", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)
    get_settings.cache_clear()

    settings = get_settings()
    admin_response = client.get("/api/admin/seed/validate")
    debug_response = client.get("/api/users/dev-reader/recommendations/mock")

    assert settings.app_env == "internal"
    assert settings.debug is False
    assert settings.enable_admin_routes is False
    assert settings.enable_debug_routes is False
    assert settings.enable_mock_services is False
    assert settings.enable_staged_internal_llm_testing is False
    assert settings.enable_internal_access_gate is False
    assert admin_response.status_code == 403
    assert debug_response.status_code == 403


def test_cors_wildcard_is_ignored_in_production(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*,https://litinerary.example")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.cors_allowed_origins == ["https://litinerary.example"]
    assert "*" not in settings.cors_allowed_origins


def test_missing_provider_keys_do_not_break_local_mock_services(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("VECTOR_DB_API_KEY", raising=False)
    monkeypatch.delenv("POI_VERIFICATION_API_KEY", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.enable_mock_services is True
    assert settings.startup_validation_notes() == []
    assert get_ai_pipeline() is not None
    assert get_vector_service() is not None
    assert get_poi_verification_adapter() is not None


def test_missing_real_provider_keys_create_startup_notes_without_crashing(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("VECTOR_DB_PROVIDER", "qdrant")
    monkeypatch.setenv("POI_VERIFICATION_PROVIDER", "google_places")
    get_settings.cache_clear()

    notes = get_settings().startup_validation_notes()

    assert any("LLM provider 'openai'" in note for note in notes)
    assert any("Vector DB provider 'qdrant'" in note for note in notes)
    assert any("POI verification provider 'google_places'" in note for note in notes)


def test_plu03_staging_auth_allows_only_auth0_external_calls(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("ENABLE_ADMIN_ROUTES", "false")
    monkeypatch.setenv("ENABLE_DEBUG_ROUTES", "false")
    monkeypatch.setenv("ENABLE_MOCK_SERVICES", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS", "staging")
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "auth0")
    monkeypatch.setenv("AUTH_REQUIRED_FOR_USER_FEATURES", "true")
    monkeypatch.setenv("AUTH_ALLOW_DEV_USER_FALLBACK", "false")
    monkeypatch.setenv("AUTH_JWT_ISSUER", "https://auth0-staging.example.test/")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "litinerary-staging-api")
    monkeypatch.setenv("AUTH_JWT_ALGORITHMS", "RS256")
    monkeypatch.setenv("AUTH_JWKS_URL", "https://auth0-staging.example.test/.well-known/jwks.json")
    monkeypatch.setenv(
        "AUTH_PROVIDER_METADATA_URL",
        "https://auth0-staging.example.test/.well-known/openid-configuration",
    )
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://staging.litinerary.example")
    monkeypatch.setenv("LITINERARY_DATABASE_URL", "postgresql://user:pass@db.example.test:5432/app")
    monkeypatch.setenv("ENABLE_DURABLE_USAGE_CONTROLS", "true")
    monkeypatch.setenv("ENABLE_REAL_LLM", "false")
    monkeypatch.setenv("ENABLE_REAL_VECTOR_DB", "false")
    monkeypatch.setenv("ENABLE_REAL_POI_PROVIDER", "false")
    monkeypatch.setenv("ENABLE_REAL_ROUTING", "false")
    monkeypatch.setenv("ENABLE_REAL_TICKETING", "false")
    monkeypatch.setenv("ENABLE_REAL_TTS", "false")
    monkeypatch.setenv("ENABLE_AFFILIATE_LINKS", "false")
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
    monkeypatch.setenv("PROVIDER_DAILY_COST_CEILING_USD", "0")
    get_settings.cache_clear()

    settings = get_settings()
    providers = provider_status(settings)

    assert settings.startup_validation_notes() == []
    auth = _provider(providers, "auth")
    assert auth["providerName"] == "auth0"
    assert auth["mode"] == "real"
    assert auth["externalCallsAllowed"] is True
    for provider in providers:
        if provider["providerType"] == "auth":
            continue
        assert provider["mode"] == "mock"
        assert provider["realEnabled"] is False
        assert provider["externalCallsAllowed"] is False


def _provider(providers: list[dict], provider_type: str) -> dict:
    return next(provider for provider in providers if provider["providerType"] == provider_type)
