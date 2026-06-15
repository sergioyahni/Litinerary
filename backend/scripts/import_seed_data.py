import argparse
import json
from pathlib import Path

from app.core.database import SessionLocal, init_db
from app.schemas.seed_admin import SeedDataPayload
from app.services.seed_manager import import_seed_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Litinerary seed data from JSON.")
    parser.add_argument("path", help="Input JSON path.")
    args = parser.parse_args()

    payload = SeedDataPayload(**json.loads(Path(args.path).read_text(encoding="utf-8")))
    init_db()
    with SessionLocal() as db:
        result = import_seed_data(db, payload)
    print(result.model_dump_json(indent=2))
    if result.validation and not result.validation.valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
