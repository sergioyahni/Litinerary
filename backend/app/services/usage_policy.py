from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Literal

from app.core.config import Settings, get_settings
from app.core.observability import EventName, log_event, record_provider_telemetry, ProviderTelemetry
from app.services.provider_contracts import (
    ProviderError,
    ProviderErrorCode,
    ProviderMetadata,
    ProviderType,
)


UsageOperationType = Literal[
    "itinerary_generation",
    "subscriber_chat_message",
    "llm_completion",
    "poi_verification",
    "routing_calculation",
    "vector_search",
    "vector_upsert",
    "ticketing_lookup",
    "tts_narration",
]


@dataclass(frozen=True)
class ProviderUsageRecord:
    provider_type: ProviderType
    operation_type: UsageOperationType
    request_count: int = 1
    estimated_tokens: int | None = None
    estimated_cost_usd: float | None = None
    user_id: str | None = None
    anonymous_session_key: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    provider_metadata: dict[str, Any] = field(default_factory=dict)
    allowed: bool = True
    block_reason: str | None = None


class InMemoryProviderUsageStore:
    """Local-only metering store for development and standard tests."""

    def __init__(self) -> None:
        self.records: list[ProviderUsageRecord] = []

    def add(self, record: ProviderUsageRecord) -> None:
        self.records.append(record)

    def count_for_day(
        self,
        *,
        operation_type: UsageOperationType,
        day: datetime,
        user_id: str | None = None,
        anonymous_session_key: str | None = None,
    ) -> int:
        return sum(
            record.request_count
            for record in self.records
            if record.allowed
            and record.operation_type == operation_type
            and _same_utc_day(record.timestamp, day)
            and record.user_id == user_id
            and record.anonymous_session_key == anonymous_session_key
        )

    def estimated_cost_for_day(self, *, day: datetime) -> float:
        return sum(
            record.estimated_cost_usd or 0
            for record in self.records
            if record.allowed and _same_utc_day(record.timestamp, day)
        )


class ProviderUsageGuard:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        store: InMemoryProviderUsageStore | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.store = store or InMemoryProviderUsageStore()

    def guard_itinerary_generation(
        self,
        *,
        user_id: str | None = None,
        anonymous_session_key: str | None = "anonymous",
        at: datetime | None = None,
    ) -> None:
        at = _utc_now(at)
        limit = (
            self.settings.registered_user_itinerary_generations_per_day
            if user_id
            else self.settings.anonymous_itinerary_generations_per_day
        )
        self._guard_daily_count(
            provider_type=ProviderType.LLM,
            operation_type="itinerary_generation",
            limit=limit,
            user_id=user_id,
            anonymous_session_key=None if user_id else anonymous_session_key,
            at=at,
            code=ProviderErrorCode.RATE_LIMITED,
            message="Daily itinerary generation limit exceeded.",
        )

    def guard_subscriber_chat(
        self,
        *,
        user_id: str,
        at: datetime | None = None,
    ) -> None:
        self._guard_daily_count(
            provider_type=ProviderType.LLM,
            operation_type="subscriber_chat_message",
            limit=self.settings.subscriber_chat_messages_per_day,
            user_id=user_id,
            anonymous_session_key=None,
            at=_utc_now(at),
            code=ProviderErrorCode.QUOTA_EXCEEDED,
            message="Daily subscriber chat message quota exceeded.",
        )

    def guard_llm_request(
        self,
        *,
        input_text: str,
        estimated_output_tokens: int | None = None,
        at: datetime | None = None,
    ) -> None:
        at = _utc_now(at)
        if len(input_text) > self.settings.llm_max_input_chars:
            self._block(
                provider_type=ProviderType.LLM,
                operation_type="llm_completion",
                at=at,
                code=ProviderErrorCode.INPUT_TOO_LARGE,
                message=(
                    "LLM input is too large; maximum is "
                    f"{self.settings.llm_max_input_chars} characters."
                ),
                estimated_tokens=_estimate_tokens(input_text),
            )
        if estimated_output_tokens and estimated_output_tokens > self.settings.llm_max_output_tokens:
            self._block(
                provider_type=ProviderType.LLM,
                operation_type="llm_completion",
                at=at,
                code=ProviderErrorCode.INPUT_TOO_LARGE,
                message=(
                    "Requested LLM output is too large; maximum is "
                    f"{self.settings.llm_max_output_tokens} tokens."
                ),
                estimated_tokens=estimated_output_tokens,
            )
        self._record(
            provider_type=ProviderType.LLM,
            operation_type="llm_completion",
            at=at,
            estimated_tokens=_estimate_tokens(input_text),
        )

    def guard_live_llm_completion(
        self,
        *,
        call_count: int,
        at: datetime | None = None,
    ) -> None:
        at = _utc_now(at)
        per_request_limit = self.settings.llm_max_live_calls_per_request
        if call_count > per_request_limit:
            self._block(
                provider_type=ProviderType.LLM,
                operation_type="llm_completion",
                at=at,
                code=ProviderErrorCode.RATE_LIMITED,
                message=(
                    "Live LLM call limit exceeded for this request; maximum is "
                    f"{per_request_limit} completion call(s)."
                ),
                request_count=call_count,
            )

        daily_limit = self.settings.llm_daily_live_request_ceiling
        used = self.store.count_for_day(
            operation_type="llm_completion",
            day=at,
            anonymous_session_key="live-llm-global",
        )
        if used >= daily_limit:
            self._block(
                provider_type=ProviderType.LLM,
                operation_type="llm_completion",
                at=at,
                code=ProviderErrorCode.QUOTA_EXCEEDED,
                message=f"Daily live LLM completion limit exceeded. Limit: {daily_limit} per day.",
                anonymous_session_key="live-llm-global",
            )
        self._record(
            provider_type=ProviderType.LLM,
            operation_type="llm_completion",
            at=at,
            anonymous_session_key="live-llm-global",
        )

    def guard_itinerary_request_bounds(self, *, duration_days: int) -> None:
        limit = self.settings.itinerary_generation_max_days
        if duration_days > limit:
            self._block(
                provider_type=ProviderType.LLM,
                operation_type="itinerary_generation",
                at=_utc_now(),
                code=ProviderErrorCode.INPUT_TOO_LARGE,
                message=f"Itinerary duration is too large; maximum is {limit} day(s).",
                request_count=duration_days,
            )

    def guard_vector_search(self, *, limit: int, at: datetime | None = None) -> None:
        if limit > self.settings.vector_search_max_results:
            self._block(
                provider_type=ProviderType.VECTOR_DB,
                operation_type="vector_search",
                at=_utc_now(at),
                code=ProviderErrorCode.UNSUPPORTED_BATCH_SIZE,
                message=(
                    "Vector search result limit is too high; maximum is "
                    f"{self.settings.vector_search_max_results}."
                ),
            )
        self._record(
            provider_type=ProviderType.VECTOR_DB,
            operation_type="vector_search",
            at=_utc_now(at),
        )

    def guard_vector_upsert(self, *, text: str, at: datetime | None = None) -> None:
        self._record(
            provider_type=ProviderType.VECTOR_DB,
            operation_type="vector_upsert",
            at=_utc_now(at),
            estimated_tokens=_estimate_tokens(text),
        )

    def guard_poi_verification_batch(self, *, request_count: int, at: datetime | None = None) -> None:
        if request_count > self.settings.poi_verification_max_batch_size:
            self._block(
                provider_type=ProviderType.POI_VERIFICATION,
                operation_type="poi_verification",
                at=_utc_now(at),
                code=ProviderErrorCode.UNSUPPORTED_BATCH_SIZE,
                message=(
                    "POI verification batch is too large; maximum is "
                    f"{self.settings.poi_verification_max_batch_size}."
                ),
                request_count=request_count,
            )
        self._record(
            provider_type=ProviderType.POI_VERIFICATION,
            operation_type="poi_verification",
            at=_utc_now(at),
            request_count=request_count,
        )

    def guard_routing_calculation(self, *, stop_count: int, at: datetime | None = None) -> None:
        if stop_count > self.settings.routing_max_stops:
            self._block(
                provider_type=ProviderType.ROUTING,
                operation_type="routing_calculation",
                at=_utc_now(at),
                code=ProviderErrorCode.TOO_MANY_STOPS,
                message=f"Route has too many stops; maximum is {self.settings.routing_max_stops}.",
                request_count=stop_count,
            )
        self._record(
            provider_type=ProviderType.ROUTING,
            operation_type="routing_calculation",
            at=_utc_now(at),
            request_count=max(1, stop_count),
        )

    def guard_ticketing_lookup(self, *, request_count: int = 1, at: datetime | None = None) -> None:
        if request_count > self.settings.ticketing_lookup_max_requests_per_itinerary:
            self._block(
                provider_type=ProviderType.TICKETING,
                operation_type="ticketing_lookup",
                at=_utc_now(at),
                code=ProviderErrorCode.UNSUPPORTED_BATCH_SIZE,
                message=(
                    "Ticketing lookup batch is too large; maximum is "
                    f"{self.settings.ticketing_lookup_max_requests_per_itinerary}."
                ),
                request_count=request_count,
            )
        self._record(
            provider_type=ProviderType.TICKETING,
            operation_type="ticketing_lookup",
            at=_utc_now(at),
            request_count=request_count,
        )

    def guard_tts_narration(self, *, text: str, at: datetime | None = None) -> None:
        self._record(
            provider_type=ProviderType.TTS,
            operation_type="tts_narration",
            at=_utc_now(at),
            estimated_tokens=_estimate_tokens(text),
        )

    def guard_estimated_cost(
        self,
        *,
        provider_type: ProviderType,
        operation_type: UsageOperationType,
        estimated_cost_usd: float,
        at: datetime | None = None,
    ) -> None:
        at = _utc_now(at)
        ceiling = self.settings.provider_daily_cost_ceiling_usd
        if estimated_cost_usd > 0 and self.store.estimated_cost_for_day(day=at) + estimated_cost_usd > ceiling:
            self._block(
                provider_type=provider_type,
                operation_type=operation_type,
                at=at,
                code=ProviderErrorCode.COST_LIMIT_EXCEEDED,
                message=f"Provider daily estimated cost ceiling exceeded: ${ceiling:.2f}.",
                estimated_cost_usd=estimated_cost_usd,
            )
        self._record(
            provider_type=provider_type,
            operation_type=operation_type,
            at=at,
            estimated_cost_usd=estimated_cost_usd,
        )

    def _guard_daily_count(
        self,
        *,
        provider_type: ProviderType,
        operation_type: UsageOperationType,
        limit: int,
        user_id: str | None,
        anonymous_session_key: str | None,
        at: datetime,
        code: ProviderErrorCode,
        message: str,
    ) -> None:
        used = self.store.count_for_day(
            operation_type=operation_type,
            day=at,
            user_id=user_id,
            anonymous_session_key=anonymous_session_key,
        )
        if used >= limit:
            self._block(
                provider_type=provider_type,
                operation_type=operation_type,
                at=at,
                code=code,
                message=f"{message} Limit: {limit} per day.",
                user_id=user_id,
                anonymous_session_key=anonymous_session_key,
            )
        self._record(
            provider_type=provider_type,
            operation_type=operation_type,
            at=at,
            user_id=user_id,
            anonymous_session_key=anonymous_session_key,
        )

    def _block(
        self,
        *,
        provider_type: ProviderType,
        operation_type: UsageOperationType,
        at: datetime,
        code: ProviderErrorCode,
        message: str,
        request_count: int = 1,
        estimated_tokens: int | None = None,
        estimated_cost_usd: float | None = None,
        user_id: str | None = None,
        anonymous_session_key: str | None = None,
    ) -> None:
        self._record(
            provider_type=provider_type,
            operation_type=operation_type,
            at=at,
            request_count=request_count,
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=estimated_cost_usd,
            user_id=user_id,
            anonymous_session_key=anonymous_session_key,
            allowed=False,
            block_reason=code.value,
        )
        raise ProviderError(
            code,
            message,
            metadata=ProviderMetadata(
                provider_name="local_usage_policy",
                provider_type=provider_type.value,
                generated_at=at.isoformat(),
            ),
        )

    def _record(
        self,
        *,
        provider_type: ProviderType,
        operation_type: UsageOperationType,
        at: datetime,
        request_count: int = 1,
        estimated_tokens: int | None = None,
        estimated_cost_usd: float | None = None,
        user_id: str | None = None,
        anonymous_session_key: str | None = None,
        allowed: bool = True,
        block_reason: str | None = None,
    ) -> None:
        self.store.add(
            record := ProviderUsageRecord(
                provider_type=provider_type,
                operation_type=operation_type,
                request_count=request_count,
                estimated_tokens=estimated_tokens,
                estimated_cost_usd=estimated_cost_usd,
                user_id=user_id,
                anonymous_session_key=anonymous_session_key,
                timestamp=at,
                allowed=allowed,
                block_reason=block_reason,
            )
        )
        if allowed:
            log_event(
                EventName.RATE_LIMIT_ALLOWED,
                category="usage_policy",
                provider_type=provider_type.value,
                operation=operation_type,
                request_count=request_count,
                estimated_tokens=estimated_tokens,
                estimated_cost_usd=estimated_cost_usd,
                user_scoped=bool(user_id),
                anonymous_scoped=bool(anonymous_session_key),
            )
        else:
            log_event(
                EventName.RATE_LIMIT_BLOCKED,
                category="usage_policy",
                provider_type=provider_type.value,
                operation=operation_type,
                request_count=request_count,
                block_reason=block_reason,
                user_scoped=bool(user_id),
                anonymous_scoped=bool(anonymous_session_key),
            )
        record_provider_telemetry(
            ProviderTelemetry(
                provider_type=provider_type.value,
                provider_name="local_usage_policy",
                operation=operation_type,
                success=allowed,
                estimated_cost_usd=estimated_cost_usd,
                error_type=block_reason,
            )
        )


@lru_cache
def get_usage_guard() -> ProviderUsageGuard:
    return ProviderUsageGuard(settings=get_settings())


def _same_utc_day(left: datetime, right: datetime) -> bool:
    return left.astimezone(UTC).date() == right.astimezone(UTC).date()


def _utc_now(value: datetime | None = None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / 4))
