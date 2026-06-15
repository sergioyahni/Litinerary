import pytest

from app.core.config import get_settings
from app.services.mock_ai_service import get_ai_pipeline


SUBSCRIBER_HEADERS = {
    "Authorization": "Bearer dev:sub-reader:user,subscriber:active",
}
USER_HEADERS = {
    "Authorization": "Bearer dev:regular-reader:user:none",
}


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    get_ai_pipeline.cache_clear()
    yield
    get_settings.cache_clear()
    get_ai_pipeline.cache_clear()


def test_subscriber_can_create_and_list_chat_session(client, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_AUTH", "true")
    get_settings.cache_clear()

    create_response = client.post(
        "/api/subscribers/chat/sessions",
        json={"title": "Dickens refinement"},
        headers=SUBSCRIBER_HEADERS,
    )
    list_response = client.get(
        "/api/subscribers/chat/sessions",
        headers=SUBSCRIBER_HEADERS,
    )

    assert create_response.status_code == 201
    session = create_response.json()
    assert session["userId"] == "sub-reader"
    assert session["title"] == "Dickens refinement"
    assert session["messages"][0]["role"] == "assistant"
    assert session["provenanceMetadata"]["mockOnly"] is True
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [session["id"]]


def test_non_subscriber_cannot_access_chat_when_auth_enabled(client, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_AUTH", "true")
    get_settings.cache_clear()

    response = client.post(
        "/api/subscribers/chat/sessions",
        json={"title": "Locked"},
        headers=USER_HEADERS,
    )

    assert response.status_code == 403
    assert "Subscriber access is required" in response.json()["detail"]


def test_anonymous_user_cannot_access_chat_when_auth_enabled(client, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("AUTH_ALLOW_DEV_USER_FALLBACK", "false")
    get_settings.cache_clear()

    response = client.get("/api/subscribers/chat/sessions")

    assert response.status_code == 401
    assert "Authentication is required" in response.json()["detail"]


def test_mock_chat_message_flow(client, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_AUTH", "true")
    get_settings.cache_clear()
    session = client.post(
        "/api/subscribers/chat/sessions",
        json={"title": "Pacing"},
        headers=SUBSCRIBER_HEADERS,
    ).json()

    response = client.post(
        f"/api/subscribers/chat/sessions/{session['id']}/messages",
        json={"content": "Make this slower and add more context."},
        headers=SUBSCRIBER_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert [message["role"] for message in payload["messages"]] == ["user", "assistant"]
    assert "Mock subscriber assistant" in payload["messages"][1]["content"]
    assert payload["messages"][1]["providerName"] == "mock_ai"


def test_mock_itinerary_refinement_creates_private_subscriber_reference(
    client,
    monkeypatch,
) -> None:
    monkeypatch.setenv("ENABLE_AUTH", "true")
    get_settings.cache_clear()
    session = client.post(
        "/api/subscribers/chat/sessions",
        json={"title": "Refine route"},
        headers=SUBSCRIBER_HEADERS,
    ).json()

    response = client.post(
        f"/api/subscribers/chat/sessions/{session['id']}/refine-itinerary",
        json={
            "sourceItineraryId": "it-london-oliver-twist-1-walking",
            "prompt": "Prefer a quieter afternoon route.",
            "durationDays": 1,
            "transportationMode": "walking",
        },
        headers=SUBSCRIBER_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    itinerary = payload["itinerary"]
    assert itinerary["isPublic"] is False
    assert itinerary["visibility"] == "private"
    assert itinerary["subscriberOnly"] is True
    assert itinerary["ownerUserId"] == "sub-reader"
    assert itinerary["createdByMode"] == "subscriber"
    assert itinerary["generatedByService"] == "mock_ai_subscriber_chat"
    assert payload["reference"]["itineraryId"] == itinerary["id"]
    assert payload["reference"]["sourceItineraryId"] == "it-london-oliver-twist-1-walking"
    assert payload["message"]["role"] == "assistant"


def test_users_cannot_read_each_others_chat_sessions(client, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_AUTH", "true")
    get_settings.cache_clear()
    session = client.post(
        "/api/subscribers/chat/sessions",
        json={"title": "Owned"},
        headers=SUBSCRIBER_HEADERS,
    ).json()

    other_headers = {
        "Authorization": "Bearer dev:other-reader:user,subscriber:active",
    }
    response = client.get(
        f"/api/subscribers/chat/sessions/{session['id']}",
        headers=other_headers,
    )

    assert response.status_code == 404
