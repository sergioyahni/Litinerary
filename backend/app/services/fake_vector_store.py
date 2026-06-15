from hashlib import sha256
import json
from math import sqrt
from pathlib import Path

from app.services.provider_contracts import ProviderMetadata
from app.services.vector_types import (
    EmbeddingProvider,
    VectorRecord,
    VectorSearchResult,
    VectorStore,
)


class FakeEmbeddingProvider(EmbeddingProvider):
    provider_name = "fake_embedding"
    model_name = "sha256-token-normalized"

    def __init__(self, dimension: int = 16) -> None:
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        normalized = " ".join(text.lower().split())
        values = [0.0 for _ in range(self.dimension)]

        for index, token in enumerate(normalized.split() or [normalized]):
            digest = sha256(f"{index}:{token}".encode("utf-8")).digest()
            for offset in range(self.dimension):
                values[offset] += (digest[offset] - 127.5) / 127.5

        return _normalize(values)


class InMemoryVectorStore(VectorStore):
    def __init__(self) -> None:
        self._records: dict[str, dict[str, VectorRecord]] = {}

    def initialize_collection(self, collection: str, dimension: int) -> None:
        _ = dimension
        self._records.setdefault(collection, {})

    def validate_health(self) -> None:
        return None

    def upsert(self, record: VectorRecord) -> None:
        self._records.setdefault(record.collection, {})[record.id] = record

    def upsert_batch(self, records: list[VectorRecord]) -> None:
        for record in records:
            self.upsert(record)

    def search(
        self,
        collection: str,
        embedding: list[float],
        limit: int = 5,
        metadata_filter: dict[str, object] | None = None,
    ) -> list[VectorSearchResult]:
        records = self.fetch_by_metadata(collection, metadata_filter or {})
        results = [
            VectorSearchResult(record=record, score=_cosine_similarity(embedding, record.embedding))
            for record in records
        ]
        return sorted(results, key=lambda result: (-result.score, result.record.id))[:limit]

    def delete(self, collection: str, vector_id: str) -> None:
        self._records.get(collection, {}).pop(vector_id, None)

    def fetch_by_metadata(
        self,
        collection: str,
        metadata_filter: dict[str, object],
    ) -> list[VectorRecord]:
        records = self._records.get(collection, {}).values()
        return [
            record
            for record in records
            if _metadata_matches(record.metadata, metadata_filter)
        ]


class LocalJsonVectorStore(InMemoryVectorStore):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        super().__init__()
        self._load()

    def upsert(self, record: VectorRecord) -> None:
        super().upsert(record)
        self._save()

    def delete(self, collection: str, vector_id: str) -> None:
        super().delete(collection, vector_id)
        self._save()

    def _load(self) -> None:
        if not self.path.exists():
            return

        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self._records = {
            collection: {
                vector_id: VectorRecord(
                    **{
                        **record,
                        "provider_metadata": _metadata_from_json(
                            record.get("provider_metadata")
                        ),
                    }
                )
                for vector_id, record in records.items()
            }
            for collection, records in payload.items()
        }

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            collection: {
                vector_id: {
                    "id": record.id,
                    "collection": record.collection,
                    "embedding": record.embedding,
                    "metadata": record.metadata,
                    "text": record.text,
                    "provider_metadata": record.provider_metadata.public_dict()
                    if record.provider_metadata
                    else None,
                }
                for vector_id, record in records.items()
            }
            for collection, records in self._records.items()
        }
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _metadata_matches(metadata: dict[str, object], metadata_filter: dict[str, object]) -> bool:
    for key, expected in metadata_filter.items():
        actual = metadata.get(key)
        if isinstance(expected, (list, tuple, set)):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 0.0

    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0

    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)


def _normalize(values: list[float]) -> list[float]:
    magnitude = sqrt(sum(value * value for value in values))
    if magnitude == 0:
        return values
    return [round(value / magnitude, 8) for value in values]


def _metadata_from_json(value: dict | None) -> ProviderMetadata | None:
    if value is None:
        return None
    return ProviderMetadata(
        provider_name=value["provider_name"],
        provider_type=value["provider_type"],
        provider_version=value.get("provider_version"),
        request_id=value.get("request_id"),
        confidence_score=value.get("confidence_score"),
        source_url=value.get("source_url"),
        generated_at=value.get("generated_at"),
        verified_at=value.get("verified_at"),
        model_name=value.get("model_name"),
        embedding_dimension=value.get("embedding_dimension"),
        cost_estimate=value.get("cost_estimate"),
        latency_ms=value.get("latency_ms"),
        warnings=value.get("warnings") or [],
    )
