from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import Base
from app.models import UsageLimitCounterModel
from app.services.fake_vector_store import FakeEmbeddingProvider, InMemoryVectorStore
from app.services.provider_contracts import ProviderError, ProviderErrorCode, ProviderType
from app.services.usage_policy import (
    DatabaseUsageCounterStore,
    InMemoryProviderUsageStore,
    ProviderUsageGuard,
    get_usage_guard,
    validate_usage_startup,
)
from app.services.vector_service import VectorService


@pytest.fixture(autouse=True)
def clear_settings_and_usage_guard_cache():
    get_settings.cache_clear()
    get_usage_guard.cache_clear()
    yield
    get_usage_guard.cache_clear()
    get_settings.cache_clear()


def _durable_store(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'usage-counters.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False, "timeout": 30})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return DatabaseUsageCounterStore(TestingSessionLocal), TestingSessionLocal, engine


def test_anonymous_generation_limit_blocks_after_daily_allowance() -> None:
    guard = ProviderUsageGuard(
        settings=Settings(anonymous_itinerary_generations_per_day=1),
        store=InMemoryProviderUsageStore(),
    )
    now = datetime(2026, 6, 15, tzinfo=UTC)

    guard.guard_itinerary_generation(anonymous_session_key="session-a", at=now)

    with pytest.raises(ProviderError) as exc_info:
        guard.guard_itinerary_generation(anonymous_session_key="session-a", at=now)

    assert exc_info.value.code == ProviderErrorCode.RATE_LIMITED


def test_registered_user_generation_limit_is_separate_from_anonymous_limit() -> None:
    guard = ProviderUsageGuard(
        settings=Settings(registered_user_itinerary_generations_per_day=1),
        store=InMemoryProviderUsageStore(),
    )
    now = datetime(2026, 6, 15, tzinfo=UTC)

    guard.guard_itinerary_generation(user_id="user-1", at=now)

    with pytest.raises(ProviderError) as exc_info:
        guard.guard_itinerary_generation(user_id="user-1", at=now)

    assert exc_info.value.code == ProviderErrorCode.RATE_LIMITED


def test_subscriber_chat_limit_blocks_after_daily_quota() -> None:
    guard = ProviderUsageGuard(
        settings=Settings(subscriber_chat_messages_per_day=1),
        store=InMemoryProviderUsageStore(),
    )

    guard.guard_subscriber_chat(user_id="subscriber-1")

    with pytest.raises(ProviderError) as exc_info:
        guard.guard_subscriber_chat(user_id="subscriber-1")

    assert exc_info.value.code == ProviderErrorCode.QUOTA_EXCEEDED


def test_routing_stop_limit_blocks_large_routes() -> None:
    guard = ProviderUsageGuard(
        settings=Settings(routing_max_stops=2),
        store=InMemoryProviderUsageStore(),
    )

    with pytest.raises(ProviderError) as exc_info:
        guard.guard_routing_calculation(stop_count=3)

    assert exc_info.value.code == ProviderErrorCode.TOO_MANY_STOPS


def test_poi_batch_limit_blocks_unsupported_batch_size() -> None:
    guard = ProviderUsageGuard(
        settings=Settings(poi_verification_max_batch_size=2),
        store=InMemoryProviderUsageStore(),
    )

    with pytest.raises(ProviderError) as exc_info:
        guard.guard_poi_verification_batch(request_count=3)

    assert exc_info.value.code == ProviderErrorCode.UNSUPPORTED_BATCH_SIZE


def test_llm_input_size_limit_blocks_large_prompts() -> None:
    guard = ProviderUsageGuard(
        settings=Settings(llm_max_input_chars=10),
        store=InMemoryProviderUsageStore(),
    )

    with pytest.raises(ProviderError) as exc_info:
        guard.guard_llm_request(input_text="x" * 11)

    assert exc_info.value.code == ProviderErrorCode.INPUT_TOO_LARGE


def test_itinerary_duration_limit_blocks_large_requests() -> None:
    guard = ProviderUsageGuard(
        settings=Settings(itinerary_generation_max_days=1),
        store=InMemoryProviderUsageStore(),
    )

    with pytest.raises(ProviderError) as exc_info:
        guard.guard_itinerary_request_bounds(duration_days=2)

    assert exc_info.value.code == ProviderErrorCode.INPUT_TOO_LARGE


def test_live_llm_per_request_call_limit_blocks_extra_completion() -> None:
    guard = ProviderUsageGuard(
        settings=Settings(llm_max_live_calls_per_request=1, llm_daily_live_request_ceiling=10),
        store=InMemoryProviderUsageStore(),
    )

    guard.guard_live_llm_completion(call_count=1)

    with pytest.raises(ProviderError) as exc_info:
        guard.guard_live_llm_completion(call_count=2)

    assert exc_info.value.code == ProviderErrorCode.RATE_LIMITED


def test_live_llm_daily_completion_ceiling_blocks_after_limit() -> None:
    guard = ProviderUsageGuard(
        settings=Settings(llm_max_live_calls_per_request=10, llm_daily_live_request_ceiling=1),
        store=InMemoryProviderUsageStore(),
    )

    guard.guard_live_llm_completion(call_count=1)

    with pytest.raises(ProviderError) as exc_info:
        guard.guard_live_llm_completion(call_count=1)

    assert exc_info.value.code == ProviderErrorCode.QUOTA_EXCEEDED


def test_vector_result_limit_blocks_large_searches() -> None:
    guard = ProviderUsageGuard(
        settings=Settings(vector_search_max_results=2),
        store=InMemoryProviderUsageStore(),
    )

    with pytest.raises(ProviderError) as exc_info:
        guard.guard_vector_search(limit=3)

    assert exc_info.value.code == ProviderErrorCode.UNSUPPORTED_BATCH_SIZE


def test_cost_ceiling_blocks_estimated_provider_spend() -> None:
    guard = ProviderUsageGuard(
        settings=Settings(provider_daily_cost_ceiling_usd=0.01),
        store=InMemoryProviderUsageStore(),
    )

    with pytest.raises(ProviderError) as exc_info:
        guard.guard_estimated_cost(
            provider_type=ProviderType.LLM,
            operation_type="llm_completion",
            estimated_cost_usd=0.02,
        )

    assert exc_info.value.code == ProviderErrorCode.COST_LIMIT_EXCEEDED


def test_limit_window_resets_on_next_utc_day() -> None:
    guard = ProviderUsageGuard(
        settings=Settings(anonymous_itinerary_generations_per_day=1),
        store=InMemoryProviderUsageStore(),
    )
    today = datetime(2026, 6, 15, 12, tzinfo=UTC)

    guard.guard_itinerary_generation(anonymous_session_key="session-a", at=today)
    guard.guard_itinerary_generation(
        anonymous_session_key="session-a",
        at=today + timedelta(days=1),
    )

    assert len([record for record in guard.store.records if record.allowed]) == 4


def test_durable_generation_limit_persists_across_guard_instances(tmp_path) -> None:
    store, session_factory, engine = _durable_store(tmp_path)
    settings = Settings(
        enable_durable_usage_controls=True,
        anonymous_itinerary_generations_per_day=1,
        anonymous_itinerary_generations_per_minute=10,
    )
    now = datetime(2026, 8, 15, 10, 0, tzinfo=UTC)

    ProviderUsageGuard(settings=settings, store=store).guard_itinerary_generation(
        anonymous_session_key="browser-session",
        at=now,
    )
    restarted_guard = ProviderUsageGuard(
        settings=settings,
        store=DatabaseUsageCounterStore(session_factory),
    )

    with pytest.raises(ProviderError) as exc_info:
        restarted_guard.guard_itinerary_generation(
            anonymous_session_key="browser-session",
            at=now,
        )

    assert exc_info.value.code == ProviderErrorCode.RATE_LIMITED
    assert exc_info.value.retry_after_seconds is not None
    engine.dispose()


def test_durable_generation_rate_limit_is_concurrency_safe(tmp_path) -> None:
    store, session_factory, engine = _durable_store(tmp_path)
    settings = Settings(
        enable_durable_usage_controls=True,
        anonymous_itinerary_generations_per_day=100,
        anonymous_itinerary_generations_per_minute=5,
    )
    now = datetime(2026, 8, 15, 10, 3, 15, tzinfo=UTC)

    def reserve() -> bool:
        guard = ProviderUsageGuard(
            settings=settings,
            store=DatabaseUsageCounterStore(session_factory),
        )
        try:
            guard.guard_itinerary_generation(
                anonymous_session_key="shared-anonymous",
                at=now,
            )
        except ProviderError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(lambda _: reserve(), range(12)))

    assert results.count(True) == 5
    assert results.count(False) == 7
    with session_factory() as db:
        minute_counter = (
            db.query(UsageLimitCounterModel)
            .filter(UsageLimitCounterModel.action == "itinerary_generation:minute")
            .one()
        )
        day_counter = (
            db.query(UsageLimitCounterModel)
            .filter(UsageLimitCounterModel.action == "itinerary_generation:day")
            .one()
        )
        assert minute_counter.units_used == 5
        assert day_counter.units_used == 5
    engine.dispose()


def test_durable_limits_are_isolated_by_authenticated_user(tmp_path) -> None:
    store, _, engine = _durable_store(tmp_path)
    settings = Settings(
        enable_durable_usage_controls=True,
        registered_user_itinerary_generations_per_day=1,
        registered_user_itinerary_generations_per_minute=10,
    )
    guard = ProviderUsageGuard(settings=settings, store=store)
    now = datetime(2026, 8, 15, 11, tzinfo=UTC)

    guard.guard_itinerary_generation(user_id="reader-a", at=now)
    guard.guard_itinerary_generation(user_id="reader-b", at=now)

    with pytest.raises(ProviderError):
        guard.guard_itinerary_generation(user_id="reader-a", at=now)
    engine.dispose()


def test_durable_provider_request_budget_blocks_real_provider_calls(tmp_path) -> None:
    store, _, engine = _durable_store(tmp_path)
    guard = ProviderUsageGuard(
        settings=Settings(
            enable_durable_usage_controls=True,
            enable_real_routing=True,
            provider_daily_request_ceiling=2,
            routing_max_stops=10,
        ),
        store=store,
    )
    now = datetime(2026, 8, 15, 12, tzinfo=UTC)

    guard.guard_routing_calculation(stop_count=1, at=now)
    guard.guard_routing_calculation(stop_count=1, at=now)

    with pytest.raises(ProviderError) as exc_info:
        guard.guard_routing_calculation(stop_count=1, at=now)

    assert exc_info.value.code == ProviderErrorCode.QUOTA_EXCEEDED
    engine.dispose()


def test_durable_cost_budget_blocks_estimated_spend_after_exact_ceiling(tmp_path) -> None:
    store, _, engine = _durable_store(tmp_path)
    guard = ProviderUsageGuard(
        settings=Settings(enable_durable_usage_controls=True, provider_daily_cost_ceiling_usd=0.02),
        store=store,
    )
    now = datetime(2026, 8, 15, 13, tzinfo=UTC)

    guard.guard_estimated_cost(
        provider_type=ProviderType.LLM,
        operation_type="llm_completion",
        estimated_cost_usd=0.01,
        at=now,
    )
    guard.guard_estimated_cost(
        provider_type=ProviderType.LLM,
        operation_type="llm_completion",
        estimated_cost_usd=0.01,
        at=now,
    )

    with pytest.raises(ProviderError) as exc_info:
        guard.guard_estimated_cost(
            provider_type=ProviderType.LLM,
            operation_type="llm_completion",
            estimated_cost_usd=0.000001,
            at=now,
        )

    assert exc_info.value.code == ProviderErrorCode.COST_LIMIT_EXCEEDED
    engine.dispose()


def test_durable_limiter_fails_closed_when_counter_table_is_missing(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'missing-counter-table.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    guard = ProviderUsageGuard(
        settings=Settings(enable_durable_usage_controls=True),
        store=DatabaseUsageCounterStore(TestingSessionLocal),
    )

    with pytest.raises(ProviderError) as exc_info:
        guard.guard_itinerary_generation(
            anonymous_session_key="anonymous",
            at=datetime(2026, 8, 15, tzinfo=UTC),
        )

    assert exc_info.value.code == ProviderErrorCode.UNAVAILABLE
    engine.dispose()


def test_usage_counter_cleanup_removes_expired_windows(tmp_path) -> None:
    store, session_factory, engine = _durable_store(tmp_path)
    guard = ProviderUsageGuard(
        settings=Settings(enable_durable_usage_controls=True, usage_counter_retention_days=30),
        store=store,
    )
    old = datetime(2026, 6, 1, tzinfo=UTC)
    current = datetime(2026, 8, 15, tzinfo=UTC)

    guard.guard_itinerary_generation(anonymous_session_key="old", at=old)
    guard.guard_itinerary_generation(anonymous_session_key="current", at=current)

    assert guard.cleanup_expired_counters(at=current) == 2
    with session_factory() as db:
        rows = db.query(UsageLimitCounterModel).all()
        assert {row.subject_key for row in rows} == {"current"}
    engine.dispose()


def test_usage_startup_validation_requires_durable_controls_in_deployed_envs() -> None:
    with pytest.raises(RuntimeError) as exc_info:
        validate_usage_startup(Settings(app_env="production", enable_durable_usage_controls=False))

    assert "ENABLE_DURABLE_USAGE_CONTROLS=true" in str(exc_info.value)


def test_usage_startup_validation_rejects_non_positive_limits() -> None:
    with pytest.raises(RuntimeError) as exc_info:
        validate_usage_startup(
            Settings(
                enable_durable_usage_controls=True,
                anonymous_itinerary_generations_per_minute=0,
            )
        )

    assert "ANONYMOUS_ITINERARY_GENERATIONS_PER_MINUTE" in str(exc_info.value)


def test_public_read_endpoints_remain_available_after_generation_quota_blocks(
    client,
    monkeypatch,
) -> None:
    monkeypatch.setenv("ANONYMOUS_ITINERARY_GENERATIONS_PER_DAY", "1")
    monkeypatch.setenv("ANONYMOUS_ITINERARY_GENERATIONS_PER_MINUTE", "10")
    get_settings.cache_clear()
    get_usage_guard.cache_clear()

    payload = {
        "destinationId": "london",
        "bookId": "oliver-twist",
        "durationDays": 1,
        "transportationMode": "walking",
    }
    assert client.post("/api/itinerary/generate", json=payload).status_code == 200
    blocked = client.post("/api/itinerary/generate", json=payload)
    destinations = client.get("/api/destinations")

    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
    assert destinations.status_code == 200


def test_readiness_payload_reports_usage_controls(client, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_DURABLE_USAGE_CONTROLS", "true")
    get_settings.cache_clear()

    response = client.get("/api/readiness")
    payload = response.json()

    assert response.status_code == 200
    assert payload["checks"]["usageControls"]["durable"] is True
    assert payload["checks"]["usageControls"]["providerDailyRequestCeiling"] > 0


def test_fake_vector_provider_works_with_default_limits() -> None:
    service = VectorService(
        embedder=FakeEmbeddingProvider(dimension=4),
        store=InMemoryVectorStore(),
    )

    service.upsert_text(
        collection="test",
        vector_id="record-1",
        text="A short local embedding fixture.",
    )
    results = service.search_text(collection="test", query="local fixture", limit=1)

    assert len(results) == 1
