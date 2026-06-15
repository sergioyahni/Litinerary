from dataclasses import dataclass, field
from typing import Protocol

from app.services.provider_contracts import ProviderMetadata


@dataclass(frozen=True)
class RoutePoint:
    id: str
    name: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class RouteRequest:
    points: list[RoutePoint]
    transportation_mode: str
    max_duration_minutes: int | None = None


@dataclass(frozen=True)
class RouteSegment:
    origin_id: str
    destination_id: str
    distance_km: float | None
    duration_minutes: int | None
    instructions: list[str] = field(default_factory=list)
    geometry: list[list[float]] = field(default_factory=list)


@dataclass(frozen=True)
class RoutePlan:
    segments: list[RouteSegment]
    total_distance_km: float | None
    total_duration_minutes: int | None
    feasible: bool
    geometry: list[list[float]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: ProviderMetadata | None = None


class RoutingProvider(Protocol):
    """Provider-neutral route planning contract.

    Future real adapters should apply provider timeouts, bounded retries, rate-limit
    handling, and cost controls before returning a RoutePlan.
    """

    def plan_route(self, request: RouteRequest) -> RoutePlan:
        """Return route feasibility and segment estimates for ordered points."""
