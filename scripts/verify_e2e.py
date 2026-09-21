"""HTTP smoke test for the CSV flow on an isolated Compose stack."""

import os
import time
import uuid
from pathlib import Path

import requests


API_URL = os.getenv("E2E_API_URL", "http://api:8000").rstrip("/")
CSV_PATH = Path(__file__).resolve().parents[1] / "data/test_import_reviews.csv"
EXPECTED_REVIEWS = 15
TIMEOUT_SECONDS = 120


def checked(response, step):
    if not response.ok:
        raise RuntimeError(f"{step}: HTTP {response.status_code}: {response.text[:500]}")
    return response.json()


def main():
    checked(requests.get(f"{API_URL}/health", timeout=10), "API health")
    login = checked(
        requests.post(
            f"{API_URL}/auth/login",
            json={
                "email": os.getenv("DEMO_ADMIN_EMAIL", "demo@satisfaction.local"),
                "password": os.getenv("DEMO_ADMIN_PASSWORD", "demo-password"),
            },
            timeout=15,
        ),
        "Demo login",
    )
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    with CSV_PATH.open("rb") as csv_file:
        created = checked(
            requests.post(
                f"{API_URL}/analysis-runs/import-csv",
                headers=headers,
                data={"company": f"coldstart-{uuid.uuid4().hex[:12]}.example"},
                files={"file": (CSV_PATH.name, csv_file, "text/csv")},
                timeout=30,
            ),
            "CSV import",
        )
    run_id = created["run_id"]
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        run = checked(
            requests.get(f"{API_URL}/analysis-runs/{run_id}", headers=headers, timeout=15),
            f"Run {run_id}",
        )
        if run["status"] == "completed":
            break
        if run["status"] == "failed":
            raise RuntimeError(f"Run {run_id} failed: {run.get('error_message')}")
        time.sleep(2)
    else:
        raise TimeoutError(f"Run {run_id} did not complete within {TIMEOUT_SECONDS}s")

    if run["total_reviews"] != EXPECTED_REVIEWS:
        raise AssertionError(
            f"Run {run_id}: expected {EXPECTED_REVIEWS} reviews, got {run['total_reviews']}"
        )
    summary = checked(
        requests.get(
            f"{API_URL}/analysis-runs/{run_id}/summary", headers=headers, timeout=15
        ),
        f"Run {run_id} summary",
    )
    if not summary.get("kpis") or not summary.get("sentiment_distribution"):
        raise AssertionError(f"Run {run_id}: summary lacks KPIs or sentiment distribution")
    print(f"PASS CSV E2E: login, run {run_id} completed, {EXPECTED_REVIEWS} reviews, summary")


if __name__ == "__main__":
    main()
