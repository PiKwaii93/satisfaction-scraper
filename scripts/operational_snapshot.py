"""Read-only snapshot of analysis runs. Run from the repository root.

The database stores naive timestamps produced by PostgreSQL NOW(). This tool
requires a UTC database session so its observation window is unambiguous.
"""

import argparse
import json
import statistics
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from psycopg2.extras import RealDictCursor

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.database import get_connection


TERMINAL_STATUSES = ("completed", "failed", "empty")
ACTIVE_STATUSES = ("pending", "running")
PUBLIC_ERRORS = frozenset({
    "Service de traitement temporairement indisponible.",
    "Les donnees de cette analyse sont introuvables. Verifie la source avant de relancer l'analyse.",
    "La collecte ou l'analyse Trustpilot a echoue. Verifie la cible avant de relancer l'analyse.",
    "L'analyse du CSV a echoue. Verifie l'import avant de relancer l'analyse.",
})


def utc_iso(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def public_error(message):
    return message if message in PUBLIC_ERRORS else "Erreur non détaillée (message conservé en base)."


def parse_since(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--since doit être une date ISO 8601 avec fuseau horaire") from exc
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("--since doit inclure un fuseau horaire")
    return parsed.astimezone(timezone.utc)


def positive_hours(value):
    try:
        hours = float(value)
        if not 0 < hours <= 24 * 365:
            raise ValueError
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--hours doit être entre 0 et 8760") from exc
    return hours


def failure_limit(value):
    try:
        limit = int(value)
        if not 0 <= limit <= 100:
            raise ValueError
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--failure-limit doit être entre 0 et 100") from exc
    return limit


def build_snapshot(rows, active_rows, *, since, until, limit):
    counts = Counter(row["status"] for row in rows)
    by_status = {status: counts.pop(status, 0) for status in (*ACTIVE_STATUSES, *TERMINAL_STATUSES)}
    by_status.update(sorted(counts.items()))
    completed = by_status["completed"]
    failed = by_status["failed"]
    terminal_count = completed + failed
    durations = [
        (row["finished_at"] - row["started_at"]).total_seconds()
        for row in rows
        if row["status"] == "completed"
        and row["started_at"] is not None
        and row["finished_at"] is not None
        and row["finished_at"] >= row["started_at"]
    ]
    completed_reviews = [row["total_reviews"] for row in rows if row["status"] == "completed"]
    volume_available = all(value is not None and value >= 0 for value in completed_reviews)
    oldest = min(active_rows, key=lambda row: (row["created_at"], row["run_id"])) if active_rows else None
    failures = sorted(
        (row for row in rows if row["status"] == "failed"),
        key=lambda row: (row["finished_at"] or row["created_at"], row["run_id"]),
        reverse=True,
    )[:limit]
    return {
        "generated_at": until.isoformat().replace("+00:00", "Z"),
        "window": {
            "since": since.isoformat().replace("+00:00", "Z"),
            "until": until.isoformat().replace("+00:00", "Z"),
            "selection": "terminal: finished_at (created_at if missing); other: created_at",
        },
        "runs": {
            "total": len(rows), "by_status": by_status,
            "terminal_success_rate": round(completed / terminal_count, 4) if terminal_count else None,
            "terminal_success_rate_definition": "completed / (completed + failed); empty excluded",
        },
        "active": {
            "count": len(active_rows),
            "by_status": {status: sum(row["status"] == status for row in active_rows) for status in ACTIVE_STATUSES},
            "oldest_run_id": oldest["run_id"] if oldest else None,
            "oldest_created_at": utc_iso(oldest["created_at"]) if oldest else None,
            "oldest_age_seconds": max(0, round((until.replace(tzinfo=None) - oldest["created_at"]).total_seconds(), 3)) if oldest else None,
        },
        "completed_duration": {
            "definition": "finished_at - started_at for completed runs with both valid timestamps",
            "count": len(durations),
            "mean_seconds": round(statistics.mean(durations), 3) if durations else None,
            "median_seconds": round(statistics.median(durations), 3) if durations else None,
            "max_seconds": round(max(durations), 3) if durations else None,
        },
        "reviews": {
            "processed": sum(completed_reviews) if volume_available else None,
            "definition": "sum of persisted total_reviews for completed runs in window",
        },
        "by_source": dict(sorted(Counter(row["source"] for row in rows).items())),
        "recent_failures": [
            {"run_id": row["run_id"], "company": row["company_name"], "source": row["source"],
             "finished_at": utc_iso(row["finished_at"]), "error_message": public_error(row["error_message"])}
            for row in failures
        ],
    }


def fetch_snapshot(*, since, until, limit):
    with get_connection() as connection:
        connection.set_session(readonly=True, isolation_level="REPEATABLE READ")
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SHOW TIME ZONE")
            db_timezone = cursor.fetchone()["TimeZone"]
            if db_timezone not in {"UTC", "Etc/UTC", "GMT", "Etc/GMT"}:
                raise RuntimeError("Le fuseau de la base doit être UTC pour lire ces timestamps sans fuseau")
            cursor.execute(
                """
                SELECT ar.run_id, ar.status, ar.source, ar.created_at, ar.started_at,
                       ar.finished_at, ar.total_reviews, ar.error_message, c.company_name
                FROM analysis_runs ar
                JOIN companies c ON c.company_id = ar.company_id
                WHERE (CASE WHEN ar.status IN ('completed', 'failed', 'empty')
                            THEN COALESCE(ar.finished_at, ar.created_at)
                            ELSE ar.created_at END) >= %s
                  AND (CASE WHEN ar.status IN ('completed', 'failed', 'empty')
                            THEN COALESCE(ar.finished_at, ar.created_at)
                            ELSE ar.created_at END) < %s;
                """, (since.replace(tzinfo=None), until.replace(tzinfo=None)),
            )
            rows = cursor.fetchall()
            cursor.execute(
                """SELECT run_id, status, created_at FROM analysis_runs
                   WHERE status IN ('pending', 'running');"""
            )
            active_rows = cursor.fetchall()
    return build_snapshot(rows, active_rows, since=since, until=until, limit=limit)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    period = parser.add_mutually_exclusive_group()
    period.add_argument("--hours", type=positive_hours, default=24)
    period.add_argument("--since", type=parse_since)
    parser.add_argument("--failure-limit", type=failure_limit, default=5)
    parser.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args(argv)
    until = datetime.now(timezone.utc)
    since = args.since or until - timedelta(hours=args.hours)
    if since >= until:
        parser.error("--since doit être antérieur à maintenant")
    snapshot = fetch_snapshot(since=since, until=until, limit=args.failure_limit)
    if args.format == "json":
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    else:
        runs = snapshot["runs"]
        active = snapshot["active"]
        print(f"Analyses depuis {snapshot['window']['since']} : {runs['total']}")
        print(f"Terminées : {runs['by_status']['completed']} ; échecs : {runs['by_status']['failed']}")
        print(f"Actives : {active['count']} ; plus ancienne : {active['oldest_run_id']} ({active['oldest_age_seconds']} s)")
        rate = runs["terminal_success_rate"]
        print(f"Taux de succès terminal : {rate * 100:.1f} %" if rate is not None else "Taux de succès terminal : indisponible")
        print(f"Échecs récents : {len(snapshot['recent_failures'])}")


if __name__ == "__main__":
    main()
