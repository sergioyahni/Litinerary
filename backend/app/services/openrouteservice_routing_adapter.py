from dataclasses import dataclass
import json
from time import monotonic
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import get_settings
from app.core.provider_guards import require_external_call_allowed
from app.services.provider_contracts import (
    ProviderError,
    ProviderErrorCode,
    ProviderMetadata,
    ProviderType,
    utc_now_iso,
)
from app.services.usage_policy import get_usage_guard
from app.services.routing_types import RoutePlan, RouteRequest, RouteSegment


class OpenRouteServiceTransport(Protocol):
    def directions(
        self,
        profile: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], int | None]:
        """Return a normalized OpenRouteService GeoJSON directions response."""


@dataclass(frozen=True)
class OpenRouteServiceSettings:
    api_key: str
    base_url: str = "https://api.openrouteservice.org"
    timeout_seconds: float = 5.0
    max_stops: int = 10
    supported_modes: list[str] | None = None
    fallback_behavior: str = "mock"


class OpenRouteServiceHttpTransport:
    def __init__(self, settings: OpenRouteServiceSettings) -> None:
        self.settings = settings
        self.base_url = settings.base_url.rstrip("/")

    def directions(
        self,
        profile: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], int | None]:
        settings = get_settings()
        require_external_call_allowed(
            provider_name="openrouteservice",
            provider_type=ProviderType.ROUTING,
            feature_flag_name="ENABLE_REAL_ROUTING",
            feature_enabled=settings.enable_real_routing,
            required_config={"ROUTING_API_KEY or OPENROUTESERVICE_API_KEY": self.settings.api_key},
            settings=settings,
        )
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}/v2/directions/{profile}/geojson",
            data=body,
            headers={
                "Accept": "application/json",
                "Authorization": self.settings.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = monotonic()
        try:
            with urlopen(request, timeout=self.settings.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as exc:
            if exc.code == 429:
                raise _provider_error(
                    ProviderErrorCode.RATE_LIMITED,
                    "OpenRouteService rate limit was exceeded.",
                ) from exc
            raise _provider_error(
                ProviderErrorCode.INVALID_RESPONSE,
                f"OpenRouteService returned HTTP {exc.code}.",
            ) from exc
        except TimeoutError as exc:
            raise _provider_error(
                ProviderErrorCode.TIMEOUT,
                "OpenRouteService request timed out.",
            ) from exc
        except URLError as exc:
            raise _provider_error(
                ProviderErrorCode.UNAVAILABLE,
                "OpenRouteService is unavailable.",
            ) from exc

        latency_ms = round((monotonic() - started) * 1000)
        if not response_body:
            return {}, latency_ms
        try:
            return json.loads(response_body), latency_ms
        except json.JSONDecodeError as exc:
            raise _provider_error(
                ProviderErrorCode.INVALID_RESPONSE,
                "OpenRouteService returned non-JSON response.",
                latency_ms=latency_ms,
            ) from exc


class OpenRouteServiceRoutingProvider:
    provider_name = "openrouteservice"
    provider_version = "directions-v2"

    def __init__(
        self,
        settings: OpenRouteServiceSettings,
        transport: OpenRouteServiceTransport | None = None,
    ) -> None:
        if not settings.api_key:
            raise _provider_error(
                ProviderErrorCode.NOT_CONFIGURED,
                "OpenRouteService API key is required when real routing is enabled.",
            )
        if settings.timeout_seconds <= 0:
            raise _provider_error(
                ProviderErrorCode.NOT_CONFIGURED,
                "Routing provider timeout must be positive.",
            )
        if settings.max_stops <= 1:
            raise _provider_error(
                ProviderErrorCode.NOT_CONFIGURED,
                "Routing provider max stops must be greater than 1.",
            )
        if settings.fallback_behavior not in {"mock", "error"}:
            raise _provider_error(
                ProviderErrorCode.NOT_CONFIGURED,
                "Routing fallback behavior must be mock or error.",
            )
        self.settings = settings
        self.supported_modes = settings.supported_modes or ["walking", "car_taxi"]
        self.transport = transport or OpenRouteServiceHttpTransport(settings)

    def plan_route(self, request: RouteRequest) -> RoutePlan:
        get_usage_guard().guard_routing_calculation(stop_count=len(request.points))
        self._validate_request(request)
        if len(request.points) < 2:
            return RoutePlan(
                segments=[],
                total_distance_km=0.0,
                total_duration_minutes=0,
                feasible=bool(request.points),
                geometry=[
                    [point.latitude, point.longitude]
                    for point in request.points
                ],
                warnings=["At least two stops are required for provider route calculation."],
                metadata=self._metadata(warnings=["No provider route call was needed."]),
            )

        profile = _profile_for_mode(request.transportation_mode)
        payload = {
            "coordinates": [
                [point.longitude, point.latitude]
                for point in request.points
            ],
            "instructions": True,
        }
        response, latency_ms = self.transport.directions(profile, payload)
        return self._route_plan_from_response(request, response, latency_ms)

    def _validate_request(self, request: RouteRequest) -> None:
        if len(request.points) > self.settings.max_stops:
            raise _provider_error(
                ProviderErrorCode.COST_LIMIT_EXCEEDED,
                f"Route request has too many stops; maximum is {self.settings.max_stops}.",
            )
        if request.transportation_mode not in {"walking", "public_transport", "car_taxi"}:
            raise _provider_error(
                ProviderErrorCode.UNSUPPORTED_LOCATION,
                f"Unsupported transportation mode: {request.transportation_mode}",
            )
        if request.transportation_mode not in self.supported_modes:
            raise _provider_error(
                ProviderErrorCode.UNSUPPORTED_LOCATION,
                (
                    "OpenRouteService adapter does not support "
                    f"{request.transportation_mode} routing in this configuration."
                ),
                warnings=["OpenRouteService does not provide transit routing here."],
            )
        for point in request.points:
            if not -90 <= point.latitude <= 90 or not -180 <= point.longitude <= 180:
                raise _provider_error(
                    ProviderErrorCode.UNSUPPORTED_LOCATION,
                    f"Invalid coordinates for route point '{point.id}'.",
                )

    def _route_plan_from_response(
        self,
        request: RouteRequest,
        response: dict[str, Any],
        latency_ms: int | None,
    ) -> RoutePlan:
        feature = _first_feature(response)
        geometry = _geometry(feature)
        properties = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
        summary = properties.get("summary") if isinstance(properties.get("summary"), dict) else {}
        total_distance_km = round(float(summary.get("distance") or 0.0) / 1000, 2)
        total_duration_minutes = round(float(summary.get("duration") or 0.0) / 60)
        segments = _segments(request, properties)
        warnings = ["OpenRouteService route geometry normalized for Leaflet display."]
        metadata = properties.get("metadata") if isinstance(properties.get("metadata"), dict) else {}
        request_id = _string_or_none(metadata.get("id")) or _string_or_none(response.get("id"))
        return RoutePlan(
            segments=segments,
            total_distance_km=total_distance_km,
            total_duration_minutes=total_duration_minutes,
            feasible=True,
            geometry=geometry,
            warnings=warnings,
            metadata=self._metadata(
                request_id=request_id,
                latency_ms=latency_ms,
                warnings=warnings,
                raw_provider_reference=request_id,
            ),
        )

    def _metadata(
        self,
        *,
        request_id: str | None = None,
        latency_ms: int | None = None,
        warnings: list[str] | None = None,
        raw_provider_reference: str | None = None,
    ) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name=self.provider_name,
            provider_type=ProviderType.ROUTING.value,
            provider_version=self.provider_version,
            request_id=request_id,
            generated_at=utc_now_iso(),
            latency_ms=latency_ms,
            warnings=warnings or [],
            raw_provider_reference=raw_provider_reference,
        )


def _profile_for_mode(transportation_mode: str) -> str:
    if transportation_mode == "walking":
        return "foot-walking"
    if transportation_mode == "car_taxi":
        return "driving-car"
    raise _provider_error(
        ProviderErrorCode.UNSUPPORTED_LOCATION,
        "OpenRouteService public transportation routing is not supported by this adapter.",
        warnings=["Use mock fallback or a future transit-capable routing provider."],
    )


def _first_feature(response: dict[str, Any]) -> dict[str, Any]:
    features = response.get("features")
    if not isinstance(features, list) or not features:
        raise _provider_error(
            ProviderErrorCode.INVALID_RESPONSE,
            "OpenRouteService response did not contain route features.",
        )
    feature = features[0]
    if not isinstance(feature, dict):
        raise _provider_error(
            ProviderErrorCode.INVALID_RESPONSE,
            "OpenRouteService route feature was not an object.",
        )
    return feature


def _geometry(feature: dict[str, Any]) -> list[list[float]]:
    geometry = feature.get("geometry")
    if not isinstance(geometry, dict):
        raise _provider_error(
            ProviderErrorCode.INVALID_RESPONSE,
            "OpenRouteService response did not include geometry.",
        )
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list):
        raise _provider_error(
            ProviderErrorCode.INVALID_RESPONSE,
            "OpenRouteService geometry coordinates were not a list.",
        )
    normalized = []
    for coordinate in coordinates:
        if (
            isinstance(coordinate, list)
            and len(coordinate) >= 2
            and isinstance(coordinate[0], int | float)
            and isinstance(coordinate[1], int | float)
        ):
            normalized.append([float(coordinate[1]), float(coordinate[0])])
    if not normalized:
        raise _provider_error(
            ProviderErrorCode.INVALID_RESPONSE,
            "OpenRouteService geometry did not contain usable coordinates.",
        )
    return normalized


def _segments(request: RouteRequest, properties: dict[str, Any]) -> list[RouteSegment]:
    raw_segments = properties.get("segments")
    if not isinstance(raw_segments, list):
        raw_segments = []
    segments = []
    for index, (origin, destination) in enumerate(
        zip(request.points, request.points[1:], strict=False)
    ):
        raw_segment = raw_segments[index] if index < len(raw_segments) else {}
        raw_segment = raw_segment if isinstance(raw_segment, dict) else {}
        instructions = _instructions(raw_segment)
        segments.append(
            RouteSegment(
                origin_id=origin.id,
                destination_id=destination.id,
                distance_km=round(float(raw_segment.get("distance") or 0.0) / 1000, 2),
                duration_minutes=round(float(raw_segment.get("duration") or 0.0) / 60),
                instructions=instructions,
            )
        )
    return segments


def _instructions(segment: dict[str, Any]) -> list[str]:
    steps = segment.get("steps")
    if not isinstance(steps, list):
        return []
    return [
        instruction
        for step in steps
        if isinstance(step, dict)
        for instruction in [_string_or_none(step.get("instruction"))]
        if instruction
    ]


def _string_or_none(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _provider_error(
    code: ProviderErrorCode,
    message: str,
    *,
    warnings: list[str] | None = None,
    latency_ms: int | None = None,
) -> ProviderError:
    return ProviderError(
        code,
        message,
        metadata=ProviderMetadata(
            provider_name="openrouteservice",
            provider_type=ProviderType.ROUTING.value,
            provider_version="directions-v2",
            generated_at=utc_now_iso(),
            latency_ms=latency_ms,
            warnings=warnings or [],
        ),
    )
