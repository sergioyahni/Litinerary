import argparse
import json
import sys
from datetime import UTC, datetime

from app.core.config import get_settings
from app.core.observability import configure_logging
from app.services.usage_policy import cleanup_expired_usage_counters


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Delete expired durable usage limit counters from the configured database."
    )
    parser.add_argument(
        "--at",
        help="UTC cleanup reference timestamp for deterministic tests, in ISO 8601 format.",
    )
    args = parser.parse_args()
    configure_logging()
    settings = get_settings()
    at = _parse_at(args.at)

    try:
        rows_removed = cleanup_expired_usage_counters(settings=settings, at=at)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "operation": "cleanup_expired_usage_counters",
                    "appEnv": settings.app_env,
                    "errorType": exc.__class__.__name__,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "status": "completed",
                "operation": "cleanup_expired_usage_counters",
                "appEnv": settings.app_env,
                "retentionDays": settings.usage_counter_retention_days,
                "rowsRemoved": rows_removed,
            },
            sort_keys=True,
        )
    )
    return 0


def _parse_at(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None
    parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


if __name__ == "__main__":
    sys.exit(main())
