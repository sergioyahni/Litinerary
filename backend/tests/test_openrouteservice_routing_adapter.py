import pytest

from app.core.config import get_settings
from app.services.openrouteservice_routing_adapter import (
    OpenRouteServiceRoutingProvider,
    OpenRouteServiceSettings,
)
from app.services.provider_contracts import ProviderError, ProviderErrorCode
from app.services.routing_service import (
    MockRoutingProvider,
    get_routing_provider,
    validate_routing_startup,
)
from app.services.routing_types import RoutePoint, RouteRequest


class FakeOpenRouteServiceTransport:
    def __init__(self, response: dict | None = None, error: ProviderError | None = None) -> None:
        self.response = response or _ors_response()
        self.error = error
        self.calls: list[dict] = []

    def directions(self, profile: str, payload: dict) -> tuple[dict, int]:
        self.calls.append({"profile": profile, "payload": payload})
        if self.error:
            raise self.error
        return self.response, 14


@pytest.fixture(autouse=True)
def clear_routing_cache():
    get_settings.cache_clear()
    get_routing_provider.cache_clear()
    yield
    get_settings.cache_clear()
    get_routing_provider.cache_clear()


def test_mock_routing_remains_default(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_REAL_ROUTING", raising=False)
    monkeypatch.delenv("ROUTING_PROVIDER", raising=False)

    provider = get_routing_provider()

    assert isinstance(provider, MockRoutingProvider)


def test_openrouteservice_selection_requires_real_routing_flag(monkeypatch) -> None:
    monkeypatch.setenv("ROUTING_PROVIDER", "openrouteservice")
    monkeypatch.delenv("ENABLE_REAL_ROUTING", raising=False)

    with pytest.raises(RuntimeError, match="ENABLE_REAL_ROUTING"):
        get_routing_provider()


def test_openrouteservice_selection_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_REAL_ROUTING", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS", "development")
    monkeypatch.setenv("ROUTING_PROVIDER", "openrouteservice")
    monkeypatch.setenv("OPENROUTESERVICE_API_KEY", "test-key")

    provider = get_routing_provider()

    assert isinstance(provider, OpenRouteServiceRoutingProvider)


def test_missing_openrouteservice_config_fails_clearly(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_REAL_ROUTING", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_CALLS", "true")
    monkeypatch.setenv("ROUTING_PROVIDER", "openrouteservice")
    monkeypatch.delenv("OPENROUTESERVICE_API_KEY", raising=False)
    monkeypatch.delenv("ROUTING_API_KEY", raising=False)

    with pytest.raises(ProviderError, match="OPENROUTESERVICE_API_KEY"):
        validate_routing_startup()


def test_openrouteservice_normalizes_route_response() -> None:
    transport = FakeOpenRouteServiceTransport()
    provider = OpenRouteServiceRoutingProvider(
        OpenRouteServiceSettings(api_key="test-key"),
        transport=transport,
    )

    plan = provider.plan_route(_route_request("walking"))

    assert plan.feasible is True
    assert plan.total_distance_km == 1.23
    assert plan.total_duration_minutes == 16
    assert plan.geometry == [[51.5, -0.1], [51.501, -0.101], [51.51, -0.11]]
    assert plan.segments[0].instructions == ["Head north", "Turn right"]
    assert plan.metadata is not None
    assert plan.metadata.provider_name == "openrouteservice"
    assert plan.metadata.raw_provider_reference == "request-123"
    assert transport.calls[0]["profile"] == "foot-walking"
    assert transport.calls[0]["payload"]["coordinates"] == [[-0.1, 51.5], [-0.11, 51.51]]


def test_openrouteservice_uses_driving_for_car_taxi() -> None:
    transport = FakeOpenRouteServiceTransport()
    provider = OpenRouteServiceRoutingProvider(
        OpenRouteServiceSettings(api_key="test-key"),
        transport=transport,
    )

    provider.plan_route(_route_request("car_taxi"))

    assert transport.calls[0]["profile"] == "driving-car"


def test_openrouteservice_handles_public_transport_as_unsupported() -> None:
    provider = OpenRouteServiceRoutingProvider(
        OpenRouteServiceSettings(api_key="test-key"),
        transport=FakeOpenRouteServiceTransport(),
    )

    with pytest.raises(ProviderError) as exc_info:
        provider.plan_route(_route_request("public_transport"))

    assert exc_info.value.code == ProviderErrorCode.UNSUPPORTED_LOCATION
    assert "transit" in exc_info.value.metadata.warnings[0].lower()


def test_openrouteservice_rejects_too_many_stops() -> None:
    provider = OpenRouteServiceRoutingProvider(
        OpenRouteServiceSettings(api_key="test-key", max_stops=2),
        transport=FakeOpenRouteServiceTransport(),
    )
    request = RouteRequest(
        points=[
            RoutePoint(id="a", name="A", latitude=51.5, longitude=-0.1),
            RoutePoint(id="b", name="B", latitude=51.51, longitude=-0.11),
            RoutePoint(id="c", name="C", latitude=51.52, longitude=-0.12),
        ],
        transportation_mode="walking",
    )

    with pytest.raises(ProviderError) as exc_info:
        provider.plan_route(request)

    assert exc_info.value.code == ProviderErrorCode.COST_LIMIT_EXCEEDED


@pytest.mark.parametrize(
    "code",
    [ProviderErrorCode.TIMEOUT, ProviderErrorCode.RATE_LIMITED],
)
def test_openrouteservice_normalizes_transport_errors(code) -> None:
    provider = OpenRouteServiceRoutingProvider(
        OpenRouteServiceSettings(api_key="test-key"),
        transport=FakeOpenRouteServiceTransport(
            error=ProviderError(code, f"normalized {code.value}")
        ),
    )

    with pytest.raises(ProviderError) as exc_info:
        provider.plan_route(_route_request("walking"))

    assert exc_info.value.code == code


def test_mock_route_request_validation() -> None:
    provider = MockRoutingProvider()

    with pytest.raises(ValueError, match="Invalid coordinates"):
        provider.plan_route(
            RouteRequest(
                points=[RoutePoint(id="bad", name="Bad", latitude=100, longitude=0)],
                transportation_mode="walking",
            )
        )


def test_unit_tests_use_fake_transport_without_network() -> None:
    transport = FakeOpenRouteServiceTransport()
    provider = OpenRouteServiceRoutingProvider(
        OpenRouteServiceSettings(api_key="test-key"),
        transport=transport,
    )

    provider.plan_route(_route_request("walking"))

    assert len(transport.calls) == 1


@pytest.mark.skip(reason="Live OpenRouteService integration requires explicit credentials and opt-in.")
def test_live_openrouteservice_integration_skipped_by_default() -> None:
    pass


def _route_request(mode: str) -> RouteRequest:
    return RouteRequest(
        points=[
            RoutePoint(id="a", name="A", latitude=51.5, longitude=-0.1),
            RoutePoint(id="b", name="B", latitude=51.51, longitude=-0.11),
        ],
        transportation_mode=mode,
    )


def _ors_response() -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-0.1, 51.5],
                        [-0.101, 51.501],
                        [-0.11, 51.51],
                    ],
                },
                "properties": {
                    "summary": {"distance": 1234.0, "duration": 960.0},
                    "metadata": {"id": "request-123"},
                    "segments": [
                        {
                            "distance": 1234.0,
                            "duration": 960.0,
                            "steps": [
                                {"instruction": "Head north"},
                                {"instruction": "Turn right"},
                            ],
                        }
                    ],
                },
            }
        ],
    }
