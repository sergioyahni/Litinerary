import pytest

from app.core.config import get_settings
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
