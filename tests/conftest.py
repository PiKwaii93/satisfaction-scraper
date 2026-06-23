import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.analysis_runs import router as analysis_runs_router
from app.api.routes.model_training import router as model_training_router


TEST_API_KEY = "test-api-key"


@pytest.fixture(autouse=True)
def configure_test_api_key(monkeypatch):
    monkeypatch.setenv("API_KEY", TEST_API_KEY)


@pytest.fixture
def api_headers():
    return {"X-API-Key": os.environ["API_KEY"]}


@pytest.fixture
def test_app():
    app = FastAPI()
    app.include_router(analysis_runs_router)
    app.include_router(model_training_router)

    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)

