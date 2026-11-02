from contextlib import contextmanager
from unittest.mock import Mock

import pytest

from app.api.services import analysis_service


def test_manual_requeue_rejects_active_run_without_reset_or_dispatch(monkeypatch):
    cursor = Mock(rowcount=0)
    reset = Mock()
    enqueue = Mock()

    @contextmanager
    def fake_cursor(commit=False):
        assert commit
        yield cursor

    monkeypatch.setattr(analysis_service, "get_cursor", fake_cursor)
    monkeypatch.setattr(analysis_service, "reset_run_events", reset)
    monkeypatch.setattr("app.api.services.job_queue.enqueue_analysis_run", enqueue)

    with pytest.raises(analysis_service.ActiveAnalysisRunError, match="deja en attente"):
        analysis_service.queue_analysis_run(42, reject_active=True)

    sql = cursor.execute.call_args.args[0]
    assert "status NOT IN ('pending', 'running')" in sql
    assert cursor.execute.call_args.args[1] == ("analysis-run-42", 42, True)
    reset.assert_not_called()
    enqueue.assert_not_called()


def test_scraper_error_is_safe_in_run_and_event_but_propagates_to_worker(
    monkeypatch, tmp_path
):
    cursor = Mock(rowcount=1)
    events = []
    run = {
        "run_id": 42, "source": "trustpilot", "trustpilot_slug": "test.example",
        "stars_requested": [1], "collection_mode": "sampled",
        "pages_per_star": 1, "max_pages": None, "domain": None,
    }

    @contextmanager
    def fake_cursor(commit=False):
        yield cursor

    monkeypatch.setattr(analysis_service, "get_analysis_run", lambda run_id: run)
    monkeypatch.setattr(analysis_service, "get_cursor", fake_cursor)
    monkeypatch.setattr(analysis_service, "record_run_event",
                        lambda run_id, message, **kwargs: events.append((message, kwargs)))
    monkeypatch.setattr(analysis_service, "default_paths",
                        lambda slug, run_id: (tmp_path / "reviews.json", tmp_path / "predictions.csv"))
    monkeypatch.setattr(analysis_service, "scrape_trustpilot",
                        lambda **kwargs: (_ for _ in ()).throw(
                            RuntimeError("credential=private /app/internal/path")))

    with pytest.raises(RuntimeError, match="credential=private"):
        analysis_service.execute_analysis_run(42)

    failure_updates = [call for call in cursor.execute.call_args_list
                       if "SET status = 'failed'" in call.args[0]]
    assert len(failure_updates) == 1
    public_message = failure_updates[0].args[1][0]
    assert "Trustpilot" in public_message
    assert "credential" not in public_message and "/app/" not in public_message
    assert any(kwargs.get("step") == "failed" for _, kwargs in events)
    assert all("credential" not in message and "/app/" not in message
               for message, _ in events)
