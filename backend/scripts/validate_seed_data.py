import argparse
import json
from pathlib import Path

from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.schemas.seed_admin import SeedDataPayload
from app.services.seed_manager import validate_current_seed_data, validate_seed_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Litinerary seed data.")
    parser.add_argument("--path", help="Optional seed JSON path. Defaults to current database.")
    args = parser.parse_args()

    if args.path:
        payload = SeedDataPayload(**json.loads(Path(args.path).read_text(encoding="utf-8")))
        report = validate_seed_data(payload)
    else:
        if not get_settings().is_deployed_environment:
            init_db()
        with SessionLocal() as db:
            report = validate_current_seed_data(db)

    print(report.model_dump_json(indent=2))
    if not report.valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
