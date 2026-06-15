from functools import lru_cache

from app.core.config import get_settings
from app.core.observability import record_provider_selection
from app.core.provider_guards import require_external_call_allowed
from app.services.provider_contracts import ProviderMetadata, ProviderType, utc_now_iso
from app.services.usage_policy import get_usage_guard
from app.services.ticketing_types import (
    TicketAvailability,
    TicketAvailabilityRequest,
    TicketingLink,
    TicketingOption,
    TicketingProvider,
    TicketingRequest,
    TicketingSearchRequest,
    TicketingUrlRequest,
    TourBookingOption,
    TourBookingRequest,
)


class MockTicketingProvider:
    provider_name = "mock_ticketing"

    def __init__(self, base_url: str = "https://example.test") -> None:
        self.base_url = base_url.rstrip("/")

    def search_ticketing_options(
        self,
        request: TicketingSearchRequest,
    ) -> list[TicketingOption]:
        get_usage_guard().guard_ticketing_lookup(request_count=request.limit)
        poi_name = request.query.strip() or "literary stop"
        return self.find_ticketing_options(
            TicketingRequest(
                poi_id=_slugify(poi_name),
                poi_name=poi_name,
                destination_id=request.destination_id,
                date=request.date,
            )
        )[: request.limit]

    def find_ticketing_options(self, request: TicketingRequest) -> list[TicketingOption]:
        get_usage_guard().guard_ticketing_lookup()
        link = self.lookup_ticketing_url(
            TicketingUrlRequest(
                poi_id=request.poi_id,
                poi_name=request.poi_name,
                destination_id=request.destination_id,
                date=request.date,
            )
        )
        if link is None:
            return []
        return [
            TicketingOption(
                title=link.title,
                source_url=link.source_url,
                affiliate=link.affiliate,
                last_checked_at=link.last_checked_at,
                confidence_score=link.confidence_score,
                warnings=["Placeholder only; no live ticket inventory was queried."],
                metadata=link.metadata,
            )
        ]

    def lookup_availability(self, request: TicketAvailabilityRequest) -> TicketAvailability:
        get_usage_guard().guard_ticketing_lookup()
        checked_at = utc_now_iso()
        return TicketAvailability(
            status="unknown",
            source_url=f"{self.base_url}/tickets/{_slugify(request.poi_name)}",
            last_checked_at=checked_at,
            warnings=[
                "Mock availability is unknown; no live ticket inventory was queried.",
            ],
            metadata=_mock_metadata(
                self.provider_name,
                source_url=f"{self.base_url}/tickets/{_slugify(request.poi_name)}",
                confidence_score=0.2,
            ),
        )

    def lookup_ticketing_url(self, request: TicketingUrlRequest) -> TicketingLink | None:
        get_usage_guard().guard_ticketing_lookup()
        source_url = f"{self.base_url}/tickets/{_slugify(request.poi_name)}"
        checked_at = utc_now_iso()
        return TicketingLink(
            title=f"Mock ticketing placeholder for {request.poi_name}",
            source_url=source_url,
            affiliate=False,
            last_checked_at=checked_at,
            confidence_score=0.2,
            warnings=["Placeholder only; no live ticketing provider call was made."],
            metadata=_mock_metadata(
                self.provider_name,
                source_url=source_url,
                confidence_score=0.2,
            ),
        )

    def lookup_tour_booking_url(self, request: TourBookingRequest) -> TourBookingOption | None:
        get_usage_guard().guard_ticketing_lookup()
        source_url = (
            f"{self.base_url}/tours/{_slugify(request.destination_id)}/"
            f"{_slugify(request.poi_name)}"
        )
        checked_at = utc_now_iso()
        return TourBookingOption(
            title=f"Mock guided tour placeholder for {request.poi_name}",
            source_url=source_url,
            affiliate=False,
            last_checked_at=checked_at,
            relevance_score=0.2,
            warnings=["Placeholder only; no live guided tour provider call was made."],
            metadata=_mock_metadata(
                self.provider_name,
                source_url=source_url,
                confidence_score=0.2,
            ),
        )


@lru_cache
def get_ticketing_provider() -> TicketingProvider:
    settings = get_settings()
    if settings.enable_real_ticketing:
        validate_ticketing_startup(settings)
    if settings.ticketing_provider == "mock" and not settings.enable_mock_services:
        raise RuntimeError(
            "Mock ticketing services are disabled in this environment. "
            "Set ENABLE_MOCK_SERVICES=true only for intentional local/test use."
        )
    if settings.ticketing_provider != "mock" and not settings.enable_real_ticketing:
        raise RuntimeError(
            f"Real ticketing provider '{settings.ticketing_provider}' is disabled by ENABLE_REAL_TICKETING."
        )
    if settings.ticketing_provider != "mock":
        raise RuntimeError(
            f"Ticketing provider '{settings.ticketing_provider}' is configured but not implemented."
        )
    record_provider_selection(
        provider_type=ProviderType.TICKETING.value,
        provider_name="mock",
        mode="mock",
    )
    return MockTicketingProvider(settings.ticketing_base_url)


def validate_ticketing_startup(settings=None) -> None:
    resolved = settings or get_settings()
    if not resolved.enable_real_ticketing:
        return
    if resolved.ticketing_provider == "mock":
        raise RuntimeError(
            "Real ticketing is enabled but no real ticketing adapter is implemented. "
            "Set ENABLE_REAL_TICKETING=false to use mock ticketing placeholders."
        )
    require_external_call_allowed(
        provider_name=resolved.ticketing_provider,
        provider_type=ProviderType.TICKETING,
        feature_flag_name="ENABLE_REAL_TICKETING",
        feature_enabled=resolved.enable_real_ticketing,
        required_config={
            "TICKETING_API_KEY": resolved.ticketing_api_key,
            "TICKETING_BASE_URL": resolved.ticketing_base_url,
        },
        settings=resolved,
    )
    missing = []
    if not resolved.ticketing_api_key:
        missing.append("TICKETING_API_KEY")
    if not resolved.ticketing_base_url:
        missing.append("TICKETING_BASE_URL")
    if resolved.ticketing_timeout_seconds <= 0:
        missing.append("TICKETING_TIMEOUT_SECONDS must be positive")
    if missing:
        raise RuntimeError(
            "Real ticketing is enabled but configuration is incomplete: "
            + ", ".join(missing)
        )
    raise RuntimeError(
        f"Ticketing provider '{resolved.ticketing_provider}' is configured, but no real "
        "ticketing adapter is implemented yet."
    )


def _mock_metadata(
    provider_name: str,
    *,
    source_url: str,
    confidence_score: float,
) -> ProviderMetadata:
    now = utc_now_iso()
    return ProviderMetadata(
        provider_name=provider_name,
        provider_type=ProviderType.TICKETING.value,
        provider_version="local-mock",
        confidence_score=confidence_score,
        source_url=source_url,
        generated_at=now,
        warnings=["No external ticketing provider call was made."],
    )


def _slugify(value: str) -> str:
    slug = "-".join(value.strip().lower().split())
    return slug or "unknown"
