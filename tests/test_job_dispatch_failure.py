from contextlib import contextmanager
import asyncio
from io import BytesIO
from unittest.mock import Mock

from fastapi import HTTPException, UploadFile
from kombu.exceptions import OperationalError

from app.api.services import analysis_service
from tests.conftest import TEST_USER


def test_broker_failure_marks_run_failed_and_hides_broker_detail(monkeypatch):
    cursor = Mock()

    @contextmanager
    def fake_cursor(commit=False):
        assert commit
        yield cursor

    events = []
    monkeypatch.setattr(analysis_service, "get_cursor", fake_cursor)
    monkeypatch.setattr(analysis_service, "reset_run_events", lambda run_id: None)
    monkeypatch.setattr(analysis_service, "record_run_event",
                        lambda run_id, message, **kw: events.append((message, kw)))
    monkeypatch.setattr("app.api.services.job_queue.enqueue_analysis_run",
                        lambda *args, **kwargs: (_ for _ in ()).throw(
                            OperationalError("redis://user:secret@broker unavailable")))

    try:
        analysis_service.queue_analysis_run(42)
    except analysis_service.JobDispatchError as exc:
        assert str(exc) == "Service de traitement temporairement indisponible."
    else:
        raise AssertionError("Dispatch failure was not propagated")

    assert any("status = 'failed'" in call.args[0] for call in cursor.execute.call_args_list)
    assert all("secret" not in message for message, _ in events)


def test_csv_route_returns_safe_503_when_dispatch_fails(monkeypatch):
    from app.api.routes import analysis_runs

    monkeypatch.setattr(analysis_runs, "is_source_available", lambda *args: True)
    monkeypatch.setattr(analysis_runs, "get_csv_column_mapping_profile", lambda *args: {})
    monkeypatch.setattr(analysis_runs, "assert_can_import_csv", lambda *args: None)
    monkeypatch.setattr(analysis_runs, "build_csv_import_preview",
                        lambda *args, **kwargs: {"review_count": 1})
    monkeypatch.setattr(analysis_runs, "create_csv_analysis_run",
                        lambda **kwargs: (_ for _ in ()).throw(
                            analysis_service.JobDispatchError(
                                "Service de traitement temporairement indisponible.")))
    file = UploadFile(filename="reviews.csv", file=BytesIO(b"avis,note\nBon service,5\n"))
    try:
        asyncio.run(analysis_runs.import_csv_run(
            company="Entreprise fictive", file=file,
            column_mapping=None, current_user=TEST_USER))
    except HTTPException as exc:
        assert exc.status_code == 503
        assert exc.detail == "Service de traitement temporairement indisponible."
    else:
        raise AssertionError("The route accepted a failed dispatch")
