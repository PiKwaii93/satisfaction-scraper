"""Offline checks for the test-VM DevOps evidence and bounded remediation."""

import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


kpis = load_module("deployment_kpis", "scripts/deployment_kpis.py")
monitor = load_module("monitor_test_vm", "deploy/monitor-test-vm.py")


def test_four_real_run_metadata_classification():
    cases = [
        (35711099951, "failure", "2026-09-22T09:33:52Z", "2026-09-22T09:34:24Z", None),
        (35711897415, "failure", "2026-09-22T09:42:24Z", "2026-09-22T09:42:45Z", None),
        (35712061341, "success", "2026-09-22T09:44:10Z", "2026-09-22T09:50:20Z", "2026-09-22T09:50:16Z"),
        (35716640160, "success", "2026-09-22T10:33:30Z", "2026-09-22T10:34:35Z", "2026-09-22T10:34:33Z"),
    ]
    rows = []
    for run_id, conclusion, created, updated, deployed_at in cases:
        run = {"id": run_id, "head_sha": "a" * 40, "created_at": created,
               "updated_at": updated, "conclusion": conclusion}
        steps = [{"name": "Prepare existing VM with Ansible",
                  "conclusion": "failure" if conclusion == "failure" else "success"},
                 {"name": kpis.DEPLOY_STEP, "conclusion": "skipped" if conclusion == "failure" else "success",
                  "completed_at": deployed_at}]
        rows.append(kpis.classify_run(run, [{"steps": steps}]))
    assert [row["failure_phase"] for row in rows] == ["pre-deployment", "pre-deployment", None, None]
    assert [row["failed_step"] for row in rows[:2]] == ["Prepare existing VM with Ansible"] * 2
    result = kpis.summarize(rows)
    assert result["success_rate"] == 0.5
    assert result["deployment_frequency_by_utc_day"] == {"2026-09-22": 2}
    assert result["cycle_seconds_by_run"] == {"35712061341": 366, "35716640160": 63}
    assert kpis.summarize(rows[2:])["success_rate"] == 1.0


def fake_probe(api=True, frontend=True, postgres=True, redis=True, mlflow=True, celery=True):
    healthy = {"postgres_db": postgres, "redis": redis, "mlflow": mlflow,
               "api": api, "frontend": frontend, "celery_worker": celery}
    return {"healthy": healthy, "docker_states": {key: "healthy" for key in healthy},
            "api_http": api, "frontend_http": frontend, "celery_ping": celery}


def monitor_root(monkeypatch, tmp_path, sha="d" * 40, free_gib=10):
    root = tmp_path / "satisfaction-test"
    release = root / "releases" / sha
    release.mkdir(parents=True)
    (release / ".source_sha").write_text(sha)
    (root / "current.sha").write_text(sha)
    monkeypatch.setattr(monitor, "ROOT", root)
    monkeypatch.setattr(monitor.shutil, "disk_usage",
                        lambda _: SimpleNamespace(free=free_gib * 1024**3))
    return sha


def supported_release(monkeypatch, tmp_path):
    sha = monitor_root(monkeypatch, tmp_path)
    script = monitor.ROOT / "releases" / sha / "scripts" / "operational_snapshot.py"
    script.parent.mkdir(parents=True)
    script.write_text("# synthetic test marker\n", encoding="utf-8")
    return sha


def sample_snapshot(*, failed=0, pending=0, running=0, age=None):
    return {"runs": {"total": 2 + failed + pending + running,
                     "by_status": {"completed": 2, "failed": failed, "pending": pending,
                                   "running": running, "empty": 0},
                     "terminal_success_rate": 2 / (2 + failed)},
            "active": {"count": pending + running, "oldest_run_id": 7 if pending + running else None,
                       "oldest_age_seconds": age},
            "reviews": {"processed": 15},
            "completed_duration": {"mean_seconds": 10, "median_seconds": 9,
                                   "max_seconds": 14},
            "recent_failures": [{"run_id": 9, "error_message": "safe"}] if failed else []}


def available(snapshot):
    return {"supported": True, "available": True, "window_hours": 24, "snapshot": snapshot}


def test_old_release_remains_healthy_without_snapshot_or_remediation(monkeypatch, tmp_path):
    monitor_root(monkeypatch, tmp_path)
    report = monitor.monitor(check=lambda _: fake_probe(),
                             collect=lambda _: (_ for _ in ()).throw(AssertionError("snapshot")),
                             restart=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("restart")))
    assert report["result"] == "healthy" and report["alert"] is None
    assert report["application_snapshot"] == {
        "supported": False, "available": False,
        "reason": "served_release_predates_operational_snapshot"}
    assert report["remediation"] is None
    assert "unsupported by served release" in monitor.summary(report)


def test_supported_snapshot_command_and_healthy_summary(monkeypatch, tmp_path):
    sha = supported_release(monkeypatch, tmp_path)
    calls = []

    def run(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout=json.dumps(sample_snapshot(pending=1, age=90000)))

    result = monitor.application_snapshot(sha, run=run)
    assert calls == [((sha, "exec", "-T", "api", "python", "scripts/operational_snapshot.py",
                       "--hours", "24", "--failure-limit", "5", "--format", "json"),
                      {"timeout": 20})]
    report = monitor.monitor(check=lambda _: fake_probe(), collect=lambda _: result,
                             restart=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("restart")))
    assert report["result"] == "healthy" and report["remediation"] is None
    assert report["application_snapshot"]["snapshot"]["active"]["oldest_age_seconds"] == 90000
    text = monitor.summary(report)
    assert "### Application analyses" in text and "- Completed: 2" in text
    assert "- Terminal success rate: 100.0%" in text
    assert "- Active runs: 1" in text and "- Processed reviews: 15" in text


@pytest.mark.parametrize("failed,expected", [
    (1, "1 failed analysis run in the last 24h"),
    (3, "3 failed analysis runs in the last 24h"),
])
def test_failed_runs_alert_without_remediation(monkeypatch, tmp_path, failed, expected):
    supported_release(monkeypatch, tmp_path)
    report = monitor.monitor(check=lambda _: fake_probe(),
                             collect=lambda _: available(sample_snapshot(failed=failed)),
                             restart=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("restart")))
    assert report["result"] == "alert" and report["alert"] == expected
    assert report["remediation"] is None
    assert report["application_snapshot"]["snapshot"]["runs"]["by_status"]["failed"] == failed


@pytest.mark.parametrize("outcome", [
    SimpleNamespace(returncode=1, stdout="private path", stderr="secret"),
    SimpleNamespace(returncode=0, stdout=""),
    SimpleNamespace(returncode=0, stdout="not json"),
    SimpleNamespace(returncode=0, stdout='{"runs": {"by_status": {"failed": 1}}}'),
    subprocess.TimeoutExpired("docker", 20, output="private path", stderr="secret"),
])
def test_snapshot_collection_failure_is_alert_without_raw_output(monkeypatch, tmp_path, outcome):
    sha = supported_release(monkeypatch, tmp_path)

    def run(*args, **kwargs):
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    result = monitor.application_snapshot(sha, run=run)
    report = monitor.monitor(check=lambda _: fake_probe(), collect=lambda _: result,
                             restart=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("restart")))
    assert report["application_snapshot"] == {"supported": True, "available": False,
                                                "reason": "snapshot_collection_failed"}
    assert report["result"] == "alert" and report["remediation"] is None
    assert "private path" not in json.dumps(report) and "secret" not in json.dumps(report)
    assert "Application snapshot: unavailable" in monitor.summary(report)


def test_infrastructure_incident_precedes_application_alert(monkeypatch, tmp_path):
    supported_release(monkeypatch, tmp_path)
    report = monitor.monitor(check=lambda _: fake_probe(redis=False),
                             collect=lambda _: available(sample_snapshot(failed=1)))
    assert report["result"] == "incident"
    assert "failed analysis run" in report["alert"]
    assert report["remediation"] is None


def test_unhealthy_database_skips_snapshot_and_keeps_incident(monkeypatch, tmp_path):
    supported_release(monkeypatch, tmp_path)
    report = monitor.monitor(check=lambda _: fake_probe(postgres=False),
                             collect=lambda _: (_ for _ in ()).throw(AssertionError("snapshot")))
    assert report["result"] == "incident"
    assert report["application_snapshot"]["reason"] == "dependencies_unhealthy"


def test_old_active_run_is_not_automatically_alerted(monkeypatch, tmp_path):
    supported_release(monkeypatch, tmp_path)
    report = monitor.monitor(check=lambda _: fake_probe(),
                             collect=lambda _: available(sample_snapshot(running=1, age=999999)))
    assert report["result"] == "healthy" and report["alert"] is None
    assert "999999 s" in monitor.summary(report)


def test_restart_requires_two_failures_and_healthy_dependencies():
    assert monitor.restart_target(fake_probe(api=False), fake_probe(api=False)) == "api"
    assert monitor.restart_target(fake_probe(frontend=False), fake_probe(frontend=False)) == "frontend"
    assert monitor.restart_target(fake_probe(api=False), fake_probe()) is None
    assert monitor.restart_target(fake_probe(api=False, postgres=False), fake_probe(api=False)) is None
    assert monitor.restart_target(fake_probe(api=False, frontend=False), fake_probe(api=False, frontend=False)) == "api"


def test_double_probe_one_restart_and_disk_alert(monkeypatch, tmp_path):
    sha = "a" * 40
    root = tmp_path / "satisfaction-test"
    release = root / "releases" / sha
    release.mkdir(parents=True)
    (release / ".source_sha").write_text(sha)
    (root / "current.sha").write_text(sha)
    monkeypatch.setattr(monitor, "ROOT", root)
    monkeypatch.setattr(monitor.shutil, "disk_usage", lambda _: SimpleNamespace(free=4 * 1024**3))
    probes = iter([fake_probe(api=False), fake_probe(api=False), fake_probe()])
    sleeps, restarts = [], []

    def restart(*args, **kwargs):
        restarts.append((args, kwargs))
        return SimpleNamespace(returncode=0)

    report = monitor.monitor(sleep=sleeps.append, check=lambda _: next(probes), restart=restart)
    assert sleeps == [30]
    assert len(restarts) == 1 and restarts[0][0] == (sha, "restart", "api")
    assert report["remediation"]["attempts"] == 1
    assert report["result"] == "alert" and "Less than 5 GiB free on /" in report["alert"]
    assert "Confirmed application incident recovered after restart" in report["alert"]
    assert len(report["probes"]) == 3
    assert "api: ok" in monitor.summary(report)
    assert json.loads(json.dumps(report))["served_sha"] == sha


def test_no_remediation_for_dependency_incident(monkeypatch, tmp_path):
    sha = "b" * 40
    root = tmp_path / "satisfaction-test"
    release = root / "releases" / sha
    release.mkdir(parents=True)
    (release / ".source_sha").write_text(sha)
    (root / "current.sha").write_text(sha)
    monkeypatch.setattr(monitor, "ROOT", root)
    monkeypatch.setattr(monitor.shutil, "disk_usage", lambda _: SimpleNamespace(free=10 * 1024**3))
    restarts = []
    report = monitor.monitor(sleep=lambda _: None, check=lambda _: fake_probe(api=False, postgres=False),
                             restart=lambda *args, **kwargs: restarts.append(args))
    assert not restarts
    assert report["result"] == "incident"


def test_single_app_failure_is_only_an_alert(monkeypatch, tmp_path):
    sha = "c" * 40
    root = tmp_path / "satisfaction-test"
    release = root / "releases" / sha
    release.mkdir(parents=True)
    (release / ".source_sha").write_text(sha)
    (root / "current.sha").write_text(sha)
    monkeypatch.setattr(monitor, "ROOT", root)
    monkeypatch.setattr(monitor.shutil, "disk_usage", lambda _: SimpleNamespace(free=10 * 1024**3))
    probes = iter([fake_probe(api=False), fake_probe(api=True, frontend=False)])
    report = monitor.monitor(sleep=lambda _: None, check=lambda _: next(probes),
                             restart=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("restart")))
    assert report["result"] == "alert"
    assert report["remediation"] is None


def test_api_incident_recovered_by_one_restart_is_alert(monkeypatch, tmp_path):
    sha = monitor_root(monkeypatch, tmp_path)
    probes = iter([fake_probe(api=False), fake_probe(api=False), fake_probe()])
    restarts, sleeps = [], []

    def restart(*args, **kwargs):
        restarts.append(args)
        return SimpleNamespace(returncode=0)

    report = monitor.monitor(sleep=sleeps.append, check=lambda _: next(probes), restart=restart)
    assert sleeps == [30]
    assert restarts == [(sha, "restart", "api")]
    assert report["result"] == "alert"
    assert report["remediation"] == {"service": "api", "attempts": 1,
                                      "command_succeeded": True, "healthy_after_restart": True}
    assert len(report["probes"]) == 3
    assert [item["healthy"]["api"] for item in report["probes"]] == [False, False, True]
    assert "alert (recovered anomaly" in monitor.summary(report)


def test_frontend_incident_recovered_by_one_restart_is_alert(monkeypatch, tmp_path):
    sha = monitor_root(monkeypatch, tmp_path)
    probes = iter([fake_probe(frontend=False), fake_probe(frontend=False), fake_probe()])
    restarts = []

    def restart(*args, **kwargs):
        restarts.append(args)
        return SimpleNamespace(returncode=0)

    report = monitor.monitor(sleep=lambda _: None, check=lambda _: next(probes), restart=restart)
    assert restarts == [(sha, "restart", "frontend")]
    assert report["result"] == "alert"
    assert len(report["probes"]) == 3
    assert [item["healthy"]["frontend"] for item in report["probes"]] == [False, False, True]


def test_failed_restart_remains_incident_even_if_post_probe_is_healthy(monkeypatch, tmp_path):
    monitor_root(monkeypatch, tmp_path)
    probes = iter([fake_probe(api=False), fake_probe(api=False), fake_probe()])
    report = monitor.monitor(sleep=lambda _: None, check=lambda _: next(probes),
                             restart=lambda *args, **kwargs: SimpleNamespace(returncode=1))
    assert report["result"] == "incident"
    assert report["remediation"]["command_succeeded"] is False
    assert len(report["probes"]) == 3


def test_post_restart_probe_still_failing_is_incident(monkeypatch, tmp_path):
    monitor_root(monkeypatch, tmp_path)
    probes = iter([fake_probe(api=False), fake_probe(api=False), fake_probe(api=False)])
    report = monitor.monitor(sleep=lambda _: None, check=lambda _: next(probes),
                             restart=lambda *args, **kwargs: SimpleNamespace(returncode=0))
    assert report["result"] == "incident"
    assert report["remediation"]["healthy_after_restart"] is False
    assert len(report["probes"]) == 3


def test_entirely_healthy_environment_has_no_remediation(monkeypatch, tmp_path):
    monitor_root(monkeypatch, tmp_path)
    report = monitor.monitor(check=lambda _: fake_probe(),
                             restart=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("restart")))
    assert report["result"] == "healthy"
    assert report["remediation"] is None
    assert len(report["probes"]) == 1
    assert "healthy (no confirmed anomaly)" in monitor.summary(report)


def test_yaml_parses_with_schedule_and_manual_dispatch():
    import yaml
    with (ROOT / ".github/workflows/monitor-test.yml").open(encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    triggers = data.get("on", data.get(True))  # PyYAML 1.1 treats `on` as a bool.
    assert "workflow_dispatch" in triggers and len(triggers["schedule"]) == 1
    assert triggers["schedule"][0]["cron"] == "17 * * * *"
    assert data["jobs"]["monitor"]["if"] == (
        "github.event_name == 'workflow_dispatch' || vars.TEST_MONITOR_SCHEDULE_ENABLED == 'true'"
    )
