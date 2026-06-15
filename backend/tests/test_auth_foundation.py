import pytest

from app.core.auth import CurrentUser, require_admin_user, require_subscriber_user, validate_auth_startup
from app.core.config import get_settings


@pytest.fixture(autouse=True)
def clear_auth_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_anonymous_public_access_still_works_when_auth_enabled(client, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("AUTH_REQUIRED_FOR_USER_FEATURES", "true")
    monkeypatch.setenv("AUTH_ALLOW_DEV_USER_FALLBACK", "false")
    get_settings.cache_clear()

    destinations = client.get("/api/destinations")
    books = client.get("/api/books", params={"city_id": "london"})
    generated = client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "london",
            "bookId": "oliver-twist",
            "durationDays": 1,
            "transportationMode": "walking",
        },
    )

    assert destinations.status_code == 200
    assert books.status_code == 200
    assert generated.status_code == 200


def test_user_endpoint_requires_auth_when_auth_enabled(client, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("AUTH_REQUIRED_FOR_USER_FEATURES", "true")
    monkeypatch.setenv("AUTH_ALLOW_DEV_USER_FALLBACK", "false")
    get_settings.cache_clear()

    response = client.get("/api/users/dev-reader")

    assert response.status_code == 401
    assert "Authentication is required" in response.json()["detail"]


def test_development_user_fallback_works_only_in_development(client, monkeypatch) -> None:
    client.post("/api/users", json={"id": "dev-reader"})
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("AUTH_REQUIRED_FOR_USER_FEATURES", "true")
    monkeypatch.setenv("AUTH_ALLOW_DEV_USER_FALLBACK", "true")
    get_settings.cache_clear()

    response = client.get("/api/users/dev-reader")

    assert response.status_code == 200
    assert response.json()["id"] == "dev-reader"


def test_development_fallback_is_not_allowed_in_production(client, monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("AUTH_REQUIRED_FOR_USER_FEATURES", "true")
    monkeypatch.setenv("AUTH_ALLOW_DEV_USER_FALLBACK", "true")
    get_settings.cache_clear()

    response = client.get("/api/users/dev-reader")

    assert response.status_code == 401


def test_dev_token_allows_matching_user_feature_access(client, monkeypatch) -> None:
    client.post("/api/users", json={"id": "dev-reader"})
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("AUTH_REQUIRED_FOR_USER_FEATURES", "true")
    monkeypatch.setenv("AUTH_ALLOW_DEV_USER_FALLBACK", "false")
    get_settings.cache_clear()

    response = client.post(
        "/api/users/dev-reader/preferences",
        json={"key": "travel", "value": {"pace": "slow"}},
        headers={"Authorization": "Bearer dev:dev-reader:user:none"},
    )

    assert response.status_code == 200
    assert response.json()["userId"] == "dev-reader"


def test_invalid_or_mismatched_tokens_are_rejected(client, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("AUTH_REQUIRED_FOR_USER_FEATURES", "true")
    monkeypatch.setenv("AUTH_ALLOW_DEV_USER_FALLBACK", "false")
    get_settings.cache_clear()

    invalid = client.get(
        "/api/users/dev-reader",
        headers={"Authorization": "Bearer not-a-dev-token"},
    )
    mismatched = client.get(
        "/api/users/dev-reader",
        headers={"Authorization": "Bearer dev:other-reader:user:none"},
    )

    assert invalid.status_code == 401
    assert mismatched.status_code == 403


def test_auth_enabled_user_creation_uses_current_user_identity(client, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("AUTH_REQUIRED_FOR_USER_FEATURES", "true")
    monkeypatch.setenv("AUTH_ALLOW_DEV_USER_FALLBACK", "false")
    get_settings.cache_clear()

    created = client.post(
        "/api/users",
        json={"displayName": "Token Reader"},
        headers={"Authorization": "Bearer dev:token-reader:user:none"},
    )
    forbidden = client.post(
        "/api/users",
        json={"id": "someone-else"},
        headers={"Authorization": "Bearer dev:token-reader:user:none"},
    )

    assert created.status_code == 201
    assert created.json()["id"] == "token-reader"
    assert forbidden.status_code == 403


def test_role_and_subscriber_checks_return_403_for_insufficient_access() -> None:
    user = CurrentUser(id="reader", auth_provider="dev", auth_subject="reader", roles={"user"})

    with pytest.raises(Exception) as admin_error:
        require_admin_user(user)
    with pytest.raises(Exception) as subscriber_error:
        require_subscriber_user(user)

    assert getattr(admin_error.value, "status_code") == 403
    assert getattr(subscriber_error.value, "status_code") == 403


def test_production_auth_startup_validation_fails_when_config_incomplete(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "dev")
    monkeypatch.delenv("AUTH_JWT_ISSUER", raising=False)
    monkeypatch.delenv("AUTH_JWT_AUDIENCE", raising=False)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="Production auth is enabled"):
        validate_auth_startup()
