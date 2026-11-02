"""Check user errors and run recovery on a disposable Compose project.

Run from the repository root: python scripts/verify_application_recovery.py
No external review website or existing database is used.
"""

import json
import os
import socket
import time
import uuid

import requests

from verify_resilience import API, CSV, PORTS, checked, command, complete, login, response, run_state, wait_for


def post_csv(headers, company, content=None, mapping=None, endpoint="import-csv"):
    data = {"company": company} if endpoint == "import-csv" else {}
    if mapping is not None:
        data["column_mapping"] = mapping
    return response("POST", f"/analysis-runs/{endpoint}", headers=headers, data=data,
                    files={"file": ("test.csv", content if content is not None else CSV.read_bytes(), "text/csv")})


def expect(result, code, message):
    assert result.status_code == code, (result.status_code, result.text[:200])
    if message:
        assert message in result.json().get("detail", ""), result.text[:200]


def main():
    name = "satisfaction-app8b-" + uuid.uuid4().hex[:12]
    env = os.environ.copy()
    env.update({key: str(value) for key, value in PORTS.items()})
    env.update(DB_HOST="postgres_db", DB_PORT="5432", DB_USER="admin",
               DB_PASSWORD="application-test-password", DB_NAME="satisfaction_app8b",
               MLFLOW_TRACKING_URI="http://mlflow:5000",
               MODEL_BOOTSTRAP_PATH="/app/app/models/sentiment_model.pkl",
               MODEL_BOOTSTRAP_SHA256_PATH="/app/app/models/sentiment_model.sha256",
               CELERY_BROKER_URL="redis://redis:6379/0",
               CELERY_RESULT_BACKEND="redis://redis:6379/1",
               JWT_SECRET_KEY="application-test-jwt-secret-at-least-32-bytes",
               DEMO_ADMIN_EMAIL="demo@satisfaction.local", DEMO_ADMIN_PASSWORD="demo-password",
               VITE_API_BASE_URL=API, FRONTEND_BASE_URL="http://localhost:15174")
    compose = ["docker", "compose", "-p", name]
    for port in PORTS.values():
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError as exc:
                raise RuntimeError(f"Isolated port {port} is occupied") from exc
    assert not command(["docker", "volume", "ls", "--format", "{{.Name}}", "--filter",
                        f"label=com.docker.compose.project={name}"], env).stdout.strip()
    start = time.monotonic()
    try:
        print(f"START isolated application project {name}", flush=True)
        command(compose + ["up", "-d", "--build", "postgres_db", "redis", "mlflow",
                           "model_bootstrap", "api", "celery_worker", "frontend"], env)
        wait_for("API", lambda: response("GET", "/health").status_code == 200)
        headers = login()

        for endpoint in ("preview-csv", "import-csv"):
            expect(post_csv(headers, "empty.example", b"", endpoint=endpoint), 400,
                   "Le fichier CSV est vide.")
            expect(post_csv(headers, "blank.example", b"\n", endpoint=endpoint), 400,
                   "Le fichier CSV est vide.")
            expect(post_csv(headers, "bad-map.example", b"avis,note\nOui,5\n",
                            "{bad", endpoint), 400, "Mapping CSV invalide")
            expect(post_csv(headers, "bad-map.example", b"avis,note\nOui,5\n",
                            "[]", endpoint), 400, "Mapping CSV invalide")
        for company, content, fragment in (
            ("missing-column.example", b"stars;headline\n5;Oui\n", "Colonne obligatoire"),
            ("header-only.example", b"avis,note\n", "Aucun avis exploitable"),
        ):
            preview = checked(post_csv(headers, company, content, endpoint="preview-csv"),
                              "invalid CSV preview")
            assert preview["review_count"] == 0 and fragment in preview["error_message"]
            expect(post_csv(headers, company, content), 400, fragment)
        note = checked(post_csv(headers, "rating.example", b"avis,note\nOui,inconnue\n",
                                endpoint="preview-csv"), "tolerant rating preview")
        assert note["preview_reviews"][0]["rating"] == 3
        for mapping, fragment in ((json.dumps({"verbatim": "absent"}), "Colonne inconnue"),
                                  (json.dumps({"verbatim": ""}), "Colonne obligatoire")):
            preview = checked(post_csv(headers, "mapping.example", b"avis,note\nOui,5\n",
                                       mapping, "preview-csv"), "invalid mapped column preview")
            assert preview["review_count"] == 0 and fragment in preview["error_message"]
            expect(post_csv(headers, "mapping.example", b"avis,note\nOui,5\n", mapping),
                   400, fragment)
        unknown = checked(post_csv(headers, "unknown.example", b"avis,note\nOui,5\n",
                                   json.dumps({"unknown": "value"}), "preview-csv"),
                          "unknown mapping field")
        assert unknown["review_count"] == 1
        assert checked(response("GET", "/analysis-runs", headers=headers), "no invalid runs") == []
        print("PASS CSV validation: empty, malformed, mapping, missing column, header only; invalid rating defaults to 3", flush=True)

        command(compose + ["stop", "celery_worker"], env)
        company = "active-test.example"
        created = checked(post_csv(headers, company), "first CSV run")
        run_id = created["run_id"]
        assert run_state(headers, run_id)["status"] == "pending"
        expect(post_csv(headers, company), 409, "Un import CSV est deja")
        expect(response("POST", f"/analysis-runs/{run_id}/execute", headers=headers),
               409, "deja")
        runs = checked(response("GET", "/analysis-runs", headers=headers), "runs")
        assert sum(run["company_name"] == company for run in runs) == 1
        command(compose + ["start", "celery_worker"], env)
        complete(headers, run_id)
        print("PASS active run: duplicate import and execute rejected; one run, 15 reviews", flush=True)

        completed_retry = checked(response("POST", f"/analysis-runs/{run_id}/execute",
                                           headers=headers), "completed re-execution")
        assert completed_retry["run_id"] == run_id
        complete(headers, run_id)
        print("PASS completed run re-executed without new run or duplicate reviews", flush=True)
        next_run = checked(post_csv(headers, company), "new import after completed run")
        assert next_run["run_id"] != run_id
        complete(headers, next_run["run_id"])
        print("PASS new analysis allowed after completed run", flush=True)

        command(compose + ["stop", "celery_worker"], env)
        failed = checked(post_csv(headers, "retry-test.example"), "CSV before controlled failure")
        failed_id = failed["run_id"]
        source = f"/app/data/api_runs/run_{failed_id}_retry-test_example_reviews.json"
        held = source + ".hold"
        command(compose + ["exec", "-T", "api", "mv", source, held], env)
        command(compose + ["start", "celery_worker"], env)
        failed_run = wait_for("failed run", lambda: (
            state if (state := run_state(headers, failed_id))["status"] == "failed" else None), 45)
        time.sleep(8)  # Allow the two existing Celery autoretries to exhaust.
        assert run_state(headers, failed_id)["status"] == "failed"
        assert failed_run["error_message"] and "/app/" not in failed_run["error_message"]
        assert checked(response("GET", "/health"), "API after run failure")
        checked(response("GET", f"/analysis-runs/{failed_id}", headers=headers), "failed run read")
        events = checked(response("GET", f"/analysis-runs/{failed_id}/events",
                                  headers=headers), "failed run events")
        assert any(event["step"] == "failed" and event["level"] == "error"
                   for event in events)
        assert all("/app/" not in event["message"] for event in events)
        command(compose + ["exec", "-T", "api", "mv", held, source], env)
        after_failure = checked(post_csv(headers, "retry-test.example"),
                                "new import after failed run")
        assert after_failure["run_id"] != failed_id
        complete(headers, after_failure["run_id"])
        retried = checked(response("POST", f"/analysis-runs/{failed_id}/execute?skip_scrape=true",
                                   headers=headers), "retry failed run")
        assert retried["run_id"] == failed_id
        result = complete(headers, failed_id)
        assert result["error_message"] is None
        print("PASS failed CSV run: new import and same-run retry completed, no stale error or duplicate review", flush=True)
        print(f"PASS application recovery in {time.monotonic()-start:.2f}s", flush=True)
    finally:
        command(compose + ["down", "-v", "--remove-orphans"], env)
        for service in ("api", "celery_worker", "model_bootstrap", "frontend"):
            image = f"{name}-{service}:latest"
            if command(["docker", "image", "inspect", image], env, check=False).returncode == 0:
                command(["docker", "image", "rm", image], env)
        for kind, fmt in (("ps", "{{.ID}}"), ("network", "{{.ID}}"),
                          ("volume", "{{.Name}}")):
            base = ["docker", "ps", "-a"] if kind == "ps" else ["docker", kind, "ls"]
            remaining = command(base + ["--format", fmt, "--filter",
                                        f"label=com.docker.compose.project={name}"], env)
            assert not remaining.stdout.strip(), f"{kind} resources remain"
        print("PASS isolated cleanup", flush=True)


if __name__ == "__main__":
    main()
