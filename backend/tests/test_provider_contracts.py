import pytest

from app.core.config import get_settings
from app.data.mock_data import BOOKS, DESTINATIONS, POIS
from app.models import BookLocationCandidateModel
from app.services.mock_ai_service import get_ai_pipeline
from app.services.narration_service import get_narration_service
from app.services.poi_verification import get_poi_verification_adapter
from app.services.provider_contracts import (
    ProviderError,
    ProviderErrorCode,
    ProviderMetadata,
    ProviderType,
)
from app.services.routing_service import get_routing_provider
from app.services.routing_types import RoutePoint, RouteRequest
from app.services.affiliate_service import get_affiliate_provider
from app.services.affiliate_types import AffiliateProductRequest
from app.services.ticketing_service import get_ticketing_provider
from app.services.ticketing_types import (
    TicketAvailabilityRequest,
    TicketingRequest,
    TicketingSearchRequest,
    TicketingUrlRequest,
    TourBookingRequest,
)
from app.services.vector_service import get_vector_service
from app.services.vector_types import VectorCollection


@pytest.fixture(autouse=True)
def clear_provider_caches():
    get_settings.cache_clear()
    get_ai_pipeline.cache_clear()
    get_vector_service.cache_clear()
    get_poi_verification_adapter.cache_clear()
    get_routing_provider.cache_clear()
    get_ticketing_provider.cache_clear()
    get_affiliate_provider.cache_clear()
    get_narration_service.cache_clear()
    yield
    get_settings.cache_clear()
    get_ai_pipeline.cache_clear()
    get_vector_service.cache_clear()
    get_poi_verification_adapter.cache_clear()
    get_routing_provider.cache_clear()
    get_ticketing_provider.cache_clear()
    get_affiliate_provider.cache_clear()
    get_narration_service.cache_clear()


def test_provider_metadata_redacts_raw_reference_from_public_dict() -> None:
    metadata = ProviderMetadata(
        provider_name="provider",
        provider_type=ProviderType.LLM,
        raw_provider_reference="sensitive-raw-payload",
        warnings=["safe warning"],
    )

    public = metadata.public_dict()

    assert public["provider_name"] == "provider"
    assert public["warnings"] == ["safe warning"]
    assert "raw_provider_reference" not in public


def test_provider_error_normalizes_error_payload() -> None:
    error = ProviderError(
        ProviderErrorCode.RATE_LIMITED,
        "Provider rate limit exceeded.",
        metadata=ProviderMetadata.mock(
            provider_name="mock",
            provider_type=ProviderType.LLM,
        ),
        retry_after_seconds=60,
    )

    payload = error.to_dict()

    assert payload["code"] == "rate_limited"
    assert payload["message"] == "Provider rate limit exceeded."
    assert payload["metadata"]["provider_name"] == "mock"
    assert payload["retryAfterSeconds"] == 60


def test_mock_ai_pipeline_results_include_provider_metadata() -> None:
    pipeline = get_ai_pipeline()
    book = next(item for item in BOOKS if item.id == "oliver-twist")
    destination = next(item for item in DESTINATIONS if item.id == "london")
    pois = [poi for poi in POIS if poi.destinationId == "london" and book.id in poi.bookIds]

    source = pipeline.book_ingestion.ingest_book(book)
    locations = pipeline.summary_location_extraction.extract_summary_and_locations(book, source)
    extracted = pipeline.poi_extraction.extract_pois(book, destination, locations, pois)

    assert source.metadata is not None
    assert source.metadata.provider_type == "llm"
    assert locations.metadata is not None
    assert extracted.metadata is not None


def test_vector_records_include_embedding_provider_metadata() -> None:
    service = get_vector_service()

    record = service.upsert_text(
        VectorCollection.ITINERARIES,
        "contract-vector",
        "A test vector record.",
        {"destination_id": "london"},
    )

    assert record.provider_metadata is not None
    assert record.provider_metadata.provider_type == "embedding"
    assert record.provider_metadata.embedding_dimension == 16
    assert record.provider_metadata.model_name == "sha256-token-normalized"


def test_poi_verification_result_includes_provider_metadata(db_session) -> None:
    candidate = BookLocationCandidateModel(
        id="contract-candidate",
        job_id="contract-job",
        book_id="oliver-twist",
        destination_id="london",
        name="Smithfield Market",
        description="Candidate for contract verification.",
        latitude=51.5188,
        longitude=-0.102,
        literary_relevance="Mock relevance.",
        confidence=0.9,
        status="candidate",
        created_at="2026-06-12T00:00:00+00:00",
    )

    result = get_poi_verification_adapter().resolve_candidate(db_session, candidate)

    assert result.metadata is not None
    assert result.metadata.provider_type == "poi_verification"
    assert result.metadata.confidence_score == result.confidence
    assert result.metadata.raw_provider_reference is None


def test_mock_routing_provider_satisfies_route_contract() -> None:
    provider = get_routing_provider()

    plan = provider.plan_route(
        RouteRequest(
            points=[
                RoutePoint(id="a", name="A", latitude=51.5, longitude=-0.1),
                RoutePoint(id="b", name="B", latitude=51.51, longitude=-0.11),
            ],
            transportation_mode="walking",
        )
    )

    assert plan.feasible is True
    assert len(plan.segments) == 1
    assert plan.metadata is not None
    assert plan.metadata.provider_type == "routing"


def test_mock_ticketing_provider_satisfies_ticketing_contract() -> None:
    provider = get_ticketing_provider()

    search_options = provider.search_ticketing_options(
        TicketingSearchRequest(query="Smithfield Market", destination_id="london")
    )
    availability = provider.lookup_availability(
        TicketAvailabilityRequest(
            poi_id="smithfield-market",
            poi_name="Smithfield Market",
            destination_id="london",
        )
    )
    ticketing_link = provider.lookup_ticketing_url(
        TicketingUrlRequest(
            poi_id="smithfield-market",
            poi_name="Smithfield Market",
            destination_id="london",
        )
    )
    tour_link = provider.lookup_tour_booking_url(
        TourBookingRequest(
            poi_id="smithfield-market",
            poi_name="Smithfield Market",
            destination_id="london",
        )
    )
    options = provider.find_ticketing_options(
        TicketingRequest(
            poi_id="smithfield-market",
            poi_name="Smithfield Market",
            destination_id="london",
        )
    )

    assert search_options[0].source_url == "https://example.test/tickets/smithfield-market"
    assert availability.status == "unknown"
    assert availability.metadata is not None
    assert ticketing_link is not None
    assert ticketing_link.source_url == "https://example.test/tickets/smithfield-market"
    assert tour_link is not None
    assert tour_link.source_url == "https://example.test/tours/london/smithfield-market"
    assert len(options) == 1
    assert options[0].source_url == "https://example.test/tickets/smithfield-market"
    assert options[0].affiliate is False
    assert options[0].last_checked_at is not None
    assert options[0].metadata is not None
    assert options[0].metadata.provider_type == "ticketing"


def test_mock_affiliate_provider_satisfies_affiliate_contract() -> None:
    provider = get_affiliate_provider()

    products = provider.lookup_book_affiliate_links(
        AffiliateProductRequest(
            book_id="oliver-twist",
            title="Oliver Twist",
            author="Charles Dickens",
        )
    )

    assert len(products) == 3
    assert products[0].source_url is not None
    assert products[0].affiliate is True
    assert products[0].last_checked_at is not None
    assert products[0].metadata is not None
    assert products[0].metadata.provider_type == "affiliate"


@pytest.mark.parametrize(
    ("env_name", "getter", "message"),
    [
        ("LITINERARY_AI_PROVIDER", get_ai_pipeline, "ENABLE_REAL_LLM"),
        ("LITINERARY_VECTOR_PROVIDER", get_vector_service, "ENABLE_REAL_VECTOR_DB"),
        (
            "LITINERARY_POI_VERIFICATION_PROVIDER",
            get_poi_verification_adapter,
            "ENABLE_REAL_POI_PROVIDER",
        ),
        ("ROUTING_PROVIDER", get_routing_provider, "ENABLE_REAL_ROUTING"),
        ("TICKETING_PROVIDER", get_ticketing_provider, "ENABLE_REAL_TICKETING"),
        ("AFFILIATE_PROVIDER", get_affiliate_provider, "ENABLE_AFFILIATE_LINKS"),
        ("TTS_PROVIDER", get_narration_service, "ENABLE_REAL_TTS"),
    ],
)
def test_real_provider_flags_prevent_accidental_external_usage(
    monkeypatch,
    env_name,
    getter,
    message,
) -> None:
    monkeypatch.setenv(env_name, "real-provider")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match=message):
        getter()
