from dataclasses import dataclass, field
from typing import Literal
from typing import Protocol

from app.services.provider_contracts import ProviderMetadata

AvailabilityStatus = Literal["available", "unavailable", "unknown"]


@dataclass(frozen=True)
class TicketingRequest:
    poi_id: str
    poi_name: str
    destination_id: str
    date: str | None = None


@dataclass(frozen=True)
class TicketingOption:
    title: str
    source_url: str | None
    estimated_price: float | None = None
    currency: str | None = None
    affiliate: bool = False
    last_checked_at: str | None = None
    confidence_score: float | None = None
    warnings: list[str] = field(default_factory=list)
    metadata: ProviderMetadata | None = None


@dataclass(frozen=True)
class TicketingSearchRequest:
    query: str
    destination_id: str
    date: str | None = None
    limit: int = 5


@dataclass(frozen=True)
class TicketAvailabilityRequest:
    poi_id: str
    poi_name: str
    destination_id: str
    date: str | None = None
    quantity: int = 1


@dataclass(frozen=True)
class TicketAvailability:
    status: AvailabilityStatus
    source_url: str | None = None
    last_checked_at: str | None = None
    warnings: list[str] = field(default_factory=list)
    metadata: ProviderMetadata | None = None


@dataclass(frozen=True)
class TicketingUrlRequest:
    poi_id: str
    poi_name: str
    destination_id: str
    date: str | None = None


@dataclass(frozen=True)
class TicketingLink:
    title: str
    source_url: str | None
    affiliate: bool = False
    last_checked_at: str | None = None
    confidence_score: float | None = None
    warnings: list[str] = field(default_factory=list)
    metadata: ProviderMetadata | None = None


@dataclass(frozen=True)
class TourBookingRequest:
    poi_id: str
    poi_name: str
    destination_id: str
    date: str | None = None


@dataclass(frozen=True)
class TourBookingOption:
    title: str
    source_url: str | None
    estimated_price: float | None = None
    currency: str | None = None
    affiliate: bool = False
    last_checked_at: str | None = None
    relevance_score: float | None = None
    warnings: list[str] = field(default_factory=list)
    metadata: ProviderMetadata | None = None


class TicketingProvider(Protocol):
    """Provider-neutral ticketing lookup contract.

    Future adapters must avoid exposing raw provider payloads, enforce timeouts and
    cost controls, and clearly distinguish affiliate links from neutral references.
    """

    def search_ticketing_options(
        self,
        request: TicketingSearchRequest,
    ) -> list[TicketingOption]:
        """Search safe ticketing/logistics options for a destination query."""

    def find_ticketing_options(self, request: TicketingRequest) -> list[TicketingOption]:
        """Return safe ticketing/logistics options for a POI."""

    def lookup_availability(self, request: TicketAvailabilityRequest) -> TicketAvailability:
        """Return optional availability status without booking or checkout behavior."""

    def lookup_ticketing_url(self, request: TicketingUrlRequest) -> TicketingLink | None:
        """Return a safe provider URL for POI tickets when available."""

    def lookup_tour_booking_url(self, request: TourBookingRequest) -> TourBookingOption | None:
        """Return a safe provider URL for guided tours when available."""
