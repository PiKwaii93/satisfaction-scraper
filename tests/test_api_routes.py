import json

from app.api.auth import AuthenticatedUser


def sample_run(**overrides):
    run = {
        "run_id": 42,
        "company_id": 7,
        "company_name": "demo-company.fr",
        "trustpilot_slug": "demo-company.fr",
        "source": "trustpilot",
        "status": "pending",
        "pages_per_star": 1,
        "stars_requested": [1, 2, 3, 4, 5],
        "total_reviews": 0,
        "celery_task_id": None,
        "created_at": None,
        "started_at": None,
        "finished_at": None,
        "execution_duration_seconds": None,
        "error_message": None,
    }
    run.update(overrides)
    return run


def test_health_is_public(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_returns_token(client, monkeypatch):
    demo_user = AuthenticatedUser(
        user_id=1,
        email="demo@satisfaction.local",
        full_name="Admin Demo",
        role="admin",
        organization_id=123,
        organization_name="Demo Org",
    )
    monkeypatch.setattr(
        "app.api.routes.auth.authenticate_user",
        lambda email, password: demo_user,
    )
    monkeypatch.setattr(
        "app.api.routes.auth.create_access_token",
        lambda user_id: f"token-{user_id}",
    )

    response = client.post(
        "/auth/login",
        json={"email": "demo@satisfaction.local", "password": "demo-password"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"] == "token-1"
    assert payload["user"]["organization"]["organization_id"] == 123


def test_login_rejects_invalid_credentials(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.auth.authenticate_user",
        lambda email, password: None,
    )

    response = client.post(
        "/auth/login",
        json={"email": "demo@satisfaction.local", "password": "wrong"},
    )

    assert response.status_code == 401


def test_protected_endpoint_requires_authentication(client):
    response = client.get("/analysis-runs")

    assert response.status_code == 401
    assert "Authentification" in response.json()["detail"]


def test_protected_endpoint_rejects_invalid_token(client):
    response = client.get(
        "/analysis-runs",
        headers={"Authorization": "Bearer wrong"},
    )

    assert response.status_code == 403
    assert "invalide" in response.json()["detail"]


def test_list_runs_with_authenticated_user(authenticated_client, monkeypatch):
    captured = {}

    def fake_list_analysis_runs(organization_id, limit, offset):
        captured["organization_id"] = organization_id
        return [sample_run()]

    monkeypatch.setattr(
        "app.api.routes.analysis_runs.list_analysis_runs",
        fake_list_analysis_runs,
    )

    response = authenticated_client.get("/analysis-runs")

    assert response.status_code == 200
    assert response.json()[0]["run_id"] == 42
    assert captured["organization_id"] == 123


def test_create_trustpilot_run_uses_service(authenticated_client, monkeypatch):
    captured_payload = {}

    def fake_create_analysis_run(payload, organization_id):
        captured_payload["company"] = payload.company
        captured_payload["execute_immediately"] = payload.execute_immediately
        captured_payload["organization_id"] = organization_id
        return sample_run(company_name="darty.com", trustpilot_slug="www.darty.com")

    monkeypatch.setattr(
        "app.api.routes.analysis_runs.create_analysis_run",
        fake_create_analysis_run,
    )

    response = authenticated_client.post(
        "/analysis-runs",
        json={
            "company": "https://fr.trustpilot.com/review/www.darty.com",
            "pages_per_star": 1,
            "execute_immediately": False,
        },
    )

    assert response.status_code == 201
    assert response.json()["company_name"] == "darty.com"
    assert captured_payload == {
        "company": "https://fr.trustpilot.com/review/www.darty.com",
        "execute_immediately": False,
        "organization_id": 123,
    }


def test_preview_csv_endpoint_accepts_column_mapping(authenticated_client):
    csv_content = (
        "stars_count;customer_review;client_name\n"
        "5;Produit conforme et livraison rapide;Alice\n"
        "1;Service client impossible a joindre;Bob\n"
    ).encode("utf-8")
    mapping = {
        "rating": "stars_count",
        "verbatim": "customer_review",
        "author": "client_name",
    }

    response = authenticated_client.post(
        "/analysis-runs/preview-csv",
        files={"file": ("reviews.csv", csv_content, "text/csv")},
        data={"column_mapping": json.dumps(mapping)},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["review_count"] == 2
    assert payload["detected_columns"]["verbatim"] == "customer_review"
    assert payload["preview_reviews"][0]["rating"] == 5


def test_preview_csv_endpoint_rejects_invalid_mapping_json(authenticated_client):
    response = authenticated_client.post(
        "/analysis-runs/preview-csv",
        files={"file": ("reviews.csv", b"avis,note\nOk,5\n", "text/csv")},
        data={"column_mapping": "{not-json"},
    )

    assert response.status_code == 400
    assert "Mapping CSV invalide" in response.json()["detail"]


def test_import_csv_passes_mapping_to_service(authenticated_client, monkeypatch):
    captured = {}

    def fake_create_csv_analysis_run(
        company_input,
        file_bytes,
        organization_id,
        original_filename=None,
        column_mapping=None,
    ):
        captured["company_input"] = company_input
        captured["organization_id"] = organization_id
        captured["original_filename"] = original_filename
        captured["column_mapping"] = column_mapping
        captured["file_bytes"] = file_bytes
        return sample_run(
            run_id=77,
            source="csv",
            company_name="Client CSV",
            trustpilot_slug="client-csv",
            stars_requested=[],
            total_reviews=2,
            status="completed",
        )

    monkeypatch.setattr(
        "app.api.routes.analysis_runs.create_csv_analysis_run",
        fake_create_csv_analysis_run,
    )

    mapping = {"verbatim": "text", "rating": "stars"}
    response = authenticated_client.post(
        "/analysis-runs/import-csv",
        data={
            "company": "Client CSV",
            "column_mapping": json.dumps(mapping),
        },
        files={"file": ("client.csv", b"text,stars\nTres bon,5\n", "text/csv")},
    )

    assert response.status_code == 201
    assert response.json()["run_id"] == 77
    assert captured["company_input"] == "Client CSV"
    assert captured["organization_id"] == 123
    assert captured["original_filename"] == "client.csv"
    assert captured["column_mapping"] == mapping
    assert captured["file_bytes"] == b"text,stars\nTres bon,5\n"

