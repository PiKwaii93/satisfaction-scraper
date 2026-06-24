import json

from app.api.auth import AuthenticatedUser
from app.api.auth import require_current_user


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


def test_list_organization_users(authenticated_client, monkeypatch):
    captured = {}

    def fake_list_organization_users(organization_id, include_invitation_links=False):
        captured["organization_id"] = organization_id
        captured["include_invitation_links"] = include_invitation_links
        return [
            {
                "user_id": 1,
                "email": "demo@satisfaction.local",
                "full_name": "Admin Demo",
                "role": "admin",
                "is_active": True,
                "created_at": None,
            }
        ]

    monkeypatch.setattr(
        "app.api.routes.auth.list_organization_users",
        fake_list_organization_users,
    )

    response = authenticated_client.get("/auth/organization/users")

    assert response.status_code == 200
    assert response.json()[0]["email"] == "demo@satisfaction.local"
    assert captured == {"organization_id": 123, "include_invitation_links": True}


def test_get_organization_settings(authenticated_client, monkeypatch):
    captured = {}

    def fake_get_organization_settings(organization_id):
        captured["organization_id"] = organization_id
        return {
            "organization_id": organization_id,
            "name": "Demo Org",
            "slug": "demo-org",
            "default_source": "trustpilot",
            "default_pages_per_star": 3,
            "created_at": None,
            "updated_at": None,
        }

    monkeypatch.setattr(
        "app.api.routes.auth.get_organization_settings",
        fake_get_organization_settings,
    )

    response = authenticated_client.get("/auth/organization/settings")

    assert response.status_code == 200
    assert response.json()["default_pages_per_star"] == 3
    assert captured == {"organization_id": 123}


def test_admin_can_update_organization_settings(authenticated_client, monkeypatch):
    captured = {}

    def fake_update_organization_settings(organization_id, payload):
        captured["organization_id"] = organization_id
        captured["name"] = payload.name
        captured["default_source"] = payload.default_source
        captured["default_pages_per_star"] = payload.default_pages_per_star
        return {
            "organization_id": organization_id,
            "name": payload.name,
            "slug": "demo-org",
            "default_source": payload.default_source,
            "default_pages_per_star": payload.default_pages_per_star,
            "created_at": None,
            "updated_at": None,
        }

    monkeypatch.setattr(
        "app.api.routes.auth.get_organization_settings",
        lambda organization_id: {
            "organization_id": organization_id,
            "name": "Demo Org",
            "slug": "demo-org",
            "default_source": "trustpilot",
            "default_pages_per_star": 1,
            "created_at": None,
            "updated_at": None,
        },
    )
    monkeypatch.setattr(
        "app.api.routes.auth.update_organization_settings",
        fake_update_organization_settings,
    )
    monkeypatch.setattr(
        "app.api.routes.auth.record_audit_event",
        lambda **kwargs: captured.setdefault("audit_event_type", kwargs["event_type"]),
    )

    response = authenticated_client.patch(
        "/auth/organization/settings",
        json={
            "name": "Demo Satisfaction",
            "default_source": "csv",
            "default_pages_per_star": 5,
        },
    )

    assert response.status_code == 200
    assert response.json()["default_source"] == "csv"
    assert captured == {
        "organization_id": 123,
        "name": "Demo Satisfaction",
        "default_source": "csv",
        "default_pages_per_star": 5,
        "audit_event_type": "organization.settings_updated",
    }


def test_member_cannot_update_organization_settings(member_client):
    response = member_client.patch(
        "/auth/organization/settings",
        json={"default_source": "csv"},
    )

    assert response.status_code == 403


def test_admin_can_list_organization_audit_events(authenticated_client, monkeypatch):
    captured = {}

    def fake_list_audit_events(organization_id, limit=30, offset=0):
        captured["organization_id"] = organization_id
        captured["limit"] = limit
        captured["offset"] = offset
        return [
            {
                "audit_event_id": 10,
                "event_type": "analysis.created",
                "actor_email": "demo@satisfaction.local",
                "summary": "Analyse creee.",
                "entity_type": "analysis_run",
                "entity_id": 42,
                "metadata": {"source": "csv"},
                "created_at": None,
            }
        ]

    monkeypatch.setattr(
        "app.api.routes.auth.list_audit_events",
        fake_list_audit_events,
    )

    response = authenticated_client.get("/auth/organization/audit-events?limit=5&offset=2")

    assert response.status_code == 200
    assert response.json()[0]["event_type"] == "analysis.created"
    assert captured == {"organization_id": 123, "limit": 5, "offset": 2}


def test_member_cannot_list_organization_audit_events(member_client):
    response = member_client.get("/auth/organization/audit-events")

    assert response.status_code == 403


def test_admin_can_create_organization_user(authenticated_client, monkeypatch):
    captured = {}

    def fake_create_organization_user(organization_id, payload):
        captured["organization_id"] = organization_id
        captured["email"] = payload.email
        captured["role"] = payload.role
        return {
            "user_id": 2,
            "email": payload.email,
            "full_name": payload.full_name,
            "role": payload.role,
            "is_active": True,
            "created_at": None,
        }

    monkeypatch.setattr(
        "app.api.routes.auth.create_organization_user",
        fake_create_organization_user,
    )

    response = authenticated_client.post(
        "/auth/organization/users",
        json={
            "email": "analyste@satisfaction.local",
            "password": "password-demo",
            "full_name": "Analyste Demo",
            "role": "member",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "analyste@satisfaction.local"
    assert captured == {
        "organization_id": 123,
        "email": "analyste@satisfaction.local",
        "role": "member",
    }


def test_member_cannot_create_organization_user(test_app):
    member_user = AuthenticatedUser(
        user_id=2,
        email="member@satisfaction.local",
        full_name="Member Demo",
        role="member",
        organization_id=123,
        organization_name="Demo Org",
    )
    test_app.dependency_overrides[require_current_user] = lambda: member_user
    try:
        from fastapi.testclient import TestClient

        response = TestClient(test_app).post(
            "/auth/organization/users",
            json={
                "email": "new@satisfaction.local",
                "password": "password-demo",
                "role": "member",
            },
        )
    finally:
        test_app.dependency_overrides.clear()

    assert response.status_code == 403


def test_admin_can_invite_organization_user(authenticated_client, monkeypatch):
    captured = {}

    def fake_invite_organization_user(organization_id, payload):
        captured["organization_id"] = organization_id
        captured["email"] = payload.email
        captured["role"] = payload.role
        return {
            "user_id": 3,
            "email": payload.email,
            "full_name": payload.full_name,
            "role": payload.role,
            "is_active": False,
            "account_status": "pending",
            "created_at": None,
            "invited_at": None,
            "activated_at": None,
            "invitation_expires_at": None,
            "invitation_accept_url": "http://localhost:5173/?invitation_token=abc",
        }

    monkeypatch.setattr(
        "app.api.routes.auth.invite_organization_user",
        fake_invite_organization_user,
    )

    response = authenticated_client.post(
        "/auth/organization/invitations",
        json={
            "email": "invite@satisfaction.local",
            "full_name": "Invite Demo",
            "role": "member",
        },
    )

    assert response.status_code == 201
    assert response.json()["account_status"] == "pending"
    assert response.json()["invitation_accept_url"].endswith("abc")
    assert captured == {
        "organization_id": 123,
        "email": "invite@satisfaction.local",
        "role": "member",
    }


def test_member_cannot_invite_organization_user(test_app):
    member_user = AuthenticatedUser(
        user_id=2,
        email="member@satisfaction.local",
        full_name="Member Demo",
        role="member",
        organization_id=123,
        organization_name="Demo Org",
    )
    test_app.dependency_overrides[require_current_user] = lambda: member_user
    try:
        from fastapi.testclient import TestClient

        response = TestClient(test_app).post(
            "/auth/organization/invitations",
            json={"email": "new@satisfaction.local", "role": "member"},
        )
    finally:
        test_app.dependency_overrides.clear()

    assert response.status_code == 403


def test_accept_invitation_returns_token(client, monkeypatch):
    invited_user = AuthenticatedUser(
        user_id=5,
        email="invite@satisfaction.local",
        full_name="Invite Demo",
        role="member",
        organization_id=123,
        organization_name="Demo Org",
    )

    monkeypatch.setattr(
        "app.api.routes.auth.accept_organization_invitation",
        lambda payload: invited_user,
    )
    monkeypatch.setattr(
        "app.api.routes.auth.create_access_token",
        lambda user_id: f"token-{user_id}",
    )

    response = client.post(
        "/auth/invitations/accept",
        json={
            "token": "invitation-token-demo",
            "password": "password-demo",
            "full_name": "Invite Demo",
        },
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "token-5"
    assert response.json()["user"]["role"] == "member"


def test_list_review_sources_requires_authentication(client):
    response = client.get("/review-sources")

    assert response.status_code == 401


def test_list_review_sources(authenticated_client):
    response = authenticated_client.get("/review-sources")

    assert response.status_code == 200
    payload = response.json()
    active_sources = {
        source["source_id"]
        for source in payload
        if source["status"] == "active" and source["supports_analysis"]
    }
    planned_sources = {
        source["source_id"] for source in payload if source["status"] == "planned"
    }

    assert {"trustpilot", "csv"}.issubset(active_sources)
    assert "google_reviews" in planned_sources
    assert payload[1]["column_aliases"]["verbatim"]


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


def test_member_cannot_create_trustpilot_run(member_client):
    response = member_client.post(
        "/analysis-runs",
        json={
            "company": "https://fr.trustpilot.com/review/www.darty.com",
            "pages_per_star": 1,
            "execute_immediately": False,
        },
    )

    assert response.status_code == 403
    assert "administrateurs" in response.json()["detail"]


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


def test_member_cannot_preview_csv(member_client):
    response = member_client.post(
        "/analysis-runs/preview-csv",
        files={"file": ("reviews.csv", b"avis,note\nOk,5\n", "text/csv")},
    )

    assert response.status_code == 403


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


def test_member_cannot_import_csv(member_client):
    response = member_client.post(
        "/analysis-runs/import-csv",
        data={"company": "Client CSV"},
        files={"file": ("client.csv", b"text,stars\nTres bon,5\n", "text/csv")},
    )

    assert response.status_code == 403


def test_member_cannot_execute_run(member_client):
    response = member_client.post("/analysis-runs/42/execute")

    assert response.status_code == 403


def test_member_cannot_save_review_feedback(member_client):
    response = member_client.post(
        "/analysis-runs/42/reviews/100/feedback",
        json={"corrected_label": "Négatif"},
    )

    assert response.status_code == 403


def test_member_cannot_delete_review_feedback(member_client):
    response = member_client.delete("/analysis-runs/42/reviews/100/feedback")

    assert response.status_code == 403


def test_member_cannot_export_feedback(member_client):
    response = member_client.get("/analysis-runs/42/feedback/export")

    assert response.status_code == 403


def test_member_cannot_start_model_training(member_client):
    response = member_client.post(
        "/model-training/runs",
        json={"feedback_sample_weight": None, "execute_immediately": False},
    )

    assert response.status_code == 403


def test_get_run_trend(authenticated_client, monkeypatch):
    captured = {}

    def fake_get_run_trend(run_id, organization_id):
        captured["run_id"] = run_id
        captured["organization_id"] = organization_id
        return {
            "current_run": sample_run(run_id=12, status="completed"),
            "previous_run": sample_run(run_id=9, status="completed"),
            "has_previous": True,
            "executive_summary": "La part negative baisse.",
            "metrics": [
                {
                    "metric": "average_rating",
                    "label": "Note moyenne",
                    "previous_value": 2.8,
                    "current_value": 3.1,
                    "delta": 0.3,
                    "direction": "up",
                    "unit": "/5",
                }
            ],
            "sentiment": [
                {
                    "label": "Negatif",
                    "previous_count": 60,
                    "current_count": 48,
                    "previous_rate": 50.0,
                    "current_rate": 40.0,
                    "delta_count": -12,
                    "delta_rate": -10.0,
                    "direction": "down",
                }
            ],
            "rising_topics": [],
            "falling_topics": [
                {
                    "topic": "livraison",
                    "previous_count": 20,
                    "current_count": 12,
                    "delta_count": -8,
                    "direction": "down",
                }
            ],
            "new_topics": [],
            "resolved_topics": [],
        }

    monkeypatch.setattr(
        "app.api.routes.analysis_runs.get_run_trend",
        fake_get_run_trend,
    )

    response = authenticated_client.get("/analysis-runs/12/trend")

    assert response.status_code == 200
    assert response.json()["previous_run"]["run_id"] == 9
    assert captured == {"run_id": 12, "organization_id": 123}


def test_get_run_trend_without_previous(authenticated_client, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.analysis_runs.get_run_trend",
        lambda run_id, organization_id: {
            "current_run": sample_run(run_id=12, status="completed"),
            "previous_run": None,
            "has_previous": False,
            "executive_summary": "Aucune analyse precedente.",
            "metrics": [],
            "sentiment": [],
            "rising_topics": [],
            "falling_topics": [],
            "new_topics": [],
            "resolved_topics": [],
        },
    )

    response = authenticated_client.get("/analysis-runs/12/trend")

    assert response.status_code == 200
    assert response.json()["has_previous"] is False


def test_get_run_trend_rejects_unfinished_run(authenticated_client, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.analysis_runs.get_run_trend",
        lambda run_id, organization_id: (_ for _ in ()).throw(
            ValueError("La tendance est disponible uniquement pour une analyse terminee.")
        ),
    )

    response = authenticated_client.get("/analysis-runs/12/trend")

    assert response.status_code == 400
    assert "tendance" in response.json()["detail"]
