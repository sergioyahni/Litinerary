from app.core.config import get_settings
from app.core.release import release_payload, release_sha


def test_release_sha_uses_render_commit(monkeypatch) -> None:
    monkeypatch.setenv("RENDER_GIT_COMMIT", "ABCDEF1234567890abcdef1234567890abcdef12")
    monkeypatch.setenv("APP_RELEASE_SHA", "1111111")

    assert release_sha() == "abcdef1234567890abcdef1234567890abcdef12"


def test_release_sha_falls_back_to_unknown_for_unsafe_values(monkeypatch) -> None:
    monkeypatch.setenv("RENDER_GIT_COMMIT", "https://example.test/secret")
    monkeypatch.delenv("APP_RELEASE_SHA", raising=False)
    monkeypatch.delenv("GITHUB_SHA", raising=False)

    assert release_sha() == "unknown"


def test_release_payload_contains_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("APP_RELEASE_SHA", "1234567890abcdef1234567890abcdef12345678")
    get_settings.cache_clear()

    payload = release_payload()

    assert payload == {
        "releaseSha": "1234567890abcdef1234567890abcdef12345678",
        "environment": "staging",
    }


def test_version_endpoint_is_safe(client, monkeypatch) -> None:
    monkeypatch.setenv("APP_RELEASE_SHA", "abcdef1234567890abcdef1234567890abcdef12")
    get_settings.cache_clear()

    response = client.get("/api/version")

    assert response.status_code == 200
    assert response.json()["releaseSha"] == "abcdef1234567890abcdef1234567890abcdef12"
    assert set(response.json()) == {"releaseSha", "environment"}
