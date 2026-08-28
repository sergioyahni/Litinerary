from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from hashlib import sha256
from typing import Any, Literal, Protocol

from sqlalchemy import case, delete, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.observability import (
    EventName,
    ProviderTelemetry,
    log_event,
    record_provider_telemetry,
)
from app.models import UsageLimitCounterModel
from app.services.provider_contracts import (
    ProviderError,
    ProviderErrorCode,
    ProviderMetadata,
    ProviderType,
)


UsageOperationType = Literal[
    "itinerary_generation",
    "itinerary_adaptation",
    "subscriber_chat_message",
    "llm_completion",
    "poi_verification",
    "routing_calculation",
    "vector_search",
    "vector_upsert",
    "ticketing_lookup",
    "tts_narration",
    "provider_request_budget",
    "provider_cost_budget",
]

WindowKind = Literal["minute", "day"]


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


@dataclass(frozen=True)
class ReservationResult:
    allowed: bool
    retry_after_seconds: int | None = None


class UsageCounterStore(Protocol):
    durable: bool

    def reserve_units(
        self,
        *,
        subject_type: str,
        subject_key: str,
        action: str,
        units: int,
        limit_units: int,
        window_start: datetime,
        window_end: datetime,
        at: datetime,
    ) -> ReservationResult:
        ...

    def record_event(self, record: ProviderUsageRecord) -> None:
        ...

    def refund_units(
        self,
        *,
        subject_type: str,
        subject_key: str,
        action: str,
        units: int,
        window_start: datetime,
    ) -> None:
        ...

    def cleanup_expired(self, *, before: datetime) -> int:
        ...


class InMemoryProviderUsageStore:
    """Local-only metering store for development and standard tests."""

    durable = False

    def __init__(self) -> None:
        self.records: list[ProviderUsageRecord] = []
        self.counters: dict[tuple[str, str, str, str], int] = {}

    def add(self, record: ProviderUsageRecord) -> None:
        self.records.append(record)

    def record_event(self, record: ProviderUsageRecord) -> None:
        self.add(record)

    def reserve_units(
        self,
        *,
        subject_type: str,
        subject_key: str,
        action: str,
        units: int,
        limit_units: int,
        window_start: datetime,
        window_end: datetime,
        at: datetime,
    ) -> ReservationResult:
        counter_key = (subject_type, subject_key, action, window_start.isoformat())
        used = self.counters.get(counter_key, 0)
        if used + units > limit_units:
            return ReservationResult(
                allowed=False,
                retry_after_seconds=_retry_after_seconds(window_end, at),
            )
        self.counters[counter_key] = used + units
        return ReservationResult(allowed=True)

    def refund_units(
        self,
        *,
        subject_type: str,
        subject_key: str,
        action: str,
        units: int,
        window_start: datetime,
    ) -> None:
        counter_key = (subject_type, subject_key, action, window_start.isoformat())
        if counter_key in self.counters:
            self.counters[counter_key] = max(0, self.counters[counter_key] - units)

    def cleanup_expired(self, *, before: datetime) -> int:
        original_count = len(self.records)
        self.records = [
            record for record in self.records if record.timestamp.astimezone(UTC) >= before
        ]
        self.counters = {
            key: value
            for key, value in self.counters.items()
            if datetime.fromisoformat(key[3]).astimezone(UTC) >= before
        }
        return original_count - len(self.records)

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


class DatabaseUsageCounterStore:
    """Durable SQL-backed counters with atomic per-window reservations."""

    durable = True

    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        if session_factory is None:
            from app.core.database import SessionLocal

            session_factory = SessionLocal
        self.session_factory = session_factory

    def record_event(self, record: ProviderUsageRecord) -> None:
        # Durable counters reserve usage in reserve_units. Non-limited event rows are
        # intentionally not written so the table remains bounded by window counters.
        return None

    def reserve_units(
        self,
        *,
        subject_type: str,
        subject_key: str,
        action: str,
        units: int,
        limit_units: int,
        window_start: datetime,
        window_end: datetime,
        at: datetime,
    ) -> ReservationResult:
        counter_id = _counter_id(subject_type, subject_key, action, window_start)
        now_iso = at.isoformat()
        values = {
            "id": counter_id,
            "subject_type": subject_type,
            "subject_key": subject_key,
            "action": action,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "units_used": 0,
            "limit_units": limit_units,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        with self.session_factory() as db:
            with db.begin():
                self._insert_counter_if_missing(db, values)
                result = db.execute(
                    update(UsageLimitCounterModel)
                    .where(
                        UsageLimitCounterModel.id == counter_id,
                        UsageLimitCounterModel.units_used + units <= limit_units,
                    )
                    .values(
                        units_used=UsageLimitCounterModel.units_used + units,
                        limit_units=limit_units,
                        updated_at=now_iso,
                    )
                )
                if result.rowcount == 1:
                    return ReservationResult(allowed=True)
                return ReservationResult(
                    allowed=False,
                    retry_after_seconds=_retry_after_seconds(window_end, at),
                )

    def cleanup_expired(self, *, before: datetime) -> int:
        with self.session_factory() as db:
            with db.begin():
                result = db.execute(
                    delete(UsageLimitCounterModel).where(
                        UsageLimitCounterModel.window_end < before.isoformat()
                    )
                )
                return int(result.rowcount or 0)

    def refund_units(
        self,
        *,
        subject_type: str,
        subject_key: str,
        action: str,
        units: int,
        window_start: datetime,
    ) -> None:
        counter_id = _counter_id(subject_type, subject_key, action, window_start)
        with self.session_factory() as db:
            with db.begin():
                db.execute(
                    update(UsageLimitCounterModel)
                    .where(UsageLimitCounterModel.id == counter_id)
                    .values(
                        units_used=case(
                            (
                                UsageLimitCounterModel.units_used >= units,
                                UsageLimitCounterModel.units_used - units,
                            ),
                            else_=0,
                        )
                    )
                )

    def _insert_counter_if_missing(self, db: Session, values: dict[str, Any]) -> None:
        dialect_name = db.bind.dialect.name if db.bind is not None else ""
        if dialect_name == "sqlite":
            statement = sqlite_insert(UsageLimitCounterModel).values(**values)
            db.execute(statement.on_conflict_do_nothing(index_elements=["id"]))
            return
        if dialect_name == "postgresql":
            statement = postgresql_insert(UsageLimitCounterModel).values(**values)
            db.execute(statement.on_conflict_do_nothing(index_elements=["id"]))
            return
        existing = db.get(UsageLimitCounterModel, values["id"])
        if existing is None:
            db.add(UsageLimitCounterModel(**values))
            db.flush()


class ProviderUsageGuard:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        store: UsageCounterStore | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.store = store or (
            DatabaseUsageCounterStore()
            if self.settings.enable_durable_usage_controls
            else InMemoryProviderUsageStore()
        )

    def guard_itinerary_generation(
        self,
        *,
        user_id: str | None = None,
        anonymous_session_key: str | None = "anonymous-global",
        at: datetime | None = None,
    ) -> None:
        at = _utc_now(at)
        rate_limit = (
            self.settings.registered_user_itinerary_generations_per_minute
            if user_id
            else self.settings.anonymous_itinerary_generations_per_minute
        )
        daily_limit = (
            self.settings.registered_user_itinerary_generations_per_day
            if user_id
            else self.settings.anonymous_itinerary_generations_per_day
        )
        subject_type, subject_key = _usage_subject(
            user_id=user_id,
            anonymous_session_key=None if user_id else anonymous_session_key,
        )
        self._reserve_composite_windows(
            provider_type=ProviderType.LLM,
            operation_type="itinerary_generation",
            subject_type=subject_type,
            subject_key=subject_key,
            at=at,
            windows=[
                (
                    "minute",
                    rate_limit,
                    ProviderErrorCode.RATE_LIMITED,
                    "Itinerary generation rate limit exceeded.",
                ),
                (
                    "day",
                    daily_limit,
                    ProviderErrorCode.RATE_LIMITED,
                    "Daily itinerary generation limit exceeded.",
                ),
            ],
        )

    def guard_subscriber_chat(
        self,
        *,
        user_id: str,
        at: datetime | None = None,
    ) -> None:
        at = _utc_now(at)
        subject_type, subject_key = _usage_subject(user_id=user_id)
        self._reserve_composite_windows(
            provider_type=ProviderType.LLM,
            operation_type="subscriber_chat_message",
            subject_type=subject_type,
            subject_key=subject_key,
            at=at,
            windows=[
                (
                    "minute",
                    self.settings.subscriber_chat_messages_per_minute,
                    ProviderErrorCode.RATE_LIMITED,
                    "Subscriber chat rate limit exceeded.",
                ),
                (
                    "day",
                    self.settings.subscriber_chat_messages_per_day,
                    ProviderErrorCode.QUOTA_EXCEEDED,
                    "Daily subscriber chat message quota exceeded.",
                ),
            ],
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
        self._emit_usage_event(
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

        self._reserve_window(
            provider_type=ProviderType.LLM,
            operation_type="llm_completion",
            subject_type="global",
            subject_key="live-llm",
            window_kind="day",
            limit=self.settings.llm_daily_live_request_ceiling,
            at=at,
            code=ProviderErrorCode.QUOTA_EXCEEDED,
            message="Daily live LLM completion limit exceeded.",
        )
        self._guard_provider_daily_request_budget(
            provider_type=ProviderType.LLM,
            operation_type="llm_completion",
            request_count=1,
            at=at,
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
        at = _utc_now(at)
        if limit > self.settings.vector_search_max_results:
            self._block(
                provider_type=ProviderType.VECTOR_DB,
                operation_type="vector_search",
                at=at,
                code=ProviderErrorCode.UNSUPPORTED_BATCH_SIZE,
                message=(
                    "Vector search result limit is too high; maximum is "
                    f"{self.settings.vector_search_max_results}."
                ),
            )
        self._guard_provider_daily_request_budget(
            provider_type=ProviderType.VECTOR_DB,
            operation_type="vector_search",
            request_count=1,
            at=at,
        )
        self._emit_usage_event(
            provider_type=ProviderType.VECTOR_DB,
            operation_type="vector_search",
            at=at,
        )

    def guard_vector_upsert(self, *, text: str, at: datetime | None = None) -> None:
        at = _utc_now(at)
        self._guard_provider_daily_request_budget(
            provider_type=ProviderType.VECTOR_DB,
            operation_type="vector_upsert",
            request_count=1,
            at=at,
        )
        self._emit_usage_event(
            provider_type=ProviderType.VECTOR_DB,
            operation_type="vector_upsert",
            at=at,
            estimated_tokens=_estimate_tokens(text),
        )

    def guard_poi_verification_batch(self, *, request_count: int, at: datetime | None = None) -> None:
        at = _utc_now(at)
        if request_count > self.settings.poi_verification_max_batch_size:
            self._block(
                provider_type=ProviderType.POI_VERIFICATION,
                operation_type="poi_verification",
                at=at,
                code=ProviderErrorCode.UNSUPPORTED_BATCH_SIZE,
                message=(
                    "POI verification batch is too large; maximum is "
                    f"{self.settings.poi_verification_max_batch_size}."
                ),
                request_count=request_count,
            )
        self._guard_provider_daily_request_budget(
            provider_type=ProviderType.POI_VERIFICATION,
            operation_type="poi_verification",
            request_count=request_count,
            at=at,
        )
        self._emit_usage_event(
            provider_type=ProviderType.POI_VERIFICATION,
            operation_type="poi_verification",
            at=at,
            request_count=request_count,
        )

    def guard_routing_calculation(self, *, stop_count: int, at: datetime | None = None) -> None:
        at = _utc_now(at)
        if stop_count > self.settings.routing_max_stops:
            self._block(
                provider_type=ProviderType.ROUTING,
                operation_type="routing_calculation",
                at=at,
                code=ProviderErrorCode.TOO_MANY_STOPS,
                message=f"Route has too many stops; maximum is {self.settings.routing_max_stops}.",
                request_count=stop_count,
            )
        self._guard_provider_daily_request_budget(
            provider_type=ProviderType.ROUTING,
            operation_type="routing_calculation",
            request_count=max(1, stop_count),
            at=at,
        )
        self._emit_usage_event(
            provider_type=ProviderType.ROUTING,
            operation_type="routing_calculation",
            at=at,
            request_count=max(1, stop_count),
        )

    def guard_ticketing_lookup(self, *, request_count: int = 1, at: datetime | None = None) -> None:
        at = _utc_now(at)
        if request_count > self.settings.ticketing_lookup_max_requests_per_itinerary:
            self._block(
                provider_type=ProviderType.TICKETING,
                operation_type="ticketing_lookup",
                at=at,
                code=ProviderErrorCode.UNSUPPORTED_BATCH_SIZE,
                message=(
                    "Ticketing lookup batch is too large; maximum is "
                    f"{self.settings.ticketing_lookup_max_requests_per_itinerary}."
                ),
                request_count=request_count,
            )
        self._guard_provider_daily_request_budget(
            provider_type=ProviderType.TICKETING,
            operation_type="ticketing_lookup",
            request_count=request_count,
            at=at,
        )
        self._emit_usage_event(
            provider_type=ProviderType.TICKETING,
            operation_type="ticketing_lookup",
            at=at,
            request_count=request_count,
        )

    def guard_tts_narration(self, *, text: str, at: datetime | None = None) -> None:
        at = _utc_now(at)
        self._guard_provider_daily_request_budget(
            provider_type=ProviderType.TTS,
            operation_type="tts_narration",
            request_count=1,
            at=at,
        )
        self._emit_usage_event(
            provider_type=ProviderType.TTS,
            operation_type="tts_narration",
            at=at,
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
        if estimated_cost_usd <= 0:
            self._emit_usage_event(
                provider_type=provider_type,
                operation_type=operation_type,
                at=at,
                estimated_cost_usd=estimated_cost_usd,
            )
            return
        units = _cost_units(estimated_cost_usd)
        limit_units = _cost_units(ceiling)
        self._reserve_window(
            provider_type=provider_type,
            operation_type="provider_cost_budget",
            subject_type="global",
            subject_key="provider-cost",
            window_kind="day",
            limit=limit_units,
            at=at,
            code=ProviderErrorCode.COST_LIMIT_EXCEEDED,
            message="Provider daily estimated cost ceiling exceeded.",
            units=units,
            estimated_cost_usd=estimated_cost_usd,
        )

    def cleanup_expired_counters(self, *, at: datetime | None = None) -> int:
        retention_days = self.settings.usage_counter_retention_days
        before = _utc_now(at) - timedelta(days=retention_days)
        return self.store.cleanup_expired(before=before)

    def _guard_provider_daily_request_budget(
        self,
        *,
        provider_type: ProviderType,
        operation_type: UsageOperationType,
        request_count: int,
        at: datetime,
    ) -> None:
        if not _real_provider_enabled(self.settings, provider_type):
            return
        self._reserve_window(
            provider_type=provider_type,
            operation_type="provider_request_budget",
            subject_type="global",
            subject_key=f"provider:{provider_type.value}",
            window_kind="day",
            limit=self.settings.provider_daily_request_ceiling,
            at=at,
            code=ProviderErrorCode.QUOTA_EXCEEDED,
            message=f"Daily {provider_type.value} provider request budget exceeded.",
            units=max(1, request_count),
        )

    def _reserve_composite_windows(
        self,
        *,
        provider_type: ProviderType,
        operation_type: UsageOperationType,
        subject_type: str,
        subject_key: str,
        at: datetime,
        windows: list[tuple[WindowKind, int, ProviderErrorCode, str]],
    ) -> None:
        reserved: list[tuple[WindowKind, datetime]] = []
        try:
            for window_kind, limit, code, message in windows:
                self._reserve_window(
                    provider_type=provider_type,
                    operation_type=operation_type,
                    subject_type=subject_type,
                    subject_key=subject_key,
                    window_kind=window_kind,
                    limit=limit,
                    at=at,
                    code=code,
                    message=message,
                )
                window_start, _ = _window_bounds(at, window_kind)
                reserved.append((window_kind, window_start))
        except ProviderError:
            for window_kind, window_start in reserved:
                try:
                    self.store.refund_units(
                        subject_type=subject_type,
                        subject_key=subject_key,
                        action=f"{operation_type}:{window_kind}",
                        units=1,
                        window_start=window_start,
                    )
                except SQLAlchemyError:
                    log_event(
                        EventName.USAGE_LIMITER_FAILED,
                        level=40,
                        category="usage_policy",
                        provider_type=provider_type.value,
                        operation=operation_type,
                        durable=self.store.durable,
                        phase="refund",
                    )
            raise

    def _reserve_window(
        self,
        *,
        provider_type: ProviderType,
        operation_type: UsageOperationType,
        subject_type: str,
        subject_key: str,
        window_kind: WindowKind,
        limit: int,
        at: datetime,
        code: ProviderErrorCode,
        message: str,
        units: int = 1,
        estimated_cost_usd: float | None = None,
    ) -> None:
        window_start, window_end = _window_bounds(at, window_kind)
        counter_action = f"{operation_type}:{window_kind}"
        try:
            result = self.store.reserve_units(
                subject_type=subject_type,
                subject_key=subject_key,
                action=counter_action,
                units=units,
                limit_units=limit,
                window_start=window_start,
                window_end=window_end,
                at=at,
            )
        except SQLAlchemyError as exc:
            log_event(
                EventName.USAGE_LIMITER_FAILED,
                level=40,
                category="usage_policy",
                provider_type=provider_type.value,
                operation=operation_type,
                durable=self.store.durable,
                error_type=exc.__class__.__name__,
            )
            raise ProviderError(
                ProviderErrorCode.UNAVAILABLE,
                "Durable usage limiter is unavailable; refusing cost-sensitive work.",
                metadata=ProviderMetadata(
                    provider_name="durable_usage_policy",
                    provider_type=provider_type.value,
                    generated_at=at.isoformat(),
                ),
            ) from exc

        if not result.allowed:
            self._block(
                provider_type=provider_type,
                operation_type=operation_type,
                at=at,
                code=code,
                message=f"{message} Limit: {limit} per {window_kind}.",
                request_count=units,
                user_id=subject_key if subject_type == "user" else None,
                anonymous_session_key=subject_key if subject_type == "anonymous" else None,
                retry_after_seconds=result.retry_after_seconds,
                estimated_cost_usd=estimated_cost_usd,
                record_block=False,
            )
        self._emit_usage_event(
            provider_type=provider_type,
            operation_type=operation_type,
            at=at,
            request_count=units,
            user_id=subject_key if subject_type == "user" else None,
            anonymous_session_key=subject_key if subject_type == "anonymous" else None,
            estimated_cost_usd=estimated_cost_usd,
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
        retry_after_seconds: int | None = None,
        record_block: bool = True,
    ) -> None:
        if record_block:
            self._emit_usage_event(
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
        else:
            log_event(
                EventName.RATE_LIMIT_BLOCKED,
                category="usage_policy",
                provider_type=provider_type.value,
                operation=operation_type,
                request_count=request_count,
                block_reason=code.value,
                user_scoped=bool(user_id),
                anonymous_scoped=bool(anonymous_session_key),
                durable=self.store.durable,
            )
        raise ProviderError(
            code,
            message,
            metadata=ProviderMetadata(
                provider_name="durable_usage_policy" if self.store.durable else "local_usage_policy",
                provider_type=provider_type.value,
                generated_at=at.isoformat(),
            ),
            retry_after_seconds=retry_after_seconds,
        )

    def _emit_usage_event(
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
        record = ProviderUsageRecord(
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
        self.store.record_event(record)
        log_event(
            EventName.RATE_LIMIT_ALLOWED if allowed else EventName.RATE_LIMIT_BLOCKED,
            category="usage_policy",
            provider_type=provider_type.value,
            operation=operation_type,
            request_count=request_count,
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=estimated_cost_usd,
            block_reason=block_reason,
            user_scoped=bool(user_id),
            anonymous_scoped=bool(anonymous_session_key),
            durable=self.store.durable,
        )
        record_provider_telemetry(
            ProviderTelemetry(
                provider_type=provider_type.value,
                provider_name="durable_usage_policy" if self.store.durable else "local_usage_policy",
                operation=operation_type,
                success=allowed,
                estimated_cost_usd=estimated_cost_usd,
                error_type=block_reason,
            )
        )


@lru_cache
def get_usage_guard() -> ProviderUsageGuard:
    return ProviderUsageGuard(settings=get_settings())


def validate_usage_startup(settings: Settings | None = None) -> None:
    resolved = settings or get_settings()
    errors = resolved.usage_control_validation_errors()
    if errors:
        raise RuntimeError(
            f"Usage-control configuration is incomplete for APP_ENV={resolved.app_env}: "
            + " ".join(errors)
        )


def cleanup_expired_usage_counters(
    *,
    settings: Settings | None = None,
    store: UsageCounterStore | None = None,
    at: datetime | None = None,
) -> int:
    resolved = settings or get_settings()
    resolved_at = _utc_now(at)
    before = resolved_at - timedelta(days=resolved.usage_counter_retention_days)
    counter_store = store or (
        DatabaseUsageCounterStore()
        if resolved.enable_durable_usage_controls
        else InMemoryProviderUsageStore()
    )
    try:
        rows_removed = counter_store.cleanup_expired(before=before)
    except Exception as exc:
        log_event(
            EventName.USAGE_COUNTER_CLEANUP_FAILED,
            level=40,
            category="usage_policy",
            operation="cleanup_expired_usage_counters",
            durable=counter_store.durable,
            retention_days=resolved.usage_counter_retention_days,
            error_type=exc.__class__.__name__,
            success=False,
        )
        raise
    log_event(
        EventName.USAGE_COUNTER_CLEANUP_COMPLETED,
        category="usage_policy",
        operation="cleanup_expired_usage_counters",
        durable=counter_store.durable,
        retention_days=resolved.usage_counter_retention_days,
        rows_removed=rows_removed,
        cutoff=before.isoformat(),
        success=True,
    )
    return rows_removed


def _usage_subject(
    *,
    user_id: str | None = None,
    anonymous_session_key: str | None = None,
) -> tuple[str, str]:
    if user_id:
        return "user", user_id
    return "anonymous", anonymous_session_key or "anonymous-global"


def _record_subject_type(record: ProviderUsageRecord) -> str:
    if record.user_id:
        return "user"
    if record.anonymous_session_key:
        return "anonymous"
    return "global"


def _record_subject_key(record: ProviderUsageRecord) -> str:
    return record.user_id or record.anonymous_session_key or "global"


def _window_bounds(at: datetime, window_kind: WindowKind) -> tuple[datetime, datetime]:
    at = _utc_now(at)
    if window_kind == "minute":
        start = at.replace(second=0, microsecond=0)
        return start, start + timedelta(minutes=1)
    start = at.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def _retry_after_seconds(window_end: datetime, at: datetime) -> int:
    return max(0, round((window_end - at).total_seconds()))


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


def _cost_units(estimated_cost_usd: float) -> int:
    return max(0, round(estimated_cost_usd * 1_000_000))


def _counter_id(
    subject_type: str,
    subject_key: str,
    action: str,
    window_start: datetime,
) -> str:
    raw = f"{subject_type}:{subject_key}:{action}:{window_start.isoformat()}"
    digest = sha256(raw.encode("utf-8")).hexdigest()[:32]
    return f"usage-{digest}"


def _real_provider_enabled(settings: Settings, provider_type: ProviderType) -> bool:
    if provider_type in {ProviderType.LLM, ProviderType.EMBEDDING}:
        return settings.enable_real_llm
    if provider_type == ProviderType.VECTOR_DB:
        return settings.enable_real_vector_db
    if provider_type == ProviderType.POI_VERIFICATION:
        return settings.enable_real_poi_provider
    if provider_type == ProviderType.ROUTING:
        return settings.enable_real_routing
    if provider_type == ProviderType.TICKETING:
        return settings.enable_real_ticketing
    if provider_type == ProviderType.TTS:
        return settings.enable_real_tts
    if provider_type == ProviderType.AFFILIATE:
        return settings.enable_affiliate_links
    return False
