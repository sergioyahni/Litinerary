from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.services.seed_manager import load_seed_data


def main() -> None:
    if not get_settings().is_deployed_environment:
        init_db()
    with SessionLocal() as db:
        result = load_seed_data(db)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
