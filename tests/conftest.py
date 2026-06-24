import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.auth import AuthenticatedUser, require_current_user
from app.api.routes.analysis_runs import router as analysis_runs_router
from app.api.routes.auth import router as auth_router
from app.api.routes.model_training import router as model_training_router


TEST_USER = AuthenticatedUser(
    user_id=1,
    email="demo@satisfaction.local",
    full_name="Admin Demo",
    role="admin",
    organization_id=123,
    organization_name="Demo Org",
)


@pytest.fixture(autouse=True)
def configure_test_auth(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")


@pytest.fixture
def test_app():
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(analysis_runs_router)
    app.include_router(model_training_router)

    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


@pytest.fixture
def authenticated_client(test_app):
    test_app.dependency_overrides[require_current_user] = lambda: TEST_USER
    try:
        yield TestClient(test_app)
    finally:
        test_app.dependency_overrides.clear()

