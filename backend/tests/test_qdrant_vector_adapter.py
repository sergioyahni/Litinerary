import pytest

from app.core.config import get_settings
from app.services.fake_vector_store import InMemoryVectorStore
from app.services.provider_contracts import ProviderError, ProviderErrorCode
from app.services.qdrant_vector_store import QdrantSettings, QdrantVectorStore
from app.services.vector_service import get_vector_service, validate_vector_startup
from app.services.vector_types import VectorCollection, VectorRecord


class RecordingTransport:
    def __init__(self) -> None:
        self.requests: list[tuple[str, str, dict | None]] = []

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        self.requests.append((method, path, payload))
        if path.endswith("/points/search"):
            return {
                "result": [
                    {
                        "id": "qdrant-point-id",
                        "score": 0.91,
                        "vector": [0.1, 0.2, 0.3],
                        "payload": {
                            "vector_id": "it-1",
                            "collection": VectorCollection.ITINERARIES,
                            "metadata": {"destination_id": "london"},
                            "text": "Dickens London",
                        },
                    }
                ]
            }
        if path.endswith("/points/scroll"):
            return {
                "result": {
                    "points": [
                        {
                            "id": "qdrant-point-id",
                            "vector": [0.1, 0.2, 0.3],
                            "payload": {
                                "vector_id": "it-1",
                                "collection": VectorCollection.ITINERARIES,
                                "metadata": {"destination_id": "london"},
                                "text": "Dickens London",
                            },
                        }
                    ]
                }
            }
        return {"result": {"status": "ok"}}


@pytest.fixture(autouse=True)
def clear_vector_settings_cache():
    get_settings.cache_clear()
    get_vector_service.cache_clear()
    yield
    get_settings.cache_clear()
    get_vector_service.cache_clear()


def test_fake_vector_store_remains_default(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_REAL_VECTOR_DB", raising=False)
    monkeypatch.delenv("LITINERARY_VECTOR_PROVIDER", raising=False)
    monkeypatch.delenv("VECTOR_DB_PROVIDER", raising=False)

    service = get_vector_service()

    assert isinstance(service.store, InMemoryVectorStore)


def test_qdrant_selection_requires_real_vector_flag(monkeypatch) -> None:
    monkeypatch.setenv("LITINERARY_VECTOR_PROVIDER", "qdrant")
    monkeypatch.setenv("VECTOR_DB_PROVIDER", "qdrant")
    monkeypatch.setenv("ENABLE_REAL_VECTOR_DB", "false")
    get_settings.cache_clear()
    get_vector_service.cache_clear()

    with pytest.raises(RuntimeError, match="ENABLE_REAL_VECTOR_DB"):
        get_vector_service()


def test_qdrant_missing_config_fails_clearly(monkeypatch) -> None:
    monkeypatch.setenv("LITINERARY_VECTOR_PROVIDER", "qdrant")
    monkeypatch.setenv("VECTOR_DB_PROVIDER", "qdrant")
    monkeypatch.setenv("ENABLE_REAL_VECTOR_DB", "true")
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.delenv("VECTOR_DB_URL", raising=False)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="QDRANT_URL"):
        validate_vector_startup(get_settings())


def test_qdrant_store_methods_use_contract_payloads_without_network() -> None:
    transport = RecordingTransport()
    store = QdrantVectorStore(
        QdrantSettings(
            url="http://qdrant.test",
            api_key="test-key",
            collection_prefix="litinerary_test",
            dimension=3,
        ),
        transport=transport,
    )
    record = VectorRecord(
        id="it-1",
        collection=VectorCollection.ITINERARIES,
        embedding=[0.1, 0.2, 0.3],
        metadata={"destination_id": "london"},
        text="Dickens London",
    )

    store.validate_health()
    store.initialize_collection(VectorCollection.ITINERARIES, 3)
    store.upsert(record)
    store.upsert_batch([record])
    search_results = store.search(
        VectorCollection.ITINERARIES,
        [0.1, 0.2, 0.3],
        metadata_filter={"destination_id": "london"},
    )
    fetched = store.fetch_by_metadata(
        VectorCollection.ITINERARIES,
        {"destination_id": "london"},
    )
    store.delete(VectorCollection.ITINERARIES, "it-1")

    methods = [method for method, _, _ in transport.requests]
    paths = [path for _, path, _ in transport.requests]
    upsert_payload = next(
        payload
        for method, path, payload in transport.requests
        if method == "PUT" and path.endswith("/points")
    )

    assert methods[0] == "GET"
    assert methods.count("PUT") == 5
    assert methods.count("POST") == 3
    assert "/collections/litinerary_test_itineraries" in paths
    assert upsert_payload["points"][0]["payload"]["vector_id"] == "it-1"
    assert upsert_payload["points"][0]["payload"]["metadata"]["destination_id"] == "london"
    assert search_results[0].record.id == "it-1"
    assert search_results[0].provider_metadata.provider_name == "qdrant"
    assert fetched[0].metadata["destination_id"] == "london"


def test_qdrant_batch_rejects_mixed_collections_without_network() -> None:
    transport = RecordingTransport()
    store = QdrantVectorStore(
        QdrantSettings(url="http://qdrant.test", dimension=3),
        transport=transport,
    )

    with pytest.raises(ValueError, match="share a collection"):
        store.upsert_batch(
            [
                VectorRecord(
                    id="it-1",
                    collection=VectorCollection.ITINERARIES,
                    embedding=[0.1, 0.2, 0.3],
                ),
                VectorRecord(
                    id="poi-1",
                    collection=VectorCollection.POIS,
                    embedding=[0.1, 0.2, 0.3],
                ),
            ]
        )

    assert transport.requests == []


def test_qdrant_missing_url_uses_normalized_provider_error() -> None:
    with pytest.raises(ProviderError) as exc_info:
        QdrantVectorStore(QdrantSettings(url="", dimension=3))

    assert exc_info.value.code == ProviderErrorCode.NOT_CONFIGURED
    assert exc_info.value.metadata.provider_type == "vector_db"
