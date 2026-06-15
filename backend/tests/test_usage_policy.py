from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import Settings, get_settings
from app.services.fake_vector_store import FakeEmbeddingProvider, InMemoryVectorStore
from app.services.provider_contracts import ProviderError, ProviderErrorCode, ProviderType
from app.services.usage_policy import (
    InMemoryProviderUsageStore,
    ProviderUsageGuard,
    get_usage_guard,
)
from app.services.vector_service import VectorService


@pytest.fixture(autouse=True)
def clear_settings_and_usage_guard_cache():
    get_settings.cache_clear()
    get_usage_guard.cache_clear()
    yield
    get_usage_guard.cache_clear()
    get_settings.cache_clear()


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

    assert len([record for record in guard.store.records if record.allowed]) == 2


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
