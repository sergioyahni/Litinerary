from app.schemas.domain import Book, Destination
from app.services import database_repository as db_repository


EXTERNAL_BOOKS: list[Book] = [
    Book(
        id="external-london-bleak-house",
        destinationIds=["london"],
        title="Bleak House",
        author="Charles Dickens",
        description="Externally discovered metadata for a Dickens novel with London route potential.",
        publicationYear=1853,
        publicDomain=True,
        themes=["classic", "law", "urban"],
        sourceType="external",
        providerId="mock-open-library:bleak-house",
        provenanceMetadata={
            "provider": "mock_external_discovery",
            "persistedAsStandaloneBook": False,
        },
    ),
    Book(
        id="external-paris-hunchback",
        destinationIds=["paris"],
        title="The Hunchback of Notre-Dame",
        author="Victor Hugo",
        description="Externally discovered metadata for a Hugo route through historic Paris.",
        publicationYear=1831,
        publicDomain=True,
        themes=["classic", "gothic", "cathedral"],
        sourceType="external",
        providerId="mock-open-library:hunchback-notre-dame",
        provenanceMetadata={
            "provider": "mock_external_discovery",
            "persistedAsStandaloneBook": False,
        },
    ),
]


EXTERNAL_DESTINATIONS: list[Destination] = [
    Destination(
        id="external-edinburgh",
        name="Edinburgh",
        country="United Kingdom",
        description="Externally discovered literary city metadata; generation requires route evidence.",
        latitude=55.9533,
        longitude=-3.1883,
        supported=True,
        sourceType="external",
        providerId="mock-places:edinburgh",
        provenanceMetadata={
            "provider": "mock_external_discovery",
            "persistedAsStandaloneDestination": False,
        },
    ),
]


def search_books(
    query: str,
    *,
    destination_id: str | None = None,
    db=None,
    include_external: bool = False,
) -> tuple[list[Book], bool]:
    repository_results = db_repository.search_public_books(
        db,
        query=query,
        destination_id=destination_id,
    )
    if repository_results or not include_external:
        return repository_results, False
    return _filter_books(EXTERNAL_BOOKS, query=query, destination_id=destination_id), True


def search_destinations(
    query: str,
    *,
    db=None,
    include_external: bool = False,
) -> tuple[list[Destination], bool]:
    repository_results = db_repository.search_public_destinations(db, query=query)
    if repository_results or not include_external:
        return repository_results, False
    normalized = query.strip().lower()
    return [
        destination
        for destination in EXTERNAL_DESTINATIONS
        if normalized in destination.name.lower() or normalized in destination.country.lower()
    ], True


def get_external_book(book_id: str, *, destination_id: str | None = None) -> Book | None:
    matches = _filter_books(EXTERNAL_BOOKS, query=book_id, destination_id=destination_id)
    for book in matches:
        if book.id == book_id or book.providerId == book_id:
            return book
    return None


def _filter_books(
    books: list[Book],
    *,
    query: str,
    destination_id: str | None = None,
) -> list[Book]:
    normalized = query.strip().lower()
    results = []
    for book in books:
        if destination_id is not None and destination_id not in book.destinationIds:
            continue
        searchable = " ".join([book.id, book.title, book.author, book.providerId or ""]).lower()
        if normalized in searchable:
            results.append(book)
    return results
