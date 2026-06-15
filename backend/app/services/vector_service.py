from functools import lru_cache

from app.core.config import get_settings
from app.core.observability import record_provider_selection
from app.core.provider_guards import require_external_call_allowed
from app.schemas.domain import Book, Itinerary, POI
from app.schemas.users import UserPreference, UserReview
from app.services.fake_vector_store import (
    FakeEmbeddingProvider,
    InMemoryVectorStore,
    LocalJsonVectorStore,
)
from app.services.qdrant_vector_store import QdrantSettings, QdrantVectorStore
from app.services.vector_types import (
    EmbeddingProvider,
    VectorCollection,
    VectorRecord,
    VectorSearchResult,
    VectorStore,
)
from app.services.provider_contracts import ProviderMetadata, ProviderType
from app.services.usage_policy import get_usage_guard


class VectorService:
    def __init__(self, embedder: EmbeddingProvider, store: VectorStore) -> None:
        self.embedder = embedder
        self.store = store

    def upsert_text(
        self,
        collection: str,
        vector_id: str,
        text: str,
        metadata: dict[str, str | int | float | bool | None] | None = None,
    ) -> VectorRecord:
        get_usage_guard().guard_vector_upsert(text=text)
        embedding = self.embedder.embed(text)
        record = VectorRecord(
            id=vector_id,
            collection=collection,
            embedding=embedding,
            metadata=metadata or {},
            text=text,
            provider_metadata=ProviderMetadata.mock(
                provider_name=getattr(self.embedder, "provider_name", "unknown_embedding"),
                provider_type=ProviderType.EMBEDDING,
                model_name=getattr(self.embedder, "model_name", None),
                embedding_dimension=len(embedding),
                warnings=["Fake/local embedding; no external vector provider call was made."],
            ),
        )
        self.store.upsert(record)
        return record

    def upsert_batch(self, records: list[VectorRecord]) -> None:
        self.store.upsert_batch(records)

    def search_text(
        self,
        collection: str,
        query: str,
        limit: int = 5,
        metadata_filter: dict[str, object] | None = None,
    ) -> list[VectorSearchResult]:
        get_usage_guard().guard_vector_search(limit=limit)
        return self.store.search(
            collection=collection,
            embedding=self.embedder.embed(query),
            limit=limit,
            metadata_filter=metadata_filter,
        )

    def delete(self, collection: str, vector_id: str) -> None:
        self.store.delete(collection, vector_id)

    def fetch_by_metadata(
        self,
        collection: str,
        metadata_filter: dict[str, object],
    ) -> list[VectorRecord]:
        return self.store.fetch_by_metadata(collection, metadata_filter)


@lru_cache
def get_vector_service() -> VectorService:
    settings = get_settings()
    if settings.vector_provider == "fake" and not settings.enable_mock_services:
        raise RuntimeError(
            "Mock vector services are disabled in this environment. "
            "Set ENABLE_MOCK_SERVICES=true only for intentional local/test use."
        )
    if settings.vector_provider != "fake" and not settings.enable_real_vector_db:
        raise RuntimeError(
            f"Real Vector DB provider '{settings.vector_provider}' is disabled by ENABLE_REAL_VECTOR_DB."
        )
    if settings.vector_provider == "qdrant":
        record_provider_selection(
            provider_type=ProviderType.VECTOR_DB.value,
            provider_name="qdrant",
            mode="real",
        )
        validate_vector_startup(settings)
        return VectorService(
            embedder=FakeEmbeddingProvider(dimension=settings.vector_dimension),
            store=QdrantVectorStore(
                QdrantSettings(
                    url=settings.qdrant_url or "",
                    api_key=settings.qdrant_api_key,
                    collection_prefix=settings.qdrant_collection_prefix,
                    dimension=settings.vector_dimension,
                    timeout_seconds=settings.qdrant_timeout_seconds,
                )
            ),
        )

    if settings.vector_provider != "fake":
        raise RuntimeError(
            f"Vector provider '{settings.vector_provider}' is configured but not implemented."
        )

    store = (
        LocalJsonVectorStore(settings.vector_store_path)
        if settings.vector_store_path
        else InMemoryVectorStore()
    )

    record_provider_selection(
        provider_type=ProviderType.VECTOR_DB.value,
        provider_name="fake",
        mode="mock",
    )
    return VectorService(
        embedder=FakeEmbeddingProvider(dimension=settings.vector_dimension),
        store=store,
    )


def validate_vector_startup(settings=None) -> None:
    resolved = settings or get_settings()
    if not resolved.enable_real_vector_db:
        return
    if resolved.vector_provider != "qdrant":
        raise RuntimeError(
            "Real Vector DB is enabled but only the Qdrant adapter boundary is implemented. "
            "Set VECTOR_DB_PROVIDER=qdrant or disable ENABLE_REAL_VECTOR_DB."
        )
    require_external_call_allowed(
        provider_name="qdrant",
        provider_type=ProviderType.VECTOR_DB,
        feature_flag_name="ENABLE_REAL_VECTOR_DB",
        feature_enabled=resolved.enable_real_vector_db,
        required_config={"QDRANT_URL or VECTOR_DB_URL": resolved.qdrant_url},
        settings=resolved,
    )
    missing = []
    if not resolved.qdrant_url:
        missing.append("QDRANT_URL or VECTOR_DB_URL")
    if resolved.vector_dimension <= 0:
        missing.append("LITINERARY_VECTOR_DIMENSION must be positive")
    if missing:
        raise RuntimeError(
            "Real Qdrant Vector DB is enabled but configuration is incomplete: "
            + ", ".join(missing)
        )


def save_user_preference_embedding(
    preference: UserPreference,
    service: VectorService | None = None,
) -> VectorRecord:
    vector_service = service or get_vector_service()
    text = f"{preference.key}: {preference.value}"
    metadata = {
        "user_id": preference.userId,
        "preference_id": preference.id,
        "preference_key": preference.key,
        "created_at": preference.createdAt,
    }
    metadata.update(_metadata_from_preference_value(preference.value))
    return vector_service.upsert_text(
        collection=VectorCollection.USER_PREFERENCES,
        vector_id=preference.id,
        text=text,
        metadata=metadata,
    )


def save_user_review_embedding(
    review: UserReview,
    itinerary: Itinerary | None = None,
    service: VectorService | None = None,
) -> VectorRecord:
    vector_service = service or get_vector_service()
    text = f"rating={review.rating}; comment={review.comment or ''}"
    metadata = {
        "user_id": review.userId,
        "review_id": review.id,
        "itinerary_id": review.itineraryId,
        "rating": review.rating,
        "created_at": review.createdAt,
    }
    if itinerary is not None:
        metadata.update(
            {
                "city_id": itinerary.destinationId,
                "destination_id": itinerary.destinationId,
                "book_id": itinerary.bookId,
            }
        )
    return vector_service.upsert_text(
        collection=VectorCollection.USER_REVIEWS,
        vector_id=review.id,
        text=text,
        metadata=metadata,
    )


def save_itinerary_embedding(
    itinerary: Itinerary,
    service: VectorService | None = None,
) -> VectorRecord:
    vector_service = service or get_vector_service()
    stop_text = " ".join(
        stop.poi.name
        for day in itinerary.days
        for stop in day.stops
    )
    text = f"{itinerary.title}. {itinerary.summary}. {stop_text}"
    return vector_service.upsert_text(
        collection=VectorCollection.ITINERARIES,
        vector_id=itinerary.id,
        text=text,
        metadata={
            "destination_id": itinerary.destinationId,
            "book_id": itinerary.bookId,
            "transportation_mode": itinerary.transportationMode,
            "is_public": itinerary.isPublic,
        },
    )


def save_book_city_mapping_embedding(
    book: Book,
    service: VectorService | None = None,
) -> list[VectorRecord]:
    vector_service = service or get_vector_service()
    return [
        vector_service.upsert_text(
            collection=VectorCollection.BOOK_CITY_MAPPINGS,
            vector_id=f"{book.id}:{destination_id}",
            text=f"{book.title} by {book.author}. {book.description}",
            metadata={"book_id": book.id, "destination_id": destination_id},
        )
        for destination_id in book.destinationIds
    ]


def save_poi_embedding(poi: POI, service: VectorService | None = None) -> VectorRecord:
    vector_service = service or get_vector_service()
    return vector_service.upsert_text(
        collection=VectorCollection.POIS,
        vector_id=poi.id,
        text=f"{poi.name}. {poi.description}. {poi.literaryRelevance}",
        metadata={
            "destination_id": poi.destinationId,
            "verification_status": poi.verificationStatus,
        },
    )


def search_similar_itineraries(
    query: str,
    metadata_filter: dict[str, object] | None = None,
    limit: int = 5,
    service: VectorService | None = None,
) -> list[VectorSearchResult]:
    vector_service = service or get_vector_service()
    return vector_service.search_text(
        VectorCollection.ITINERARIES,
        query,
        limit=limit,
        metadata_filter=metadata_filter,
    )


def search_books_by_metadata(
    metadata_filter: dict[str, object],
    service: VectorService | None = None,
) -> list[VectorRecord]:
    vector_service = service or get_vector_service()
    return vector_service.fetch_by_metadata(
        VectorCollection.BOOK_CITY_MAPPINGS,
        metadata_filter,
    )


def search_similar_books(
    query: str,
    metadata_filter: dict[str, object] | None = None,
    limit: int = 5,
    service: VectorService | None = None,
) -> list[VectorSearchResult]:
    vector_service = service or get_vector_service()
    return vector_service.search_text(
        VectorCollection.BOOK_CITY_MAPPINGS,
        query,
        limit=limit,
        metadata_filter=metadata_filter,
    )


def search_pois_by_metadata(
    metadata_filter: dict[str, object],
    service: VectorService | None = None,
) -> list[VectorRecord]:
    vector_service = service or get_vector_service()
    return vector_service.fetch_by_metadata(VectorCollection.POIS, metadata_filter)


def search_similar_pois(
    query: str,
    metadata_filter: dict[str, object] | None = None,
    limit: int = 5,
    service: VectorService | None = None,
) -> list[VectorSearchResult]:
    vector_service = service or get_vector_service()
    return vector_service.search_text(
        VectorCollection.POIS,
        query,
        limit=limit,
        metadata_filter=metadata_filter,
    )


def find_itineraries_similar_to_user_preferences(
    user_id: str,
    metadata_filter: dict[str, object] | None = None,
    limit: int = 5,
    service: VectorService | None = None,
) -> list[VectorSearchResult]:
    vector_service = service or get_vector_service()
    query = _combined_user_vector_text(
        vector_service.fetch_by_metadata(
            VectorCollection.USER_PREFERENCES,
            {"user_id": user_id},
        )
    )
    if not query:
        return []

    return vector_service.search_text(
        VectorCollection.ITINERARIES,
        query,
        limit=limit,
        metadata_filter=metadata_filter,
    )


def find_itineraries_similar_to_user_positive_reviews(
    user_id: str,
    metadata_filter: dict[str, object] | None = None,
    limit: int = 5,
    min_rating: int = 4,
    service: VectorService | None = None,
) -> list[VectorSearchResult]:
    vector_service = service or get_vector_service()
    reviews = vector_service.fetch_by_metadata(
        VectorCollection.USER_REVIEWS,
        {"user_id": user_id},
    )
    positive_reviews = [
        record
        for record in reviews
        if _metadata_rating(record.metadata.get("rating")) >= min_rating
    ]
    query = _combined_user_vector_text(positive_reviews)
    if not query:
        return []

    return vector_service.search_text(
        VectorCollection.ITINERARIES,
        query,
        limit=limit,
        metadata_filter=metadata_filter,
    )


def find_pois_similar_to_user_interests(
    user_id: str,
    metadata_filter: dict[str, object] | None = None,
    limit: int = 5,
    service: VectorService | None = None,
) -> list[VectorSearchResult]:
    vector_service = service or get_vector_service()
    preference_text = vector_service.fetch_by_metadata(
        VectorCollection.USER_PREFERENCES,
        {"user_id": user_id},
    )
    review_text = [
        record
        for record in vector_service.fetch_by_metadata(
            VectorCollection.USER_REVIEWS,
            {"user_id": user_id},
        )
        if _metadata_rating(record.metadata.get("rating")) >= 4
    ]
    query = _combined_user_vector_text([*preference_text, *review_text])
    if not query:
        return []

    return vector_service.search_text(
        VectorCollection.POIS,
        query,
        limit=limit,
        metadata_filter=metadata_filter,
    )


def _metadata_from_preference_value(
    value: dict,
) -> dict[str, str | int | float | bool | None]:
    city_id = _first_scalar_value(value, "cityId", "city_id", "destinationId", "destination_id")
    book_id = _first_scalar_value(value, "bookId", "book_id")
    itinerary_id = _first_scalar_value(value, "itineraryId", "itinerary_id")
    metadata: dict[str, str | int | float | bool | None] = {}
    if city_id is not None:
        metadata["city_id"] = city_id
        metadata["destination_id"] = city_id
    if book_id is not None:
        metadata["book_id"] = book_id
    if itinerary_id is not None:
        metadata["itinerary_id"] = itinerary_id
    return metadata


def _first_scalar_value(
    value: dict,
    *keys: str,
) -> str | int | float | bool | None:
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, str | int | float | bool) or candidate is None:
            return candidate
    return None


def _metadata_rating(value: object) -> int:
    return value if isinstance(value, int) else 0


def _combined_user_vector_text(records: list[VectorRecord]) -> str:
    return " ".join(record.text for record in sorted(records, key=lambda record: record.id))
