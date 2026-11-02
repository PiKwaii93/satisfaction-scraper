"""Snapshot arithmetic and optional real-PostgreSQL query on disposable DB only."""

from datetime import datetime, timedelta, timezone
import os
import subprocess
import sys
import uuid

import psycopg2
import pytest
from psycopg2 import sql

from app.api.database import get_db_config, run_schema_migrations
from scripts.operational_snapshot import (
    build_snapshot, failure_limit, fetch_snapshot, parse_since, positive_hours,
    public_error,
)


NOW = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
BASE = NOW.replace(tzinfo=None)


def run(run_id, status, *, created=30, started=None, finished=None, reviews=0, error=None):
    return {
        "run_id": run_id, "status": status, "source": "csv",
        "company_name": "Société test", "created_at": BASE - timedelta(seconds=created),
        "started_at": BASE - timedelta(seconds=started) if started is not None else None,
        "finished_at": BASE - timedelta(seconds=finished) if finished is not None else None,
        "total_reviews": reviews, "error_message": error,
    }


def snapshot(rows=(), active=(), limit=5):
    return build_snapshot(rows, active, since=NOW - timedelta(hours=24), until=NOW, limit=limit)


def test_zero_runs_has_no_invented_rate_or_duration():
    result = snapshot()
    assert result["runs"]["total"] == 0
    assert result["runs"]["terminal_success_rate"] is None
    assert result["completed_duration"]["mean_seconds"] is None
    assert result["active"]["oldest_run_id"] is None
    assert result["reviews"]["processed"] == 0


def test_completed_durations_and_processed_volume():
    result = snapshot([run(1, "completed", started=25, finished=5, reviews=15),
                       run(2, "completed", started=40, finished=10, reviews=5)])
    assert result["runs"]["terminal_success_rate"] == 1
    assert result["completed_duration"]["count"] == 2
    assert result["completed_duration"]["mean_seconds"] == 25
    assert result["completed_duration"]["median_seconds"] == 25
    assert result["completed_duration"]["max_seconds"] == 30
    assert result["reviews"]["processed"] == 20


def test_mixed_statuses_active_age_failures_and_safe_errors():
    rows = [run(1, "completed", started=20, finished=2, reviews=15),
            run(2, "failed", finished=4, error="/app/secret?token=abc"),
            run(3, "failed", finished=3, error="Service de traitement temporairement indisponible."),
            run(4, "pending", created=120), run(5, "running", created=60),
            run(6, "empty", finished=1)]
    result = snapshot(rows, [rows[3], rows[4]], limit=1)
    assert result["runs"]["total"] == 6
    assert result["runs"]["terminal_success_rate"] == round(1 / 3, 4)
    assert result["runs"]["by_status"]["empty"] == 1
    assert result["active"]["by_status"] == {"pending": 1, "running": 1}
    assert result["active"]["oldest_run_id"] == 4
    assert result["active"]["oldest_age_seconds"] == 120
    assert len(result["recent_failures"]) == 1
    assert result["recent_failures"][0]["run_id"] == 3
    assert "token" not in str(snapshot(rows, [], limit=5)["recent_failures"])
    assert public_error(None).startswith("Erreur non détaillée")


def test_completed_without_valid_timestamps_excluded_from_duration_only():
    result = snapshot([run(1, "completed", reviews=3),
                       run(2, "completed", started=2, finished=4, reviews=4)])
    assert result["runs"]["by_status"]["completed"] == 2
    assert result["completed_duration"]["count"] == 0
    assert result["completed_duration"]["mean_seconds"] is None
    assert result["reviews"]["processed"] == 7


@pytest.mark.parametrize("value", ["0", "-1", "nan", "9000", "abc"])
def test_invalid_hours(value):
    with pytest.raises(Exception):
        positive_hours(value)


@pytest.mark.parametrize("value", ["-1", "101", "abc"])
def test_invalid_failure_limit(value):
    with pytest.raises(Exception):
        failure_limit(value)


def test_since_requires_timezone():
    with pytest.raises(Exception):
        parse_since("2026-11-01T00:00:00")
    assert parse_since("2026-11-01T01:00:00+01:00") == datetime(2026, 11, 1, tzinfo=timezone.utc)


@pytest.mark.skipif(os.getenv("OPERATIONAL_SNAPSHOT_TEST_DB") != "1", reason="requires disposable PostgreSQL")
def test_real_query_on_disposable_database(monkeypatch):
    config = get_db_config()
    assert config["database"].startswith("snapshot_test_"), "Refusing non-test database"
    temp_name = f"snapshot_test_{uuid.uuid4().hex}"
    maintenance = {**config, "database": "postgres"}
    conn = psycopg2.connect(**maintenance)
    try:
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(temp_name)))
    finally:
        conn.close()
    try:
        monkeypatch.setenv("DB_NAME", temp_name)
        run_schema_migrations()
        with psycopg2.connect(**get_db_config()) as conn:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO organizations (name, slug) VALUES ('Snapshot test', 'snapshot-test') RETURNING organization_id")
                organization_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO companies (organization_id, company_name, trustpilot_slug) VALUES (%s, 'Entreprise test', 'snapshot-test') RETURNING company_id", (organization_id,))
                company_id = cursor.fetchone()[0]
                for status, created, started, finished, reviews, error in [
                    ("completed", 100, 70, 10, 15, None),
                    ("failed", 90, 60, 20, 0, "/app/private/secret"),
                    ("pending", 120, None, None, 0, None),
                    ("running", 80, 50, None, 0, None),
                    ("empty", 70, 40, 5, 0, None),
                ]:
                    cursor.execute(
                        """INSERT INTO analysis_runs
                           (organization_id, company_id, source, status, total_reviews,
                            created_at, started_at, finished_at, error_message)
                           VALUES (%s, %s, 'csv', %s, %s, NOW() - %s * INTERVAL '1 second',
                                   CASE WHEN %s IS NULL THEN NULL ELSE NOW() - %s * INTERVAL '1 second' END,
                                   CASE WHEN %s IS NULL THEN NULL ELSE NOW() - %s * INTERVAL '1 second' END, %s)""",
                        (organization_id, company_id, status, reviews, created,
                         started, started, finished, finished, error),
                    )
        observed = fetch_snapshot(since=datetime.now(timezone.utc) - timedelta(hours=1),
                                  until=datetime.now(timezone.utc), limit=5)
        assert observed["runs"]["total"] == 5
        assert observed["runs"]["by_status"] == {"pending": 1, "running": 1, "completed": 1, "failed": 1, "empty": 1}
        assert observed["runs"]["terminal_success_rate"] == 0.5
        assert observed["completed_duration"]["mean_seconds"] == 60
        assert observed["reviews"]["processed"] == 15
        assert observed["active"]["count"] == 2
        assert observed["recent_failures"][0]["error_message"].startswith("Erreur non détaillée")
        completed = subprocess.run(
            [sys.executable, "-m", "scripts.operational_snapshot", "--hours", "1"],
            capture_output=True, text=True, check=True,
        )
        import json
        from_cli = json.loads(completed.stdout)
        assert from_cli["runs"]["by_status"] == observed["runs"]["by_status"]
        assert from_cli["reviews"]["processed"] == 15
        assert "/app/private" not in completed.stdout
        print("ISOLATED SNAPSHOT: 5 runs; completed=1 failed=1 pending=1 running=1 empty=1; "
              "success=0.5; processed=15; duration=60s; active=2; failure redacted")
    finally:
        monkeypatch.setenv("DB_NAME", config["database"])
        conn = psycopg2.connect(**maintenance)
        try:
            conn.autocommit = True
            with conn.cursor() as cursor:
                cursor.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(temp_name)))
        finally:
            conn.close()
