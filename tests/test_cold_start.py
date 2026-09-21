import hashlib
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts import bootstrap_mlflow_model as bootstrap


def test_bootstrap_registers_only_when_production_alias_missing(monkeypatch, tmp_path):
    model_path = tmp_path / "sentiment_model.pkl"
    model_path.write_bytes(b"reviewed-model")
    hash_path = tmp_path / "sentiment_model.sha256"
    hash_path.write_text(hashlib.sha256(model_path.read_bytes()).hexdigest())
    model = Mock()
    monkeypatch.setattr(bootstrap, "load_verified_model", lambda *_: (model, "sha256-test"))
    client = Mock()
    client.get_model_version_by_alias.side_effect = [
        Exception("RESOURCE_DOES_NOT_EXIST: alias not found"),
        SimpleNamespace(version="1"),
    ]
    monkeypatch.setattr(bootstrap.mlflow, "start_run", Mock(return_value=Mock(__enter__=Mock(), __exit__=Mock(return_value=False))))
    monkeypatch.setattr(bootstrap.mlflow, "set_tag", Mock())
    monkeypatch.setattr(bootstrap.mlflow.sklearn, "log_model", Mock(return_value=SimpleNamespace(registered_model_version="1")))
    load = Mock(return_value=model)
    monkeypatch.setattr(bootstrap.mlflow.sklearn, "load_model", load)

    result = bootstrap.bootstrap_model(client, model_path, hash_path)

    assert result.version == "1"
    client.set_registered_model_alias.assert_called_once_with("sentiment_model", "production", "1")
    assert load.call_args_list[0].args == ("models:/sentiment_model/1",)
    assert load.call_args_list[1].args == ("models:/sentiment_model@production",)


def test_bootstrap_keeps_existing_production_without_loading_local_artifact(monkeypatch):
    client = Mock()
    client.get_model_version_by_alias.return_value = SimpleNamespace(version="53")
    load = Mock()
    monkeypatch.setattr(bootstrap.mlflow.sklearn, "load_model", load)
    monkeypatch.setattr(bootstrap, "load_verified_model", Mock(side_effect=AssertionError("must not open pickle")))

    result = bootstrap.bootstrap_model(client, "missing.pkl", "missing.sha256")

    assert result.version == "53"
    client.set_registered_model_alias.assert_not_called()
    load.assert_called_once_with("models:/sentiment_model@production")


def test_bootstrap_rejects_changed_model_before_publication(tmp_path):
    model_path = tmp_path / "sentiment_model.pkl"
    model_path.write_bytes(b"different")
    hash_path = tmp_path / "sentiment_model.sha256"
    hash_path.write_text("0" * 64)
    with pytest.raises(ValueError, match="Empreinte"):
        bootstrap.load_verified_model(model_path, hash_path)


def test_runtime_auth_dependency_imports():
    from app.api.auth import hash_password, verify_password

    password_hash = hash_password("cold-start-password")
    assert verify_password("cold-start-password", password_hash)


def test_health_checks_database(monkeypatch):
    from fastapi import HTTPException
    from app.api import main

    class Cursor:
        def execute(self, query):
            assert query == "SELECT 1 AS healthy;"

        def fetchone(self):
            return {"healthy": 1}

    class Connection:
        def __enter__(self):
            return Cursor()

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(main, "get_cursor", lambda: Connection())
    assert main.health_check() == {"status": "ok", "database": "ok"}

    def unavailable():
        raise OSError("database unreachable")

    monkeypatch.setattr(main, "get_cursor", unavailable)
    with pytest.raises(HTTPException) as exc:
        main.health_check()
    assert exc.value.status_code == 503
