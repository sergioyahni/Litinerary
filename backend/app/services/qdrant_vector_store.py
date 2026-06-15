from dataclasses import dataclass
import json
from time import monotonic
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import NAMESPACE_URL, uuid5

from app.core.config import get_settings
from app.core.provider_guards import require_external_call_allowed
from app.services.provider_contracts import (
    ProviderError,
    ProviderErrorCode,
    ProviderMetadata,
    ProviderType,
    utc_now_iso,
)
from app.services.vector_types import VectorRecord, VectorSearchResult, VectorStore


class QdrantTransport(Protocol):
    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a normalized JSON request to Qdrant."""


@dataclass(frozen=True)
class QdrantSettings:
    url: str
    api_key: str | None = None
    collection_prefix: str = "litinerary"
    dimension: int = 16
    timeout_seconds: float = 5.0


class QdrantHttpTransport:
    def __init__(self, settings: QdrantSettings) -> None:
        self.settings = settings
        self.base_url = settings.url.rstrip("/")

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        settings = get_settings()
        require_external_call_allowed(
            provider_name="qdrant",
            provider_type=ProviderType.VECTOR_DB,
            feature_flag_name="ENABLE_REAL_VECTOR_DB",
            feature_enabled=settings.enable_real_vector_db,
            required_config={"QDRANT_URL or VECTOR_DB_URL": self.settings.url},
            settings=settings,
        )
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"}
        if self.settings.api_key:
            headers["api-key"] = self.settings.api_key
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=self.settings.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as exc:
            raise _provider_error(
                ProviderErrorCode.INVALID_RESPONSE,
                f"Qdrant returned HTTP {exc.code}.",
            ) from exc
        except TimeoutError as exc:
            raise _provider_error(
                ProviderErrorCode.TIMEOUT,
                "Qdrant request timed out.",
            ) from exc
        except URLError as exc:
            raise _provider_error(
                ProviderErrorCode.UNAVAILABLE,
                "Qdrant is unavailable.",
            ) from exc

        if not response_body:
            return {}
        try:
            return json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise _provider_error(
                ProviderErrorCode.INVALID_RESPONSE,
                "Qdrant returned non-JSON response.",
            ) from exc


class QdrantVectorStore(VectorStore):
    provider_name = "qdrant"
    provider_version = "rest-v1"

    def __init__(
        self,
        settings: QdrantSettings,
        transport: QdrantTransport | None = None,
    ) -> None:
        if not settings.url:
            raise _provider_error(
                ProviderErrorCode.NOT_CONFIGURED,
                "Qdrant URL is required when the real Vector DB adapter is enabled.",
            )
        if settings.dimension <= 0:
            raise _provider_error(
                ProviderErrorCode.NOT_CONFIGURED,
                "Qdrant embedding dimension must be positive.",
            )
        self.settings = settings
        self.transport = transport or QdrantHttpTransport(settings)

    def initialize_collection(self, collection: str, dimension: int) -> None:
        self.transport.request(
            "PUT",
            f"/collections/{quote(self._collection_name(collection), safe='')}",
            {
                "vectors": {
                    "size": dimension,
                    "distance": "Cosine",
                }
            },
        )

    def validate_health(self) -> None:
        self.transport.request("GET", "/")

    def upsert(self, record: VectorRecord) -> None:
        self.upsert_batch([record])

    def upsert_batch(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        collection = records[0].collection
        if any(record.collection != collection for record in records):
            raise ValueError("Qdrant batch upsert requires all records to share a collection.")
        self.initialize_collection(collection, len(records[0].embedding))
        started = monotonic()
        self.transport.request(
            "PUT",
            f"/collections/{quote(self._collection_name(collection), safe='')}/points",
            {
                "points": [
                    {
                        "id": _point_id(record.collection, record.id),
                        "vector": record.embedding,
                        "payload": _record_payload(record),
                    }
                    for record in records
                ]
            },
        )
        latency_ms = round((monotonic() - started) * 1000)
        for record in records:
            object.__setattr__(
                record,
                "provider_metadata",
                self._metadata(latency_ms=latency_ms),
            )

    def search(
        self,
        collection: str,
        embedding: list[float],
        limit: int = 5,
        metadata_filter: dict[str, object] | None = None,
    ) -> list[VectorSearchResult]:
        started = monotonic()
        payload: dict[str, Any] = {
            "vector": embedding,
            "limit": limit,
            "with_payload": True,
            "with_vector": True,
        }
        if metadata_filter:
            payload["filter"] = _qdrant_filter(metadata_filter)
        response = self.transport.request(
            "POST",
            f"/collections/{quote(self._collection_name(collection), safe='')}/points/search",
            payload,
        )
        metadata = self._metadata(latency_ms=round((monotonic() - started) * 1000))
        return [
            VectorSearchResult(
                record=_record_from_point(collection, point, metadata),
                score=float(point.get("score") or 0.0),
                provider_metadata=metadata,
            )
            for point in response.get("result", [])
        ]

    def delete(self, collection: str, vector_id: str) -> None:
        self.transport.request(
            "POST",
            f"/collections/{quote(self._collection_name(collection), safe='')}/points/delete",
            {"points": [_point_id(collection, vector_id)]},
        )

    def fetch_by_metadata(
        self,
        collection: str,
        metadata_filter: dict[str, object],
    ) -> list[VectorRecord]:
        response = self.transport.request(
            "POST",
            f"/collections/{quote(self._collection_name(collection), safe='')}/points/scroll",
            {
                "filter": _qdrant_filter(metadata_filter),
                "limit": 100,
                "with_payload": True,
                "with_vector": True,
            },
        )
        metadata = self._metadata()
        return [
            _record_from_point(collection, point, metadata)
            for point in response.get("result", {}).get("points", [])
        ]

    def _collection_name(self, collection: str) -> str:
        prefix = self.settings.collection_prefix.strip("_")
        return f"{prefix}_{collection}" if prefix else collection

    def _metadata(self, latency_ms: int | None = None) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name=self.provider_name,
            provider_type=ProviderType.VECTOR_DB.value,
            provider_version=self.provider_version,
            generated_at=utc_now_iso(),
            embedding_dimension=self.settings.dimension,
            latency_ms=latency_ms,
            warnings=["Qdrant adapter boundary; external calls occur only when explicitly enabled."],
        )


def _point_id(collection: str, vector_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"litinerary:{collection}:{vector_id}"))


def _record_payload(record: VectorRecord) -> dict[str, Any]:
    return {
        "vector_id": record.id,
        "collection": record.collection,
        "metadata": record.metadata,
        "text": record.text,
    }


def _record_from_point(
    collection: str,
    point: dict[str, Any],
    provider_metadata: ProviderMetadata,
) -> VectorRecord:
    payload = point.get("payload") or {}
    metadata = payload.get("metadata") or {}
    return VectorRecord(
        id=str(payload.get("vector_id") or point.get("id")),
        collection=str(payload.get("collection") or collection),
        embedding=[float(value) for value in point.get("vector") or []],
        metadata=metadata,
        text=str(payload.get("text") or ""),
        provider_metadata=provider_metadata,
    )


def _qdrant_filter(metadata_filter: dict[str, object]) -> dict[str, Any]:
    must = []
    for key, value in metadata_filter.items():
        field_key = f"metadata.{key}"
        if isinstance(value, (list, tuple, set)):
            must.append({"key": field_key, "match": {"any": list(value)}})
        else:
            must.append({"key": field_key, "match": {"value": value}})
    return {"must": must}


def _provider_error(code: ProviderErrorCode, message: str) -> ProviderError:
    return ProviderError(
        code,
        message,
        metadata=ProviderMetadata(
            provider_name="qdrant",
            provider_type=ProviderType.VECTOR_DB.value,
            provider_version="rest-v1",
            generated_at=utc_now_iso(),
        ),
    )
