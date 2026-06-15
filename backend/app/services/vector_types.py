from dataclasses import dataclass, field
from typing import Protocol

from app.services.provider_contracts import ProviderMetadata


class VectorCollection:
    USER_PREFERENCES = "user_preferences"
    USER_REVIEWS = "user_reviews"
    ITINERARIES = "itineraries"
    BOOK_CITY_MAPPINGS = "book_city_mappings"
    POIS = "pois"


@dataclass(frozen=True)
class VectorRecord:
    id: str
    collection: str
    embedding: list[float]
    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)
    text: str = ""
    provider_metadata: ProviderMetadata | None = None


@dataclass(frozen=True)
class VectorSearchResult:
    record: VectorRecord
    score: float
    provider_metadata: ProviderMetadata | None = None


class EmbeddingProvider(Protocol):
    provider_name: str
    model_name: str
    dimension: int

    def embed(self, text: str) -> list[float]:
        """Create a deterministic vector embedding for the supplied text."""


class VectorStore(Protocol):
    def initialize_collection(self, collection: str, dimension: int) -> None:
        """Create or verify a collection/index before writes."""

    def validate_health(self) -> None:
        """Validate provider configuration and basic availability."""

    def upsert(self, record: VectorRecord) -> None:
        """Create or replace a vector record."""

    def upsert_batch(self, records: list[VectorRecord]) -> None:
        """Create or replace multiple vector records."""

    def search(
        self,
        collection: str,
        embedding: list[float],
        limit: int = 5,
        metadata_filter: dict[str, object] | None = None,
    ) -> list[VectorSearchResult]:
        """Return similar vectors in descending score order."""

    def delete(self, collection: str, vector_id: str) -> None:
        """Delete a vector if it exists."""

    def fetch_by_metadata(
        self,
        collection: str,
        metadata_filter: dict[str, object],
    ) -> list[VectorRecord]:
        """Fetch vectors whose metadata matches the supplied filter."""
