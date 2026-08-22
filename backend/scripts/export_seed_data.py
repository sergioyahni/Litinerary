import argparse
from pathlib import Path

from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.services.seed_manager import export_seed_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Litinerary seed data to JSON.")
    parser.add_argument("path", help="Output JSON path.")
    args = parser.parse_args()

    if not get_settings().is_deployed_environment:
        init_db()
    with SessionLocal() as db:
        payload = export_seed_data(db)

    path = Path(args.path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.model_dump_json(indent=2), encoding="utf-8")
    print(f"Exported seed data to {path}")


if __name__ == "__main__":
    main()
