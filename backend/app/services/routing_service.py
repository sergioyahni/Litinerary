from functools import lru_cache
from math import sqrt

from app.core.config import get_settings
from app.schemas.domain import Itinerary, ItineraryDay
from app.services.provider_contracts import ProviderError, ProviderMetadata, ProviderType
from app.services.routing_types import RoutePlan, RoutePoint, RouteRequest, RouteSegment, RoutingProvider


class MockRoutingProvider:
    provider_name = "mock_routing"

    def plan_route(self, request: RouteRequest) -> RoutePlan:
        _validate_route_request(request, max_stops=50)
        segments: list[RouteSegment] = []
        for origin, destination in zip(request.points, request.points[1:], strict=False):
            distance = _rough_distance_km(
                origin.latitude,
                origin.longitude,
                destination.latitude,
                destination.longitude,
            )
            segments.append(
                RouteSegment(
                    origin_id=origin.id,
                    destination_id=destination.id,
                    distance_km=distance,
                    duration_minutes=max(1, round(distance * 15)),
                    instructions=["Mock straight-line segment; no routing API was called."],
                    geometry=[
                        [origin.latitude, origin.longitude],
                        [destination.latitude, destination.longitude],
                    ],
                )
            )

        total_distance = round(sum(segment.distance_km or 0 for segment in segments), 2)
        total_minutes = sum(segment.duration_minutes or 0 for segment in segments)
        return RoutePlan(
            segments=segments,
            total_distance_km=total_distance,
            total_duration_minutes=total_minutes,
            feasible=bool(request.points),
            geometry=[
                [point.latitude, point.longitude]
                for point in request.points
            ],
            warnings=["Mock routing uses straight-line estimates only."],
            metadata=ProviderMetadata.mock(
                provider_name=self.provider_name,
                provider_type=ProviderType.ROUTING,
                confidence_score=0.4,
                warnings=["No external routing provider call was made."],
            ),
        )


@lru_cache
def get_routing_provider() -> RoutingProvider:
    settings = get_settings()
    if settings.routing_provider == "mock" and not settings.enable_mock_services:
        raise RuntimeError(
            "Mock routing services are disabled in this environment. "
            "Set ENABLE_MOCK_SERVICES=true only for intentional local/test use."
        )
    if settings.routing_provider != "mock" and not settings.enable_real_routing:
        raise RuntimeError(
            f"Real routing provider '{settings.routing_provider}' is disabled by ENABLE_REAL_ROUTING."
        )
    if settings.routing_provider == "openrouteservice":
        validate_routing_startup(settings)
        from app.services.openrouteservice_routing_adapter import (
            OpenRouteServiceRoutingProvider,
            OpenRouteServiceSettings,
        )

        return OpenRouteServiceRoutingProvider(
            OpenRouteServiceSettings(
                api_key=settings.routing_api_key or "",
                base_url=settings.routing_base_url,
                timeout_seconds=settings.routing_timeout_seconds,
                max_stops=settings.routing_max_stops,
                supported_modes=settings.routing_supported_modes,
                fallback_behavior=settings.routing_fallback_behavior,
            )
        )
    if settings.routing_provider != "mock":
        raise RuntimeError(
            f"Routing provider '{settings.routing_provider}' is configured but not implemented."
        )
    return MockRoutingProvider()


def validate_routing_startup(settings=None) -> None:
    resolved = settings or get_settings()
    if not resolved.enable_real_routing:
        return
    if resolved.routing_provider != "openrouteservice":
        raise RuntimeError(
            "Real routing is enabled but only the OpenRouteService adapter boundary is "
            "implemented. Set ROUTING_PROVIDER=openrouteservice or disable ENABLE_REAL_ROUTING."
        )
    missing = []
    if not resolved.routing_api_key:
        missing.append("ROUTING_API_KEY or OPENROUTESERVICE_API_KEY")
    if resolved.routing_timeout_seconds <= 0:
        missing.append("ROUTING_TIMEOUT_SECONDS must be positive")
    if resolved.routing_max_stops <= 1:
        missing.append("ROUTING_MAX_STOPS must be greater than 1")
    if not resolved.routing_supported_modes:
        missing.append("ROUTING_SUPPORTED_MODES must contain at least one mode")
    if resolved.routing_fallback_behavior not in {"mock", "error"}:
        missing.append("ROUTING_FALLBACK_BEHAVIOR must be mock or error")
    if missing:
        raise RuntimeError(
            "Real OpenRouteService routing is enabled but configuration is incomplete: "
            + ", ".join(missing)
        )


def enrich_itinerary_routes(itinerary: Itinerary) -> Itinerary:
    settings = get_settings()
    provider = get_routing_provider()
    days = [
        _enrich_day_route(
            day,
            itinerary.transportationMode,
            provider,
            fallback_to_mock=settings.routing_fallback_behavior == "mock",
        )
        for day in itinerary.days
    ]
    return itinerary.model_copy(update={"days": days}, deep=True)


def _rough_distance_km(
    left_latitude: float,
    left_longitude: float,
    right_latitude: float,
    right_longitude: float,
) -> float:
    return round(sqrt((left_latitude - right_latitude) ** 2 + (left_longitude - right_longitude) ** 2) * 111, 2)


def _enrich_day_route(
    day: ItineraryDay,
    transportation_mode: str,
    provider: RoutingProvider,
    *,
    fallback_to_mock: bool,
) -> ItineraryDay:
    points = [
        RoutePoint(
            id=stop.id,
            name=stop.poi.name,
            latitude=stop.poi.latitude,
            longitude=stop.poi.longitude,
        )
        for stop in day.stops
    ]
    if not points:
        return day
    try:
        plan = provider.plan_route(
            RouteRequest(points=points, transportation_mode=transportation_mode)
        )
    except ProviderError as exc:
        if not fallback_to_mock:
            raise
        plan = MockRoutingProvider().plan_route(
            RouteRequest(points=points, transportation_mode=transportation_mode)
        )
        plan.warnings.append(
            f"Routing provider failed with {exc.code.value}; used mock straight-line fallback."
        )
    return day.model_copy(
        update={
            "estimatedDistanceKm": plan.total_distance_km,
            "estimatedDurationHours": round((plan.total_duration_minutes or 0) / 60, 2),
            "routeGeometry": plan.geometry,
            "routingProviderMetadata": plan.metadata.public_dict() if plan.metadata else None,
            "routingWarnings": plan.warnings,
        },
        deep=True,
    )


def _validate_route_request(request: RouteRequest, max_stops: int) -> None:
    if len(request.points) > max_stops:
        raise ValueError(f"Route request has too many stops; maximum is {max_stops}.")
    if request.transportation_mode not in {"walking", "public_transport", "car_taxi"}:
        raise ValueError(f"Unsupported transportation mode: {request.transportation_mode}")
    for point in request.points:
        if not -90 <= point.latitude <= 90 or not -180 <= point.longitude <= 180:
            raise ValueError(f"Invalid coordinates for route point '{point.id}'.")
