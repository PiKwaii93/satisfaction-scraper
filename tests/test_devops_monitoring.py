"""Offline checks for the test-VM DevOps evidence and bounded remediation."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


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
