"""Run Alembic upgrade and seed checks against a disposable SQLite DB."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
DB_PATH = ROOT / "tests" / ".artifacts" / "tmp" / "ci-migration-seed.db"


def main() -> int:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "test",
            "LITINERARY_DATABASE_URL": f"sqlite:///{DB_PATH.as_posix()}",
        }
    )

    heads = run([sys.executable, "-m", "alembic", "heads"], env=env)
    run([sys.executable, "-m", "alembic", "upgrade", "head"], env=env)
    run([sys.executable, "-m", "scripts.seed_database"], env=env)
    counts = run(
        [
            sys.executable,
            "-c",
            (
                "import json; "
                "from app.core.database import SessionLocal; "
                "from app.models.domain import DestinationModel, BookModel, POIModel, ItineraryModel, UsageLimitCounterModel; "
                "db=SessionLocal(); "
                "print(json.dumps({"
                "'destinations': db.query(DestinationModel).count(), "
                "'books': db.query(BookModel).count(), "
                "'pois': db.query(POIModel).count(), "
                "'itineraries': db.query(ItineraryModel).count(), "
                "'usage_counters': db.query(UsageLimitCounterModel).count()"
                "})); "
                "db.close()"
            ),
        ],
        env=env,
    )
    payload = {
        "head": heads.split()[0],
        "counts": json.loads(counts),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def run(command: list[str], *, env: dict[str, str]) -> str:
    result = subprocess.run(
        command,
        cwd=BACKEND,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    if result.stderr:
        print(result.stderr, end="")
    if result.stdout:
        print(result.stdout, end="")
    return result.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
