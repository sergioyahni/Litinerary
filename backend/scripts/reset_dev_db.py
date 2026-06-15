from app.core.database import SessionLocal, init_db
from app.services.seed_manager import reset_dev_data


def main() -> None:
    init_db()
    with SessionLocal() as db:
        result = reset_dev_data(db)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
