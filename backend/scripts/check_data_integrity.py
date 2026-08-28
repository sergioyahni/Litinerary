import argparse
import json
import sys

from app.core.database import SessionLocal
from app.core.observability import EventName, configure_logging, log_event
from app.services.data_integrity import check_database_integrity


def main() -> int:
    parser = argparse.ArgumentParser(description="Run read-only Litinerary data integrity checks.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON result.")
    args = parser.parse_args()
    configure_logging()

    with SessionLocal() as db:
        violations = check_database_integrity(db)

    status = "ok" if not violations else "failed"
    payload = {
        "integrity_status": status,
        "violations": sum(item.count for item in violations),
        "checks_failed": len(violations),
        "details": [
            {"check": item.check, "count": item.count, "detail": item.detail}
            for item in violations
        ],
    }
    event_name = (
        EventName.DATA_INTEGRITY_CHECK_COMPLETED
        if not violations
        else EventName.DATA_INTEGRITY_CHECK_FAILED
    )
    log_event(
        event_name,
        category="database_recovery",
        operation="check_data_integrity",
        integrity_status=status,
        violations=payload["violations"],
        checks_failed=payload["checks_failed"],
        success=not violations,
    )

    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"integrity_status={status}")
        print(f"violations={payload['violations']}")
        for item in violations:
            print(f"violation={item.check} count={item.count}")
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
