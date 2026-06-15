"""Print a dry-run plan for future Vector DB backfill.

This script intentionally does not connect to a real Vector DB or write embeddings.
Use it as an operator checklist before implementing an explicit backfill command.
"""

from app.services.vector_types import VectorCollection


BACKFILL_STEPS = [
    (
        VectorCollection.USER_PREFERENCES,
        "Read user_preferences, embed preference key/value text, preserve user_id metadata.",
    ),
    (
        VectorCollection.USER_REVIEWS,
        "Read user_reviews joined to itineraries, embed rating/comment text, preserve user and itinerary metadata.",
    ),
    (
        VectorCollection.ITINERARIES,
        "Read public and permitted private itineraries, embed title/summary/stops, preserve ownership and visibility metadata.",
    ),
    (
        VectorCollection.POIS,
        "Read POIs, embed name/description/literary relevance, preserve verification/provider metadata.",
    ),
    (
        VectorCollection.BOOK_CITY_MAPPINGS,
        "Read books and destination links, embed title/author/description for city-scoped discovery.",
    ),
]


def main() -> None:
    print("Litinerary Vector Backfill Plan (dry run only)")
    print("No embeddings are generated and no Vector DB calls are made.")
    for index, (collection, description) in enumerate(BACKFILL_STEPS, start=1):
        print(f"{index}. {collection}: {description}")
    print("Future implementation must be gated by ENABLE_REAL_VECTOR_DB and tested without network calls.")


if __name__ == "__main__":
    main()
