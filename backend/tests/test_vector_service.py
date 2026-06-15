from app.schemas.domain import Book, Itinerary
from app.schemas.users import UserPreference, UserReview
from app.services.fake_vector_store import (
    FakeEmbeddingProvider,
    InMemoryVectorStore,
    LocalJsonVectorStore,
)
from app.services.vector_service import (
    VectorService,
    save_book_city_mapping_embedding,
    save_itinerary_embedding,
    save_poi_embedding,
    save_user_preference_embedding,
    save_user_review_embedding,
    find_itineraries_similar_to_user_positive_reviews,
    find_itineraries_similar_to_user_preferences,
    find_pois_similar_to_user_interests,
    search_books_by_metadata,
    search_pois_by_metadata,
    search_similar_books,
    search_similar_itineraries,
    search_similar_pois,
)
from app.services.vector_types import VectorCollection
from app.data.mock_data import ITINERARIES, POIS


def make_service() -> VectorService:
    return VectorService(FakeEmbeddingProvider(dimension=8), InMemoryVectorStore())


def test_fake_embedding_generation_is_deterministic() -> None:
    embedder = FakeEmbeddingProvider(dimension=8)

    assert embedder.embed("Slow classic travel") == embedder.embed("Slow classic travel")
    assert embedder.embed("Slow classic travel") != embedder.embed("Packed thriller travel")
    assert len(embedder.embed("Slow classic travel")) == 8


def test_vector_store_filters_metadata_and_returns_stable_similarity_order() -> None:
    service = make_service()
    first = service.upsert_text(
        VectorCollection.ITINERARIES,
        "it-1",
        "Dickens London markets and alleys",
        {"destination_id": "london"},
    )
    service.upsert_text(
        VectorCollection.ITINERARIES,
        "it-2",
        "Paris museum symbols",
        {"destination_id": "paris"},
    )
    service.upsert_text(
        VectorCollection.ITINERARIES,
        "it-3",
        "London detective walking clues",
        {"destination_id": "london"},
    )

    results = service.search_text(
        VectorCollection.ITINERARIES,
        "London markets",
        metadata_filter={"destination_id": "london"},
    )

    assert {result.record.metadata["destination_id"] for result in results} == {"london"}
    assert results == service.search_text(
        VectorCollection.ITINERARIES,
        "London markets",
        metadata_filter={"destination_id": "london"},
    )
    assert first in [result.record for result in results]


def test_user_preference_and_review_embeddings_can_be_saved() -> None:
    service = make_service()
    preference = UserPreference(
        id="pref-1",
        userId="dev-reader",
        key="travel",
        value={"pace": "slow"},
        createdAt="now",
    )
    review = UserReview(
        id="review-1",
        userId="dev-reader",
        itineraryId="it-1",
        rating=5,
        comment="Great route",
        createdAt="now",
    )

    save_user_preference_embedding(preference, service=service)
    save_user_review_embedding(review, itinerary=ITINERARIES[0], service=service)

    preference_record = service.fetch_by_metadata(
        VectorCollection.USER_PREFERENCES,
        {"user_id": "dev-reader"},
    )[0]
    review_record = service.fetch_by_metadata(
        VectorCollection.USER_REVIEWS,
        {"itinerary_id": "it-1"},
    )[0]

    assert preference_record.id == "pref-1"
    assert preference_record.metadata["preference_id"] == "pref-1"
    assert preference_record.metadata["created_at"] == "now"
    assert review_record.id == "review-1"
    assert review_record.metadata["review_id"] == "review-1"
    assert review_record.metadata["city_id"] == ITINERARIES[0].destinationId
    assert review_record.metadata["book_id"] == ITINERARIES[0].bookId


def test_itinerary_book_and_poi_vector_helpers_support_search_and_metadata_fetch() -> None:
    service = make_service()
    itinerary: Itinerary = ITINERARIES[0]
    poi = POIS[0]
    book = Book(
        id="oliver-twist",
        destinationIds=["london"],
        title="Oliver Twist",
        author="Charles Dickens",
        description="A London novel.",
        publicationYear=1838,
        publicDomain=True,
        themes=["classic"],
    )

    save_itinerary_embedding(itinerary, service=service)
    save_book_city_mapping_embedding(book, service=service)
    save_poi_embedding(poi, service=service)

    similar = search_similar_itineraries(
        "Dickens markets",
        metadata_filter={"destination_id": "london"},
        service=service,
    )
    books = search_books_by_metadata({"destination_id": "london"}, service=service)
    pois = search_pois_by_metadata({"destination_id": "london"}, service=service)

    assert similar[0].record.id == itinerary.id
    assert books[0].metadata["book_id"] == "oliver-twist"
    assert pois[0].id == poi.id


def test_book_and_poi_similarity_helpers_support_metadata_filters() -> None:
    service = make_service()
    london_book = Book(
        id="bleak-house",
        destinationIds=["london"],
        title="Bleak House",
        author="Charles Dickens",
        description="A legal mystery through London courts and streets.",
        publicationYear=1853,
        publicDomain=True,
        themes=["classic", "law"],
    )
    paris_book = Book(
        id="les-miserables",
        destinationIds=["paris"],
        title="Les Miserables",
        author="Victor Hugo",
        description="A Paris novel of revolution and conscience.",
        publicationYear=1862,
        publicDomain=True,
        themes=["classic"],
    )

    save_book_city_mapping_embedding(london_book, service=service)
    save_book_city_mapping_embedding(paris_book, service=service)
    save_poi_embedding(POIS[0], service=service)

    books = search_similar_books(
        "London courts",
        metadata_filter={"destination_id": "london"},
        service=service,
    )
    pois = search_similar_pois(
        POIS[0].name,
        metadata_filter={"destination_id": POIS[0].destinationId},
        service=service,
    )

    assert [result.record.id for result in books] == ["bleak-house:london"]
    assert pois[0].record.id == POIS[0].id


def test_local_json_vector_store_persists_records(tmp_path) -> None:
    path = tmp_path / "vectors.json"
    service = VectorService(FakeEmbeddingProvider(dimension=8), LocalJsonVectorStore(path))
    service.upsert_text(
        VectorCollection.USER_PREFERENCES,
        "pref-1",
        "travel pace slow",
        {"user_id": "dev-reader"},
    )

    reloaded = VectorService(FakeEmbeddingProvider(dimension=8), LocalJsonVectorStore(path))
    records = reloaded.fetch_by_metadata(
        VectorCollection.USER_PREFERENCES,
        {"user_id": "dev-reader"},
    )

    assert records[0].id == "pref-1"


def test_mock_recommendation_queries_are_deterministic() -> None:
    service = make_service()
    itinerary: Itinerary = ITINERARIES[0]
    poi = POIS[0]
    preference = UserPreference(
        id="pref-1",
        userId="dev-reader",
        key="travel",
        value={
            "pace": "slow",
            "themes": ["classic"],
            "cityId": itinerary.destinationId,
            "bookId": itinerary.bookId,
        },
        createdAt="now",
    )
    review = UserReview(
        id="review-1",
        userId="dev-reader",
        itineraryId=itinerary.id,
        rating=5,
        comment=f"Loved {poi.name}",
        createdAt="now",
    )

    save_itinerary_embedding(itinerary, service=service)
    save_poi_embedding(poi, service=service)
    save_user_preference_embedding(preference, service=service)
    save_user_review_embedding(review, itinerary=itinerary, service=service)

    by_preferences = find_itineraries_similar_to_user_preferences(
        "dev-reader",
        metadata_filter={"destination_id": itinerary.destinationId},
        service=service,
    )
    by_reviews = find_itineraries_similar_to_user_positive_reviews(
        "dev-reader",
        service=service,
    )
    pois = find_pois_similar_to_user_interests("dev-reader", service=service)

    assert by_preferences == find_itineraries_similar_to_user_preferences(
        "dev-reader",
        metadata_filter={"destination_id": itinerary.destinationId},
        service=service,
    )
    assert by_preferences[0].record.id == itinerary.id
    assert by_reviews[0].record.id == itinerary.id
    assert pois[0].record.id == poi.id
