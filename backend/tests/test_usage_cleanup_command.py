import json
import logging
import os
import subprocess
import sys
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.database import Base
from app.core.observability import EventName
from app.models import DestinationModel, UsageLimitCounterModel
from app.services.usage_policy import (
    DatabaseUsageCounterStore,
    cleanup_expired_usage_counters,
)


def _json_messages(caplog):
    messages = []
    for record in caplog.records:
        try:
            messages.append(json.loads(record.message))
        except json.JSONDecodeError:
            continue
    return messages


def _usage_counter(
    *,
    row_id: str,
    subject_key: str,
    window_start: datetime,
    window_end: datetime,
) -> UsageLimitCounterModel:
    now = datetime(2026, 8, 15, tzinfo=UTC).isoformat()
    return UsageLimitCounterModel(
        id=row_id,
        subject_type="anonymous",
        subject_key=subject_key,
        action="itinerary_generation:day",
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
        units_used=1,
        limit_units=10,
        created_at=now,
        updated_at=now,
    )


def _destination() -> DestinationModel:
    return DestinationModel(
        id="cleanup-test-destination",
        name="Cleanup Test City",
        country="Testland",
        region=None,
        description="Durable cleanup should not touch this row.",
        latitude=1.0,
        longitude=2.0,
        image_url=None,
        supported=True,
    )


def _durable_store(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'cleanup-counters.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return database_url, DatabaseUsageCounterStore(TestingSessionLocal), TestingSessionLocal, engine


def test_cleanup_function_deletes_expired_preserves_active_and_logs_completion(
    tmp_path,
    caplog,
) -> None:
    _, store, session_factory, engine = _durable_store(tmp_path)
    current = datetime(2026, 8, 15, tzinfo=UTC)
    with session_factory() as db:
        db.add(_destination())
        db.add(
            _usage_counter(
                row_id="expired-counter",
                subject_key="expired",
                window_start=datetime(2026, 6, 1, tzinfo=UTC),
                window_end=datetime(2026, 6, 2, tzinfo=UTC),
            )
        )
        db.add(
            _usage_counter(
                row_id="active-counter",
                subject_key="active",
                window_start=datetime(2026, 8, 15, tzinfo=UTC),
                window_end=datetime(2026, 8, 16, tzinfo=UTC),
            )
        )
        db.commit()

    caplog.set_level(logging.INFO, logger="litinerary")
    removed = cleanup_expired_usage_counters(
        settings=Settings(enable_durable_usage_controls=True, usage_counter_retention_days=30),
        store=store,
        at=current,
    )
    second_removed = cleanup_expired_usage_counters(
        settings=Settings(enable_durable_usage_controls=True, usage_counter_retention_days=30),
        store=store,
        at=current,
    )

    assert removed == 1
    assert second_removed == 0
    with session_factory() as db:
        counters = db.query(UsageLimitCounterModel).all()
        assert [counter.subject_key for counter in counters] == ["active"]
        assert db.query(DestinationModel).filter_by(id="cleanup-test-destination").count() == 1
    completed = [
        item
        for item in _json_messages(caplog)
        if item["event"] == EventName.USAGE_COUNTER_CLEANUP_COMPLETED
    ]
    assert completed[0]["rows_removed"] == 1
    assert completed[0]["success"] is True
    engine.dispose()


def test_cleanup_failure_is_logged_and_raised(caplog) -> None:
    class BrokenStore:
        durable = True

        def cleanup_expired(self, *, before: datetime) -> int:
            raise SQLAlchemyError("database failed with password=redacted-test-secret")

    caplog.set_level(logging.INFO, logger="litinerary")
    with pytest.raises(SQLAlchemyError):
        cleanup_expired_usage_counters(
            settings=Settings(enable_durable_usage_controls=True),
            store=BrokenStore(),
            at=datetime(2026, 8, 15, tzinfo=UTC),
        )

    raw_messages = "\n".join(record.message for record in caplog.records)
    failure = next(
        item
        for item in _json_messages(caplog)
        if item["event"] == EventName.USAGE_COUNTER_CLEANUP_FAILED
    )
    assert failure["success"] is False
    assert failure["error_type"] == "SQLAlchemyError"
    assert "redacted-test-secret" not in raw_messages


def test_cleanup_command_reports_rows_removed_against_configured_database(tmp_path) -> None:
    database_url, _, session_factory, engine = _durable_store(tmp_path)
    with session_factory() as db:
        db.add(_destination())
        db.add(
            _usage_counter(
                row_id="script-expired-counter",
                subject_key="script-expired",
                window_start=datetime(2026, 6, 1, tzinfo=UTC),
                window_end=datetime(2026, 6, 2, tzinfo=UTC),
            )
        )
        db.add(
            _usage_counter(
                row_id="script-active-counter",
                subject_key="script-active",
                window_start=datetime(2026, 8, 15, tzinfo=UTC),
                window_end=datetime(2026, 8, 16, tzinfo=UTC),
            )
        )
        db.commit()

    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env = {
        **os.environ,
        "APP_ENV": "test",
        "LITINERARY_DATABASE_URL": database_url,
        "ENABLE_DURABLE_USAGE_CONTROLS": "true",
        "USAGE_COUNTER_RETENTION_DAYS": "30",
    }
    command = [
        sys.executable,
        "-m",
        "scripts.cleanup_usage_counters",
        "--at",
        "2026-08-15T00:00:00+00:00",
    ]

    first = subprocess.run(
        command,
        cwd=backend_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    second = subprocess.run(
        command,
        cwd=backend_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(first.stdout)["rowsRemoved"] == 1
    assert json.loads(second.stdout)["rowsRemoved"] == 0
    with session_factory() as db:
        counters = db.query(UsageLimitCounterModel).all()
        assert [counter.subject_key for counter in counters] == ["script-active"]
        assert db.query(DestinationModel).filter_by(id="cleanup-test-destination").count() == 1
    engine.dispose()
