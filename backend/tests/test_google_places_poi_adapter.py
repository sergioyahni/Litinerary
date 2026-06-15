import pytest

from app.core.config import get_settings
from app.models import BookLocationCandidateModel, POIModel
from app.services.google_places_poi_adapter import (
    GooglePlacesPOIVerificationAdapter,
    GooglePlacesSettings,
)
from app.services.poi_verification import (
    MockPOIVerificationAdapter,
    PlaceSearchQuery,
    apply_verification_result,
    get_poi_verification_adapter,
    validate_poi_provider_startup,
)
from app.services.provider_contracts import ProviderError, ProviderErrorCode


class FakeGooglePlacesTransport:
    def __init__(self, response: dict | None = None, error: ProviderError | None = None) -> None:
        self.response = response or {"places": []}
        self.error = error
        self.calls: list[dict] = []

    def search_text(self, payload: dict, field_mask: str) -> tuple[dict, int]:
        self.calls.append({"payload": payload, "field_mask": field_mask})
        if self.error:
            raise self.error
        return self.response, 12


@pytest.fixture(autouse=True)
def clear_poi_provider_cache():
    get_settings.cache_clear()
    get_poi_verification_adapter.cache_clear()
    yield
    get_settings.cache_clear()
    get_poi_verification_adapter.cache_clear()


def test_mock_adapter_remains_default(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_REAL_POI_PROVIDER", raising=False)
    monkeypatch.delenv("POI_PROVIDER", raising=False)
    monkeypatch.delenv("LITINERARY_POI_VERIFICATION_PROVIDER", raising=False)
    monkeypatch.delenv("POI_VERIFICATION_PROVIDER", raising=False)

    adapter = get_poi_verification_adapter()

    assert isinstance(adapter, MockPOIVerificationAdapter)


def test_google_adapter_selection_requires_real_provider_flag(monkeypatch) -> None:
    monkeypatch.setenv("POI_PROVIDER", "google_places")
    monkeypatch.delenv("ENABLE_REAL_POI_PROVIDER", raising=False)

    with pytest.raises(RuntimeError, match="ENABLE_REAL_POI_PROVIDER"):
        get_poi_verification_adapter()


def test_google_adapter_selection_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_REAL_POI_PROVIDER", "true")
    monkeypatch.setenv("POI_PROVIDER", "google_places")
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "test-key")

    adapter = get_poi_verification_adapter()

    assert isinstance(adapter, GooglePlacesPOIVerificationAdapter)


def test_missing_google_config_fails_clearly_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_REAL_POI_PROVIDER", "true")
    monkeypatch.setenv("POI_PROVIDER", "google_places")
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    monkeypatch.delenv("POI_PROVIDER_API_KEY", raising=False)
    monkeypatch.delenv("POI_VERIFICATION_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="configuration is incomplete"):
        validate_poi_provider_startup()


def test_settings_support_poi_provider_alias_and_threshold(monkeypatch) -> None:
    monkeypatch.setenv("POI_PROVIDER", "google_places")
    monkeypatch.setenv("POI_PROVIDER_MIN_CONFIDENCE", "0.91")

    settings = get_settings()

    assert settings.poi_verification_provider == "google_places"
    assert settings.poi_provider_min_confidence == 0.91


def test_google_search_normalizes_provider_response(db_session) -> None:
    transport = FakeGooglePlacesTransport(
        {
            "places": [
                {
                    "id": "places/smithfield",
                    "displayName": {"text": "Smithfield Market"},
                    "formattedAddress": "Grand Ave, London",
                    "location": {"latitude": 51.5188, "longitude": -0.102},
                    "googleMapsUri": "https://maps.google.com/?cid=smithfield",
                    "regularOpeningHours": {
                        "weekdayDescriptions": ["Monday: 10 AM-5 PM", "Tuesday: 10 AM-5 PM"]
                    },
                    "businessStatus": "OPERATIONAL",
                }
            ]
        }
    )
    adapter = GooglePlacesPOIVerificationAdapter(
        GooglePlacesSettings(api_key="test-key", min_confidence=0.8),
        transport=transport,
    )

    results = adapter.search_places(
        db_session,
        PlaceSearchQuery(
            name="Smithfield Market",
            city_id="london",
            latitude=51.5188,
            longitude=-0.102,
        ),
    )

    assert len(results) == 1
    result = results[0]
    assert result.provider == "google_places"
    assert result.name == "Smithfield Market"
    assert result.address == "Grand Ave, London"
    assert result.confidence == 1.0
    assert result.metadata is not None
    assert result.metadata.raw_provider_reference == "places/smithfield"
    assert "places.id" in transport.calls[0]["field_mask"]
    assert "London" in transport.calls[0]["payload"]["textQuery"]


def test_google_adapter_resolves_candidate_as_provider_verified(db_session) -> None:
    adapter = GooglePlacesPOIVerificationAdapter(
        GooglePlacesSettings(api_key="test-key", min_confidence=0.8),
        transport=FakeGooglePlacesTransport(
            {
                "places": [
                    {
                        "id": "places/smithfield",
                        "displayName": {"text": "Smithfield Market"},
                        "formattedAddress": "Grand Ave, London",
                        "location": {"latitude": 51.5188, "longitude": -0.102},
                        "googleMapsUri": "https://maps.google.com/?cid=smithfield",
                    }
                ]
            }
        ),
    )
    candidate = BookLocationCandidateModel(
        id="google-candidate",
        job_id="contract-job",
        book_id="oliver-twist",
        destination_id="london",
        name="Smithfield Market",
        description="Candidate for real adapter verification.",
        latitude=51.5188,
        longitude=-0.102,
        literary_relevance="Test relevance.",
        confidence=0.9,
        status="candidate",
        created_at="2026-06-12T00:00:00+00:00",
    )

    result = adapter.resolve_candidate(db_session, candidate)

    assert result.status == "provider_verified"
    assert result.metadata is not None
    assert result.metadata.provider_type == "poi_verification"
    assert result.metadata.raw_provider_reference == "places/smithfield"


def test_google_adapter_low_confidence_result_needs_review(db_session) -> None:
    adapter = GooglePlacesPOIVerificationAdapter(
        GooglePlacesSettings(api_key="test-key", min_confidence=0.9),
        transport=FakeGooglePlacesTransport(
            {
                "places": [
                    {
                        "id": "places/other",
                        "displayName": {"text": "Other Landmark"},
                        "formattedAddress": "London",
                        "location": {"latitude": 51.4, "longitude": -0.3},
                    }
                ]
            }
        ),
    )

    result = adapter.verify_poi(db_session, _poi())

    assert result.status == "needs_review"
    assert result.confidence < 0.9
    assert any("below the configured confidence threshold" in note for note in result.notes)
    assert "Low-confidence" in result.metadata.warnings[-1]


def test_google_adapter_no_match_result_needs_review(db_session) -> None:
    adapter = GooglePlacesPOIVerificationAdapter(
        GooglePlacesSettings(api_key="test-key"),
        transport=FakeGooglePlacesTransport({"places": []}),
    )

    result = adapter.verify_poi(db_session, _poi())

    assert result.status == "needs_review"
    assert result.confidence == 0.0
    assert result.verified_name == "Smithfield Market"
    assert "no match" in result.notes[0].lower()


@pytest.mark.parametrize(
    "code",
    [ProviderErrorCode.TIMEOUT, ProviderErrorCode.RATE_LIMITED],
)
def test_google_adapter_normalizes_transport_errors(db_session, code) -> None:
    adapter = GooglePlacesPOIVerificationAdapter(
        GooglePlacesSettings(api_key="test-key"),
        transport=FakeGooglePlacesTransport(
            error=ProviderError(code, f"normalized {code.value}")
        ),
    )

    with pytest.raises(ProviderError) as exc_info:
        adapter.verify_poi(db_session, _poi())

    assert exc_info.value.code == code


def test_apply_google_verification_preserves_metadata_notes_and_manual_review() -> None:
    poi = _poi()
    poi.verification_notes = ["Keep existing reviewer note."]
    poi.manual_review_status = "reviewed"
    result = GooglePlacesPOIVerificationAdapter(
        GooglePlacesSettings(api_key="test-key", min_confidence=0.8),
        transport=FakeGooglePlacesTransport(
            {
                "places": [
                    {
                        "id": "places/smithfield",
                        "displayName": {"text": "Smithfield Market"},
                        "formattedAddress": "Grand Ave, London",
                        "location": {"latitude": 51.5188, "longitude": -0.102},
                        "googleMapsUri": "https://maps.google.com/?cid=smithfield",
                    }
                ]
            }
        ),
    ).verify_poi(_NoDestinationSession(), poi)

    apply_verification_result(poi, result)

    assert poi.verification_status == "provider_verified"
    assert poi.verification_provider == "google_places"
    assert poi.verification_confidence == 1.0
    assert poi.provenance_metadata["externalProviderUsed"] is True
    assert "Keep existing reviewer note." in poi.verification_notes
    assert poi.manual_review_status == "reviewed"


def test_unit_tests_use_fake_transport_without_network(db_session) -> None:
    transport = FakeGooglePlacesTransport({"places": []})
    adapter = GooglePlacesPOIVerificationAdapter(
        GooglePlacesSettings(api_key="test-key"),
        transport=transport,
    )

    adapter.search_places(db_session, PlaceSearchQuery(name="A", city_id="london"))

    assert len(transport.calls) == 1


@pytest.mark.skip(reason="Live Google Places integration requires explicit credentials and opt-in.")
def test_live_google_places_integration_skipped_by_default() -> None:
    pass


class _NoDestinationSession:
    def get(self, model, key):
        return None


def _poi() -> POIModel:
    return POIModel(
        id="smithfield-market",
        destination_id="london",
        name="Smithfield Market",
        description="Temporary test POI.",
        latitude=51.5188,
        longitude=-0.102,
        estimated_duration_minutes=30,
        literary_relevance="Test relevance.",
        verification_status="needs_review",
        verification_notes=[],
    )
