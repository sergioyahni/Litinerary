from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class IntegrityViolation:
    check: str
    count: int
    detail: str


def check_database_integrity(db: Session) -> list[IntegrityViolation]:
    checks = [
        (
            "itinerary_days_missing_itinerary",
            """
            SELECT COUNT(*)
            FROM itinerary_days d
            LEFT JOIN itineraries i ON i.id = d.itinerary_id
            WHERE i.id IS NULL
            """,
            "itinerary_days rows must reference an existing itinerary",
        ),
        (
            "itinerary_stops_missing_day",
            """
            SELECT COUNT(*)
            FROM itinerary_stops s
            LEFT JOIN itinerary_days d ON d.id = s.day_id
            WHERE d.id IS NULL
            """,
            "itinerary_stops rows must reference an existing itinerary day",
        ),
        (
            "itinerary_stops_missing_poi",
            """
            SELECT COUNT(*)
            FROM itinerary_stops s
            LEFT JOIN pois p ON p.id = s.poi_id
            WHERE p.id IS NULL
            """,
            "itinerary_stops rows must reference an existing POI",
        ),
        (
            "itineraries_missing_destination",
            """
            SELECT COUNT(*)
            FROM itineraries i
            LEFT JOIN destinations d ON d.id = i.destination_id
            WHERE d.id IS NULL
            """,
            "itineraries must reference an existing destination",
        ),
        (
            "itineraries_missing_book",
            """
            SELECT COUNT(*)
            FROM itineraries i
            LEFT JOIN books b ON b.id = i.book_id
            WHERE b.id IS NULL
            """,
            "itineraries must reference an existing book",
        ),
        (
            "itinerary_book_destination_mismatch",
            """
            SELECT COUNT(*)
            FROM itineraries i
            LEFT JOIN book_destinations bd
              ON bd.book_id = i.book_id AND bd.destination_id = i.destination_id
            WHERE bd.book_id IS NULL
            """,
            "itinerary books must be linked to the itinerary destination",
        ),
        (
            "itinerary_stop_poi_destination_mismatch",
            """
            SELECT COUNT(*)
            FROM itinerary_stops s
            JOIN itinerary_days d ON d.id = s.day_id
            JOIN itineraries i ON i.id = d.itinerary_id
            JOIN pois p ON p.id = s.poi_id
            WHERE p.destination_id != i.destination_id
            """,
            "itinerary stop POIs must belong to the itinerary destination",
        ),
        (
            "itinerary_stop_poi_book_mismatch",
            """
            SELECT COUNT(*)
            FROM itinerary_stops s
            JOIN itinerary_days d ON d.id = s.day_id
            JOIN itineraries i ON i.id = d.itinerary_id
            LEFT JOIN poi_books pb ON pb.poi_id = s.poi_id AND pb.book_id = i.book_id
            WHERE pb.poi_id IS NULL
            """,
            "itinerary stop POIs must be linked to the itinerary book",
        ),
        (
            "pois_missing_destination",
            """
            SELECT COUNT(*)
            FROM pois p
            LEFT JOIN destinations d ON d.id = p.destination_id
            WHERE d.id IS NULL
            """,
            "POIs must reference an existing destination",
        ),
        (
            "poi_books_missing_book",
            """
            SELECT COUNT(*)
            FROM poi_books pb
            LEFT JOIN books b ON b.id = pb.book_id
            WHERE b.id IS NULL
            """,
            "POI/book links must reference an existing book",
        ),
        (
            "owner_user_missing",
            """
            SELECT COUNT(*)
            FROM itineraries i
            LEFT JOIN users u ON u.id = i.owner_user_id
            WHERE i.owner_user_id IS NOT NULL AND u.id IS NULL
            """,
            "owned itineraries must reference an existing user",
        ),
        (
            "public_visibility_mismatch",
            """
            SELECT COUNT(*)
            FROM itineraries
            WHERE (visibility = 'public' AND is_public IS NOT TRUE)
               OR (visibility != 'public' AND is_public IS NOT FALSE)
            """,
            "itinerary visibility must match is_public",
        ),
        (
            "subscriber_only_invalid",
            """
            SELECT COUNT(*)
            FROM itineraries
            WHERE subscriber_only IS TRUE
              AND (
                visibility != 'private'
                OR is_public IS NOT FALSE
                OR owner_user_id IS NULL
              )
            """,
            "subscriber-only itineraries must be private and owner-bound",
        ),
    ]
    violations: list[IntegrityViolation] = []
    for check_name, sql, detail in checks:
        count = int(db.execute(text(sql)).scalar_one() or 0)
        if count:
            violations.append(IntegrityViolation(check=check_name, count=count, detail=detail))
    return violations
