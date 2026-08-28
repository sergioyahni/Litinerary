from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.services.seed import seed_database


def main() -> None:
    if not get_settings().is_deployed_environment:
        init_db()
    with SessionLocal() as db:
        counts = seed_database(db)

    print(
        "Seeded database: "
        f"{counts['destinations']} destinations, "
        f"{counts['books']} books, "
        f"{counts['pois']} POIs, "
        f"{counts['itineraries']} itineraries."
    )


if __name__ == "__main__":
    main()
