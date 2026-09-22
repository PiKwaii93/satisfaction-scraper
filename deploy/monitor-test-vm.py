"""Bounded monitoring of the existing test Compose stack. Python 3 stdlib only."""

import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen


ROOT = Path.home() / "satisfaction-test"
SERVICES = ("postgres_db", "redis", "mlflow", "api", "frontend", "celery_worker")
DISK_ALERT_BYTES = 5 * 1024**3
COMPOSE_ENV = {
    "POSTGRES_HOST_PORT": "127.0.0.1:5432", "MLFLOW_HOST_PORT": "127.0.0.1:5000",
    "REDIS_HOST_PORT": "127.0.0.1:6379", "API_HOST_PORT": "127.0.0.1:8000",
    "FRONTEND_HOST_PORT": "127.0.0.1:5173", "DASHBOARD_HOST_PORT": "127.0.0.1:8501",
    "DB_HOST": "postgres_db", "DB_PORT": "5432", "MLFLOW_TRACKING_URI": "http://mlflow:5000",
    "CELERY_BROKER_URL": "redis://redis:6379/0", "CELERY_RESULT_BACKEND": "redis://redis:6379/1",
    "VITE_API_BASE_URL": "http://localhost:8000", "FRONTEND_BASE_URL": "http://localhost:5173",
}


def compose(sha, *args, timeout=20):
    import os
    env = os.environ.copy()
    env.update(COMPOSE_ENV)
    command = ["docker", "compose", "--project-directory", str(ROOT / "releases" / sha),
               "--env-file", str(ROOT / "shared" / "test.env"), "-p", "satisfaction-test",
               "-f", str(ROOT / "releases" / sha / "docker-compose.yml"), *args]
    return subprocess.run(command, env=env, text=True, capture_output=True, timeout=timeout, check=False)


def docker_health(sha, service):
    try:
        container = compose(sha, "ps", "--all", "-q", service)
        if container.returncode or not container.stdout.strip():
            return "missing"
        state = subprocess.run(["docker", "inspect", "--format", "{{json .State}}",
                                container.stdout.strip()], capture_output=True, text=True,
                               timeout=10, check=False)
        if state.returncode:
            return "unavailable"
        detail = json.loads(state.stdout)
        if detail.get("Status") != "running":
            return detail.get("Status", "unknown")
        return detail.get("Health", {}).get("Status", "running")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return "unavailable"


def http_ok(url):
    try:
        with urlopen(url, timeout=5) as response:
            return 200 <= response.status < 400
    except Exception:
        return False


def celery_ping(sha):
    try:
        result = compose(sha, "exec", "-T", "celery_worker", "celery", "-A",
                         "app.api.celery_app.celery_app", "inspect", "ping", "--timeout", "5",
                         timeout=15)
        return result.returncode == 0 and "pong" in result.stdout.lower()
    except (OSError, subprocess.TimeoutExpired):
        return False


def probe(sha):
    states = {service: docker_health(sha, service) for service in SERVICES}
    api_http = http_ok("http://127.0.0.1:8000/health")
    frontend_http = http_ok("http://127.0.0.1:5173/")
    ping = celery_ping(sha) if states["celery_worker"] == "running" else False
    healthy = {service: states[service] == "healthy" for service in SERVICES[:5]}
    healthy["api"] = healthy["api"] and api_http
    healthy["frontend"] = healthy["frontend"] and frontend_http
    healthy["celery_worker"] = states["celery_worker"] == "running" and ping
    return {"docker_states": states, "api_http": api_http, "frontend_http": frontend_http,
            "celery_ping": ping, "healthy": healthy}


def restart_target(first, second):
    """At most one service; only after both failed probes and healthy dependencies."""
    a, b = first["healthy"], second["healthy"]
    deps = ("postgres_db", "redis", "mlflow")
    if not a["api"] and not b["api"] and all(a[d] and b[d] for d in deps):
        return "api"
    if not a["frontend"] and not b["frontend"] and a["api"] and b["api"] and all(a[d] and b[d] for d in deps):
        return "frontend"
    return None


def monitor(sleep=time.sleep, check=probe, restart=compose):
    stamp = datetime.now(timezone.utc).isoformat()
    marker = ROOT / "current.sha"
    try:
        sha = marker.read_text(encoding="utf-8").strip() if marker.is_file() else ""
    except OSError:
        sha = ""
    source_marker = ROOT / "releases" / sha / ".source_sha"
    try:
        valid_source = source_marker.is_file() and source_marker.read_text(encoding="utf-8").strip() == sha
    except OSError:
        valid_source = False
    if not re.fullmatch(r"[0-9a-f]{40}", sha) or not valid_source:
        return {"timestamp_utc": stamp, "served_sha": None, "result": "incident",
                "ssh": "ok", "alert": "Invalid or absent current SHA", "remediation": None, "probes": []}
    free = shutil.disk_usage("/").free
    first = check(sha)
    second = None
    if not first["healthy"]["api"] or not first["healthy"]["frontend"]:
        sleep(30)
        second = check(sha)
    action = None
    final = second or first
    probes = [first] + ([second] if second else [])
    target = restart_target(first, second) if second else None
    if target:
        try:
            result = restart(sha, "restart", target, timeout=60)
            succeeded = result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            succeeded = False
        action = {"service": target, "attempts": 1, "command_succeeded": succeeded}
        final = check(sha)
        probes.append(final)
        action["healthy_after_restart"] = final["healthy"][target]
    dependencies = ("postgres_db", "redis", "mlflow", "celery_worker")
    persistent_apps = {service for service in ("api", "frontend")
                       if second and not first["healthy"][service] and not second["healthy"][service]}
    incident = (bool(action and not action["command_succeeded"])
                or any(not final["healthy"][service] for service in dependencies)
                or any(not final["healthy"][service] for service in persistent_apps))
    transient_app = any(not final["healthy"][service] for service in ("api", "frontend")) and not incident
    alert = "Less than 5 GiB free on /" if free < DISK_ALERT_BYTES else None
    if action and action["command_succeeded"] and not incident:
        alert = "; ".join(filter(None, (alert, "Confirmed application incident recovered after restart")))
    if transient_app:
        alert = "; ".join(filter(None, (alert, "Application probe failed once; incident not confirmed")))
    return {"timestamp_utc": stamp, "served_sha": sha, "ssh": "ok", "disk_free_bytes": free,
            "components": final, "probes": probes,
            "alert": alert, "remediation": action,
            "result": "incident" if incident else "alert" if alert else "healthy"}


def summary(report):
    lines = ["### Test VM supervision", "", f"- Time (UTC): {report['timestamp_utc']}",
             f"- Served SHA: {report.get('served_sha') or 'unavailable'}",
             f"- SSH: {report.get('ssh', 'ok')}"]
    components = report.get("components", {})
    for name in SERVICES:
        healthy = components.get("healthy", {}).get(name)
        state = components.get("docker_states", {}).get(name, "unknown")
        lines.append(f"- {name}: {'ok' if healthy else 'failed' if healthy is False else 'unavailable'} (Docker: {state})")
    if components:
        lines.append(f"- API HTTP: {components['api_http']}; frontend HTTP: {components['frontend_http']}; Celery ping: {components['celery_ping']}")
    free = report.get("disk_free_bytes")
    lines.append(f"- Disk free on /: {free / 1024**3:.2f} GiB" if free is not None else "- Disk free on /: unavailable")
    lines.append(f"- Alert: {report.get('alert') or 'none'}")
    action = report.get("remediation")
    lines.append(f"- Remediation: {action['service']} restart once; healthy after: {action['healthy_after_restart']}" if action else "- Remediation: none")
    meanings = {"healthy": "no confirmed anomaly", "alert": "recovered anomaly or non-critical alert",
                "incident": "unresolved anomaly or critical dependency failure"}
    lines.append(f"- Final result: {report['result']} ({meanings[report['result']]})")
    return "\n".join(lines) + "\n"


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "probe":
        report = monitor()
        print(json.dumps(report, indent=2))
        return 0 if report["result"] == "healthy" else 1
    if len(sys.argv) == 3 and sys.argv[1] == "summary":
        print(summary(json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))))
        return 0
    if len(sys.argv) == 2 and sys.argv[1] == "ssh-failure":
        print(json.dumps({"timestamp_utc": datetime.now(timezone.utc).isoformat(), "served_sha": None,
                          "ssh": "unreachable", "result": "incident", "alert": "SSH probe failed",
                          "remediation": None, "probes": []}, indent=2))
        return 0
    print("Usage: monitor-test-vm.py probe | summary REPORT.json | ssh-failure", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
