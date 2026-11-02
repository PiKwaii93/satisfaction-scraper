"""Exercise dependency outages on a disposable Compose project only.

Run from the repository root with ``python scripts/verify_resilience.py``.
The fixed host ports are deliberately different from the normal local stack.
"""

import argparse
import os
import socket
import subprocess
import time
import uuid
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data/test_import_reviews.csv"
API = "http://127.0.0.1:18001"
PORTS = {"POSTGRES_HOST_PORT": 15433, "REDIS_HOST_PORT": 16380,
         "MLFLOW_HOST_PORT": 15001, "API_HOST_PORT": 18001,
         "FRONTEND_HOST_PORT": 15174}


def command(args, env, *, check=True):
    result = subprocess.run(args, cwd=ROOT, env=env, text=True,
                            capture_output=True, timeout=240)
    if check and result.returncode:
        raise RuntimeError(f"Command failed ({' '.join(args)}): {result.stderr[-1200:]}")
    return result


def wait_for(label, probe, timeout=120):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            value = probe()
            if value:
                return value
        except (requests.RequestException, ValueError) as exc:
            last = str(exc)
        time.sleep(1)
    raise TimeoutError(f"{label} did not recover within {timeout}s: {last}")


def response(method, path, **kwargs):
    return requests.request(method, API + path, timeout=15, **kwargs)


def healthy():
    result = response("GET", "/health")
    return result if result.status_code == 200 else None


def checked(result, step):
    if not result.ok:
        raise AssertionError(f"{step}: HTTP {result.status_code}: {result.text[:250]}")
    return result.json()


def login():
    data = checked(response("POST", "/auth/login", json={
        "email": "demo@satisfaction.local", "password": "demo-password"}), "login")
    return {"Authorization": f"Bearer {data['access_token']}"}


def submit(headers, company):
    with CSV.open("rb") as file:
        return response("POST", "/analysis-runs/import-csv", headers=headers,
                        data={"company": company},
                        files={"file": (CSV.name, file, "text/csv")})


def run_state(headers, run_id):
    return checked(response("GET", f"/analysis-runs/{run_id}", headers=headers), "run state")


def complete(headers, run_id):
    def probe():
        state = run_state(headers, run_id)
        if state["status"] == "failed":
            raise AssertionError(f"Run {run_id} failed: {state.get('error_message')}")
        return state if state["status"] == "completed" else None
    state = wait_for("CSV run", probe, 120)
    assert state["total_reviews"] == 15, state["total_reviews"]
    summary = checked(response("GET", f"/analysis-runs/{run_id}/summary",
                               headers=headers), "summary")
    assert summary.get("kpis") and summary.get("sentiment_distribution")
    reviews = checked(response("GET", f"/analysis-runs/{run_id}/reviews?limit=100",
                               headers=headers), "analyzed reviews")
    assert reviews["total"] == 15 and len(reviews["reviews"]) == 15
    assert len({review["review_id"] for review in reviews["reviews"]}) == 15
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observe-redis", action="store_true",
                        help="Record the current Redis failure behavior before a fix")
    parser.add_argument("--bootstrap-failure", action="store_true",
                        help="Verify that a failed one-shot bootstrap blocks dependent services")
    args = parser.parse_args()
    name = "satisfaction-resilience-" + uuid.uuid4().hex[:12]
    env = os.environ.copy()
    env.update({key: str(value) for key, value in PORTS.items()})
    env.update(DB_HOST="postgres_db", DB_PORT="5432", DB_USER="admin",
               DB_PASSWORD="resilience-test-password", DB_NAME="satisfaction_resilience",
               MLFLOW_TRACKING_URI="http://mlflow:5000",
               MODEL_BOOTSTRAP_PATH="/app/app/models/sentiment_model.pkl",
               MODEL_BOOTSTRAP_SHA256_PATH="/app/app/models/sentiment_model.sha256",
               CELERY_BROKER_URL="redis://redis:6379/0",
               CELERY_RESULT_BACKEND="redis://redis:6379/1",
               JWT_SECRET_KEY="resilience-test-jwt-secret-at-least-32-bytes",
               DEMO_ADMIN_EMAIL="demo@satisfaction.local",
               DEMO_ADMIN_PASSWORD="demo-password",
               VITE_API_BASE_URL=API,
               FRONTEND_BASE_URL="http://localhost:15174")
    compose = ["docker", "compose", "-p", name]
    for port in PORTS.values():
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError as exc:
                raise RuntimeError(f"Isolated port {port} is occupied; no stack started") from exc
    command(["docker", "compose", "version"], env)
    existing = command(["docker", "volume", "ls", "--format", "{{.Name}}",
                        "--filter", f"label=com.docker.compose.project={name}"], env)
    if existing.stdout.strip():
        raise RuntimeError(f"Refusing to reuse existing project {name}")
    started = time.monotonic()
    try:
        print(f"START isolated project {name}", flush=True)
        if args.bootstrap_failure:
            env["MODEL_BOOTSTRAP_SHA256_PATH"] = "/app/nonexistent-resilience-check.sha256"
            outcome = command(compose + ["up", "-d", "--build", "postgres_db", "redis",
                                         "mlflow", "model_bootstrap", "api"], env, check=False)
            assert outcome.returncode != 0, "Bootstrap unexpectedly succeeded"
            bootstrap_id = command(compose + ["ps", "-a", "-q", "model_bootstrap"],
                                   env).stdout.strip()
            assert bootstrap_id, "Bootstrap container missing"
            exit_code = command(["docker", "inspect", "-f", "{{.State.ExitCode}}",
                                 bootstrap_id], env).stdout.strip()
            api_id = command(compose + ["ps", "-a", "-q", "api"], env).stdout.strip()
            api_running = (command(["docker", "inspect", "-f", "{{.State.Running}}",
                                    api_id], env).stdout.strip() if api_id else "false")
            assert exit_code != "0" and api_running == "false", (exit_code, api_running)
            print(f"PASS model_bootstrap failed (exit {exit_code}); API did not start",
                  flush=True)
            return
        command(compose + ["up", "-d", "--build", "postgres_db", "redis", "mlflow",
                           "model_bootstrap", "api", "celery_worker", "frontend"], env)
        wait_for("API baseline", healthy)
        wait_for("frontend baseline", lambda: requests.get(
            "http://127.0.0.1:15174/", timeout=5).status_code == 200)
        headers = login()
        print("PASS isolated baseline and login", flush=True)

        t = time.monotonic()
        command(compose + ["stop", "postgres_db"], env)
        failed = response("GET", "/health")
        detection = time.monotonic() - t
        assert failed.status_code == 503, (failed.status_code, failed.text[:200])
        assert failed.json()["detail"] == "PostgreSQL indisponible."
        command(compose + ["start", "postgres_db"], env)
        wait_for("PostgreSQL recovery", healthy)
        checked(response("GET", "/analysis-runs", headers=headers), "DB business read")
        print(f"PASS PostgreSQL: HTTP 503 in {detection:.2f}s; recovered in "
              f"{time.monotonic()-t:.2f}s", flush=True)

        t = time.monotonic()
        command(compose + ["stop", "celery_worker"], env)
        created = checked(submit(headers, f"worker-off-{uuid.uuid4().hex[:8]}.example"),
                          "CSV while worker stopped")
        run_id = created["run_id"]
        time.sleep(3)
        assert run_state(headers, run_id)["status"] == "pending"
        assert healthy()
        command(compose + ["start", "celery_worker"], env)
        complete(headers, run_id)
        print(f"PASS Celery: queued pending, completed with 15 reviews in "
              f"{time.monotonic()-t:.2f}s", flush=True)

        t = time.monotonic()
        company = f"redis-off-{uuid.uuid4().hex[:8]}.example"
        command(compose + ["stop", "redis"], env)
        failure = submit(headers, company)
        dispatch_time = time.monotonic() - t
        runs = checked(response("GET", "/analysis-runs", headers=headers), "runs after dispatch")
        matching = [run for run in runs if run.get("company_name") == company]
        status = matching[0]["status"] if matching else "not created"
        print(f"OBSERVE Redis: HTTP {failure.status_code} in {dispatch_time:.2f}s; "
              f"body={failure.text[:200]!r}; run={status}", flush=True)
        if not args.observe_redis:
            assert failure.status_code == 503, failure.status_code
            assert failure.json()["detail"] == "Service de traitement temporairement indisponible."
            assert status == "failed", status
        command(compose + ["start", "redis"], env)
        wait_for("Redis health", lambda: command(compose + ["exec", "-T", "redis",
                  "redis-cli", "ping"], env, check=False).returncode == 0)
        recovered = checked(submit(headers, f"redis-back-{uuid.uuid4().hex[:8]}.example"),
                            "CSV after Redis recovery")
        complete(headers, recovered["run_id"])
        print(f"PASS Redis recovery: 15 reviews; scenario {time.monotonic()-t:.2f}s",
              flush=True)
        print(f"PASS all scenarios in {time.monotonic()-started:.2f}s", flush=True)
    finally:
        cleanup_errors = []
        cleanup = command(compose + ["down", "-v", "--remove-orphans"], env, check=False)
        if cleanup.returncode:
            cleanup_errors.append(f"Compose down failed: {cleanup.stderr[-300:]}")
        for service in ("api", "celery_worker", "model_bootstrap", "frontend"):
            image = f"{name}-{service}:latest"
            if command(["docker", "image", "inspect", image], env, check=False).returncode == 0:
                removed = command(["docker", "image", "rm", image], env, check=False)
                if removed.returncode:
                    cleanup_errors.append(f"Image {image} remains")
        for resource in ("ps", "network", "volume"):
            args = (["docker", "ps", "-a"] if resource == "ps" else
                    ["docker", resource, "ls"])
            field = "{{.Name}}" if resource == "volume" else "{{.ID}}"
            remaining = command(args + ["--format", field,
                                       "--filter", f"label=com.docker.compose.project={name}"],
                                env, check=False)
            if remaining.returncode or remaining.stdout.strip():
                cleanup_errors.append(f"{resource} resources remain for {name}")
        if cleanup_errors:
            raise RuntimeError("; ".join(cleanup_errors))
        print(f"PASS cleanup: no containers, networks, volumes or project images for {name}",
              flush=True)


if __name__ == "__main__":
    main()
