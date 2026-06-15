import pytest

from app.core.config import get_settings
from app.schemas.domain import AffiliateLink, Book, POI
from app.services.affiliate_service import get_affiliate_provider, validate_affiliate_startup
from app.services.affiliate_types import AffiliateProductRequest
from app.services.ticketing_service import get_ticketing_provider, validate_ticketing_startup
from app.services.ticketing_types import TicketingRequest


@pytest.fixture(autouse=True)
def clear_provider_caches():
    get_settings.cache_clear()
    get_ticketing_provider.cache_clear()
    get_affiliate_provider.cache_clear()
    yield
    get_settings.cache_clear()
    get_ticketing_provider.cache_clear()
    get_affiliate_provider.cache_clear()


def test_mock_ticketing_and_affiliate_are_default_without_credentials(monkeypatch) -> None:
    monkeypatch.delenv("TICKETING_API_KEY", raising=False)
    monkeypatch.delenv("AFFILIATE_API_KEY", raising=False)
    monkeypatch.delenv("ENABLE_REAL_TICKETING", raising=False)
    monkeypatch.delenv("ENABLE_AFFILIATE_LINKS", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.ticketing_provider == "mock"
    assert settings.affiliate_provider == "mock"
    assert get_ticketing_provider() is not None
    assert get_affiliate_provider() is not None


def test_real_ticketing_enabled_without_config_fails_clearly(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_REAL_TICKETING", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS", "development")
    monkeypatch.setenv("TICKETING_PROVIDER", "future_ticketing")
    monkeypatch.delenv("TICKETING_API_KEY", raising=False)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="TICKETING_API_KEY"):
        validate_ticketing_startup()


def test_real_ticketing_enabled_with_mock_provider_fails_clearly(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_REAL_TICKETING", "true")
    monkeypatch.setenv("TICKETING_PROVIDER", "mock")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="no real ticketing adapter"):
        validate_ticketing_startup()


def test_real_affiliate_enabled_without_config_fails_clearly(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_AFFILIATE_LINKS", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS", "development")
    monkeypatch.setenv("AFFILIATE_PROVIDER", "future_affiliate")
    monkeypatch.delenv("AFFILIATE_API_KEY", raising=False)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="AFFILIATE_API_KEY"):
        validate_affiliate_startup()


def test_mock_ticketing_provider_never_requires_external_configuration() -> None:
    options = get_ticketing_provider().find_ticketing_options(
        TicketingRequest(
            poi_id="british-museum",
            poi_name="British Museum",
            destination_id="london",
        )
    )

    assert options[0].source_url == "https://example.test/tickets/british-museum"
    assert options[0].metadata is not None
    assert options[0].metadata.source_url == options[0].source_url
    assert options[0].metadata.raw_provider_reference is None


def test_mock_affiliate_provider_returns_disclosed_placeholder_links() -> None:
    products = get_affiliate_provider().find_products(
        AffiliateProductRequest(
            book_id="moby-dick",
            title="Moby-Dick",
            author="Herman Melville",
            format="ebook",
        )
    )

    assert len(products) == 1
    assert products[0].affiliate is True
    assert products[0].source_url == "https://example.test/books/moby-dick-herman-melville-ebook"
    assert products[0].metadata is not None
    assert products[0].metadata.provider_type == "affiliate"


def test_ticketing_and_affiliate_links_are_optional_schema_fields() -> None:
    poi = POI(
        id="optional-poi",
        destinationId="london",
        bookIds=["oliver-twist"],
        name="Optional Stop",
        description="No ticketing URL is required.",
        latitude=51.5,
        longitude=-0.1,
        estimatedDurationMinutes=30,
        literaryRelevance="Test relevance.",
        verificationStatus="mock",
    )
    book = Book(
        id="optional-book",
        destinationIds=["london"],
        title="Optional Book",
        author="Example Author",
        description="No affiliate links are required.",
        publicDomain=True,
        themes=[],
    )

    assert poi.ticketingUrl is None
    assert book.affiliateLinks == []


def test_book_affiliate_link_schema_preserves_provider_metadata_fields() -> None:
    link = AffiliateLink(
        title="Example Book",
        sourceUrl="https://example.test/books/example",
        providerName="mock_affiliate",
        affiliate=True,
        lastCheckedAt="2026-06-14T00:00:00+00:00",
        relevanceScore=0.4,
    )

    payload = link.model_dump()

    assert payload["providerName"] == "mock_affiliate"
    assert payload["providerType"] == "affiliate"
    assert payload["affiliate"] is True
    assert payload["lastCheckedAt"] == "2026-06-14T00:00:00+00:00"
    assert payload["relevanceScore"] == 0.4
