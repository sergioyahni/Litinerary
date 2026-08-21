import json
import logging
import os
from contextvars import ContextVar
from dataclasses import dataclass
from enum import StrEnum
from time import perf_counter
from typing import Any
from uuid import uuid4


REQUEST_ID_HEADER = "X-Request-ID"
request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


class EventName(StrEnum):
    API_REQUEST_STARTED = "api_request_started"
    API_REQUEST_COMPLETED = "api_request_completed"
    API_REQUEST_FAILED = "api_request_failed"
    ITINERARY_GENERATION_REQUESTED = "itinerary_generation_requested"
    ITINERARY_GENERATION_SUCCEEDED = "itinerary_generation_succeeded"
    ITINERARY_GENERATION_FAILED = "itinerary_generation_failed"
    PROVIDER_SELECTION = "provider_selection"
    PROVIDER_CALL_BLOCKED = "provider_call_blocked"
    PROVIDER_CALL_SUCCEEDED = "provider_call_succeeded"
    PROVIDER_CALL_FAILED = "provider_call_failed"
    POI_VERIFICATION_REQUESTED = "poi_verification_requested"
    ROUTING_REQUESTED = "routing_requested"
    LLM_JUDGE_REJECTED = "llm_judge_rejected"
    ADMIN_ACTION_ATTEMPTED = "admin_action_attempted"
    RATE_LIMIT_ALLOWED = "rate_limit_allowed"
    RATE_LIMIT_BLOCKED = "rate_limit_blocked"
    USAGE_LIMITER_FAILED = "usage_limiter_failed"
    USAGE_COUNTER_CLEANUP_COMPLETED = "usage_counter_cleanup_completed"
    USAGE_COUNTER_CLEANUP_FAILED = "usage_counter_cleanup_failed"
    AUTH_FORBIDDEN = "auth_forbidden"
    AUTH_UNAUTHORIZED = "auth_unauthorized"
    READINESS_CHECKED = "readiness_checked"


SENSITIVE_KEY_PARTS = {
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "jwt",
    "password",
    "prompt",
    "raw",
    "secret",
    "text",
    "token",
}

logger = logging.getLogger("litinerary")


@dataclass(frozen=True)
class ProviderTelemetry:
    provider_type: str
    provider_name: str
    operation: str
    success: bool
    latency_ms: int | None = None
    estimated_cost_usd: float | None = None
    warning_count: int = 0
    error_type: str | None = None
    request_id: str | None = None


def configure_logging() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO)
    logger.setLevel(logging.INFO)


def current_request_id() -> str | None:
    return request_id_context.get()


def new_request_id() -> str:
    return f"req-{uuid4().hex}"


def log_event(
    event_name: EventName | str,
    *,
    level: int = logging.INFO,
    category: str = "application",
    **fields: Any,
) -> None:
    payload = {
        "event": str(event_name),
        "category": category,
        "request_id": fields.pop("request_id", None) or current_request_id(),
        "app_env": _current_app_env(),
        **_redact(fields),
    }
    logger.log(level, json.dumps(payload, sort_keys=True, separators=(",", ":")))


def record_provider_selection(
    *,
    provider_type: str,
    provider_name: str,
    mode: str,
) -> None:
    log_event(
        EventName.PROVIDER_SELECTION,
        category="provider",
        provider_type=provider_type,
        provider_name=provider_name,
        mode=mode,
    )


def record_provider_telemetry(telemetry: ProviderTelemetry) -> None:
    log_event(
        EventName.PROVIDER_CALL_SUCCEEDED
        if telemetry.success
        else EventName.PROVIDER_CALL_FAILED,
        category="provider",
        provider_type=telemetry.provider_type,
        provider_name=telemetry.provider_name,
        operation=telemetry.operation,
        success=telemetry.success,
        latency_ms=telemetry.latency_ms,
        estimated_cost_usd=telemetry.estimated_cost_usd,
        warning_count=telemetry.warning_count,
        error_type=telemetry.error_type,
        request_id=telemetry.request_id,
    )


def log_provider_blocked(
    *,
    provider_type: str,
    provider_name: str,
    reason: str,
    operation: str | None = None,
) -> None:
    log_event(
        EventName.PROVIDER_CALL_BLOCKED,
        category="provider",
        provider_type=provider_type,
        provider_name=provider_name,
        operation=operation,
        reason=reason,
    )


def start_timer() -> float:
    return perf_counter()


def elapsed_ms(started_at: float) -> int:
    return round((perf_counter() - started_at) * 1000)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in SENSITIVE_KEY_PARTS):
                redacted[str(key)] = "[redacted]"
            else:
                redacted[str(key)] = _redact(item)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    return value


def _current_app_env() -> str:
    value = os.getenv("APP_ENV", "development").strip().lower()
    if value in {"development", "test", "internal", "beta", "staging", "production"}:
        return value
    return "development"
