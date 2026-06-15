import pytest

from app.core.config import get_settings
from app.data.mock_data import ITINERARIES
from app.schemas.narration import NarrationRequest
from app.services.narration_service import build_itinerary_narration, get_narration_service
from app.services.provider_contracts import ProviderError


@pytest.fixture(autouse=True)
def clear_narration_caches():
    get_settings.cache_clear()
    get_narration_service.cache_clear()
    yield
    get_settings.cache_clear()
    get_narration_service.cache_clear()


def test_narration_generation_uses_itinerary_days_and_stops() -> None:
    itinerary = next(item for item in ITINERARIES if item.id == "it-london-oliver-twist-1-walking")

    narration = build_itinerary_narration(itinerary)

    assert narration.itineraryId == itinerary.id
    assert narration.format == "text_only"
    assert "Oliver Twist in London" in narration.script.text
    assert "Day 1" in narration.script.text
    assert "Smithfield Market" in narration.script.text
    assert narration.script.providerType == "tts"
    assert narration.audio.available is False


def test_placeholder_audio_metadata_is_explicit_and_local_only() -> None:
    itinerary = next(item for item in ITINERARIES if item.id == "it-london-oliver-twist-1-walking")

    narration = build_itinerary_narration(
        itinerary,
        NarrationRequest(includePlaceholderAudio=True),
    )

    assert narration.format == "placeholder_audio"
    assert narration.audio.available is True
    assert narration.audio.url is None
    assert narration.audio.placeholder is True
    assert "no generated audio file" in narration.audio.warnings[0].lower()


def test_mock_tts_provider_remains_default(monkeypatch) -> None:
    monkeypatch.delenv("TTS_PROVIDER", raising=False)
    monkeypatch.delenv("ENABLE_REAL_TTS", raising=False)
    get_settings.cache_clear()
    get_narration_service.cache_clear()

    settings = get_settings()
    service = get_narration_service()

    assert settings.tts_provider == "mock"
    assert service.__class__.__name__ == "MockNarrationService"


def test_missing_real_tts_config_is_safe(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_REAL_TTS", "true")
    monkeypatch.setenv("TTS_PROVIDER", "future-provider")
    monkeypatch.delenv("TTS_API_KEY", raising=False)
    get_settings.cache_clear()
    get_narration_service.cache_clear()

    settings = get_settings()

    assert any("TTS_API_KEY" in note for note in settings.startup_validation_notes())
    with pytest.raises(ProviderError):
        get_narration_service()


def test_narration_api_endpoints_return_text_fallback(client) -> None:
    get_response = client.get("/api/itineraries/it-london-oliver-twist-1-walking/narration")
    post_response = client.post(
        "/api/itineraries/it-london-oliver-twist-1-walking/narration",
        json={"voiceStyle": "warm_literary", "includePlaceholderAudio": True},
    )

    assert get_response.status_code == 200
    assert get_response.json()["format"] == "text_only"
    assert "Smithfield Market" in get_response.json()["script"]["text"]
    assert post_response.status_code == 200
    assert post_response.json()["audio"]["placeholder"] is True
