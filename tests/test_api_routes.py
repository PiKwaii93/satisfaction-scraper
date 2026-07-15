import json

from app.api.auth import AuthenticatedUser
from app.api.auth import require_current_user
from app.api.services.usage_limits import FeatureNotAvailableError, UsageLimitError


def sample_run(**overrides):
    run = {
        "run_id": 42,
        "company_id": 7,
        "organization_id": 123,
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


def sample_alert(**overrides):
    alert = {
        "alert_id": 9,
        "organization_id": 123,
        "run_id": 42,
        "company_id": 7,
        "company_name": "demo-company.fr",
        "alert_type": "negative_share_high",
        "severity": "warning",
        "title": "Part d'avis negatifs a surveiller",
        "message": "42.0% des avis sont negatifs.",
        "status": "open",
        "metadata": {"negative_rate": 42.0},
        "created_at": None,
        "updated_at": None,
        "acknowledged_at": None,
        "resolved_at": None,
    }
    alert.update(overrides)
    return alert


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


def test_get_organization_usage(authenticated_client, monkeypatch):
    captured = {}

    def fake_get_organization_usage(organization_id):
        captured["organization_id"] = organization_id
        return {
            "plan": "pro",
            "plan_label": "Pro",
            "period_start": None,
            "limits": {
                "monthly_runs": 50,
                "monthly_reviews": 10000,
                "csv_reviews_per_import": 2000,
                "members": 5,
            },
            "usage": {
                "monthly_runs": 2,
                "monthly_reviews": 240,
                "members": 3,
            },
            "features": {"benchmark": True, "model_training": False},
        }

    monkeypatch.setattr(
        "app.api.routes.auth.get_organization_usage",
        fake_get_organization_usage,
    )

    response = authenticated_client.get("/auth/organization/usage")

    assert response.status_code == 200
    assert response.json()["plan"] == "pro"
    assert response.json()["usage"]["members"] == 3
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


def test_admin_cannot_update_organization_plan(authenticated_client):
    response = authenticated_client.patch(
        "/auth/organization/plan",
        json={"plan": "business"},
    )

    assert response.status_code == 403


def test_platform_admin_can_update_organization_plan(platform_client, monkeypatch):
    captured = {}

    monkeypatch.setattr(
        "app.api.routes.platform.get_organization_settings",
        lambda organization_id: {
            "organization_id": organization_id,
            "name": "Demo Org",
            "slug": "demo-org",
            "plan": "free",
            "default_source": "trustpilot",
            "default_pages_per_star": 1,
            "created_at": None,
            "updated_at": None,
        },
    )

    def fake_update_organization_plan(organization_id, plan):
        captured["organization_id"] = organization_id
        captured["plan"] = plan
        return {
            "organization_id": organization_id,
            "name": "Demo Org",
            "slug": "demo-org",
            "plan": plan,
            "default_source": "trustpilot",
            "default_pages_per_star": 1,
            "created_at": None,
            "updated_at": None,
        }

    monkeypatch.setattr(
        "app.api.routes.platform.update_organization_plan",
        fake_update_organization_plan,
    )
    monkeypatch.setattr(
        "app.api.routes.platform.record_audit_event",
        lambda **kwargs: captured.setdefault("audit_event", kwargs),
    )

    response = platform_client.patch(
        "/platform/organizations/123/plan",
        json={"plan": "business"},
    )

    assert response.status_code == 200
    assert response.json()["plan"] == "business"
    assert captured["organization_id"] == 123
    assert captured["plan"] == "business"
    assert captured["audit_event"]["event_type"] == "platform.organization_plan_updated"
    assert captured["audit_event"]["metadata"] == {
        "previous_plan": "free",
        "new_plan": "business",
    }


def test_member_cannot_update_organization_plan(member_client):
    response = member_client.patch(
        "/auth/organization/plan",
        json={"plan": "pro"},
    )

    assert response.status_code == 403


def test_user_can_create_upgrade_request(authenticated_client, monkeypatch):
    captured = {}

    def fake_create_upgrade_request(organization_id, user, payload):
        captured["organization_id"] = organization_id
        captured["user_email"] = user.email
        captured["requested_plan"] = payload.requested_plan
        captured["source"] = payload.source
        return {
            "upgrade_request_id": 7,
            "organization_id": organization_id,
            "requested_plan": payload.requested_plan,
            "current_plan": "free",
            "status": "pending",
            "source": payload.source,
            "note": payload.note,
            "metadata": payload.metadata,
            "requested_by_email": user.email,
            "created_at": None,
            "updated_at": None,
            "handled_at": None,
        }

    monkeypatch.setattr(
        "app.api.routes.auth.create_upgrade_request",
        fake_create_upgrade_request,
    )
    monkeypatch.setattr(
        "app.api.routes.auth.record_audit_event",
        lambda **kwargs: captured.setdefault("audit_event", kwargs),
    )

    response = authenticated_client.post(
        "/auth/organization/upgrade-requests",
        json={
            "requested_plan": "pro",
            "source": "benchmark_gate",
            "note": "Besoin du benchmark",
        },
    )

    assert response.status_code == 201
    assert response.json()["requested_plan"] == "pro"
    assert captured["organization_id"] == 123
    assert captured["user_email"] == "demo@satisfaction.local"
    assert captured["source"] == "benchmark_gate"
    assert captured["audit_event"]["event_type"] == "organization.upgrade_requested"
    assert captured["audit_event"]["entity_type"] == "upgrade_request"


def test_admin_can_list_upgrade_requests(authenticated_client, monkeypatch):
    captured = {}

    def fake_list_upgrade_requests(organization_id, status, limit, offset):
        captured["organization_id"] = organization_id
        captured["status"] = status
        captured["limit"] = limit
        captured["offset"] = offset
        return [
            {
                "upgrade_request_id": 7,
                "organization_id": organization_id,
                "requested_plan": "business",
                "current_plan": "pro",
                "status": "pending",
                "source": "model_training_gate",
                "note": None,
                "metadata": {},
                "requested_by_email": "member@satisfaction.local",
                "created_at": None,
                "updated_at": None,
                "handled_at": None,
            }
        ]

    monkeypatch.setattr(
        "app.api.routes.auth.list_upgrade_requests",
        fake_list_upgrade_requests,
    )

    response = authenticated_client.get(
        "/auth/organization/upgrade-requests?request_status=open&limit=5&offset=2"
    )

    assert response.status_code == 200
    assert response.json()[0]["requested_plan"] == "business"
    assert captured == {
        "organization_id": 123,
        "status": "open",
        "limit": 5,
        "offset": 2,
    }


def test_member_cannot_list_upgrade_requests(member_client):
    response = member_client.get("/auth/organization/upgrade-requests")

    assert response.status_code == 403


def test_platform_admin_can_list_platform_organizations(platform_client, monkeypatch):
    captured = {}

    def fake_list_platform_organizations(limit, offset):
        captured["limit"] = limit
        captured["offset"] = offset
        return [
            {
                "organization_id": 123,
                "name": "Demo Org",
                "slug": "demo-org",
                "plan": "business",
                "active_users": 3,
                "analysis_runs": 12,
                "total_reviews": 1200,
                "open_upgrade_requests": 1,
                "created_at": None,
                "updated_at": None,
            }
        ]

    monkeypatch.setattr(
        "app.api.routes.platform.list_platform_organizations",
        fake_list_platform_organizations,
    )

    response = platform_client.get("/platform/organizations?limit=5&offset=2")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Demo Org"
    assert captured == {"limit": 5, "offset": 2}


def test_admin_cannot_list_platform_organizations(authenticated_client):
    response = authenticated_client.get("/platform/organizations")

    assert response.status_code == 403


def test_platform_admin_can_list_platform_upgrade_requests(platform_client, monkeypatch):
    captured = {}

    def fake_list_platform_upgrade_requests(status, limit, offset):
        captured["status"] = status
        captured["limit"] = limit
        captured["offset"] = offset
        return [
            {
                "upgrade_request_id": 7,
                "organization_id": 123,
                "organization_name": "Demo Org",
                "organization_slug": "demo-org",
                "requested_plan": "pro",
                "current_plan": "free",
                "status": "pending",
                "source": "benchmark_gate",
                "note": None,
                "metadata": {},
                "requested_by_email": "demo@satisfaction.local",
                "created_at": None,
                "updated_at": None,
                "handled_at": None,
            }
        ]

    monkeypatch.setattr(
        "app.api.routes.platform.list_platform_upgrade_requests",
        fake_list_platform_upgrade_requests,
    )

    response = platform_client.get(
        "/platform/upgrade-requests?request_status=open&limit=5&offset=2"
    )

    assert response.status_code == 200
    assert response.json()[0]["organization_name"] == "Demo Org"
    assert captured == {"status": "open", "limit": 5, "offset": 2}


def test_admin_cannot_update_upgrade_request_status(authenticated_client):
    response = authenticated_client.patch(
        "/auth/organization/upgrade-requests/7",
        json={"status": "completed"},
    )

    assert response.status_code == 403


def test_platform_admin_can_update_upgrade_request_status(platform_client, monkeypatch):
    captured = {}

    def fake_update_upgrade_request_status(upgrade_request_id, status):
        captured["upgrade_request_id"] = upgrade_request_id
        captured["status"] = status
        return {
            "upgrade_request_id": upgrade_request_id,
            "organization_id": 123,
            "organization_name": "Demo Org",
            "organization_slug": "demo-org",
            "requested_plan": "pro",
            "current_plan": "free",
            "status": status,
            "source": "benchmark_gate",
            "note": None,
            "metadata": {},
            "requested_by_email": "demo@satisfaction.local",
            "created_at": None,
            "updated_at": None,
            "handled_at": None,
        }

    monkeypatch.setattr(
        "app.api.routes.platform.update_platform_upgrade_request_status",
        fake_update_upgrade_request_status,
    )
    monkeypatch.setattr(
        "app.api.routes.platform.record_audit_event",
        lambda **kwargs: captured.setdefault("audit_event", kwargs),
    )

    response = platform_client.patch(
        "/platform/upgrade-requests/7",
        json={"status": "completed"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert captured["upgrade_request_id"] == 7
    assert captured["audit_event"]["event_type"] == "platform.upgrade_request_updated"


def test_member_cannot_update_upgrade_request_status(member_client):
    response = member_client.patch(
        "/auth/organization/upgrade-requests/7",
        json={"status": "completed"},
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


def test_admin_can_get_organization_action_center(authenticated_client, monkeypatch):
    captured = {}

    def fake_get_action_center(organization_id, role="member", limit=8):
        captured["organization_id"] = organization_id
        captured["role"] = role
        captured["limit"] = limit
        return {
            "counts": {
                "open_alerts": 2,
                "critical_alerts": 1,
                "failed_runs": 1,
                "active_runs": 0,
                "pending_invitations": 1,
                "training_ready_corrections": 5,
                "recent_completed_runs": 3,
            },
            "items": [
                {
                    "item_id": "alert-1",
                    "item_type": "business_alert",
                    "severity": "critical",
                    "title": "Part d'avis negatifs elevee",
                    "message": "55% des avis sont negatifs.",
                    "action_label": "Ouvrir le run",
                    "action_target": {"run_id": 42},
                    "requires_admin": False,
                    "created_at": None,
                }
            ],
        }

    monkeypatch.setattr(
        "app.api.routes.auth.get_action_center",
        fake_get_action_center,
    )

    response = authenticated_client.get("/auth/organization/action-center?limit=5")

    assert response.status_code == 200
    assert response.json()["counts"]["open_alerts"] == 2
    assert response.json()["items"][0]["item_type"] == "business_alert"
    assert captured == {"organization_id": 123, "role": "admin", "limit": 5}


def test_member_can_get_limited_organization_action_center(member_client, monkeypatch):
    captured = {}

    def fake_get_action_center(organization_id, role="member", limit=8):
        captured["organization_id"] = organization_id
        captured["role"] = role
        captured["limit"] = limit
        return {
            "counts": {
                "open_alerts": 0,
                "critical_alerts": 0,
                "failed_runs": 0,
                "active_runs": 1,
                "pending_invitations": 0,
                "training_ready_corrections": 0,
                "recent_completed_runs": 2,
            },
            "items": [],
        }

    monkeypatch.setattr(
        "app.api.routes.auth.get_action_center",
        fake_get_action_center,
    )

    response = member_client.get("/auth/organization/action-center")

    assert response.status_code == 200
    assert response.json()["counts"]["active_runs"] == 1
    assert captured == {"organization_id": 123, "role": "member", "limit": 8}


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
    monkeypatch.setattr("app.api.routes.auth.assert_can_add_member", lambda org_id: None)

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


def test_create_organization_user_respects_member_limit(authenticated_client, monkeypatch):
    def fake_assert_can_add_member(organization_id):
        raise UsageLimitError("Limite du plan atteinte pour les membres: 1/1.")

    monkeypatch.setattr(
        "app.api.routes.auth.assert_can_add_member",
        fake_assert_can_add_member,
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

    assert response.status_code == 403
    assert "Limite du plan atteinte" in response.json()["detail"]


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
    monkeypatch.setattr("app.api.routes.auth.assert_can_add_member", lambda org_id: None)

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


def test_admin_can_update_review_source(authenticated_client, monkeypatch):
    captured = {}

    def fake_update_review_source(organization_id, source_id, payload):
        captured["organization_id"] = organization_id
        captured["source_id"] = source_id
        captured["enabled"] = payload.enabled
        captured["config"] = payload.config
        return {
            "source_id": source_id,
            "label": "Trustpilot",
            "category": "Web public",
            "status": "active",
            "supports_analysis": True,
            "is_configured": True,
            "is_enabled": True,
            "can_configure": True,
            "last_error": None,
            "config": payload.config,
            "updated_at": None,
            "description": "Avis Trustpilot",
            "setup_hint": "Configurer une entreprise par defaut",
            "required_fields": [],
            "optional_fields": [],
            "column_aliases": {},
            "primary_action": "Coller une URL",
        }

    monkeypatch.setattr(
        "app.api.routes.review_sources.update_review_source",
        fake_update_review_source,
    )
    monkeypatch.setattr(
        "app.api.routes.review_sources.record_audit_event",
        lambda **kwargs: captured.setdefault("audit_event", kwargs),
    )

    response = authenticated_client.patch(
        "/review-sources/trustpilot",
        json={
            "enabled": True,
            "config": {
                "default_company": "https://fr.trustpilot.com/review/www.darty.com",
                "pages_per_star": 3,
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert response.json()["config"]["pages_per_star"] == 3
    assert captured["organization_id"] == 123
    assert captured["source_id"] == "trustpilot"
    assert captured["enabled"] is True
    assert captured["config"]["default_company"].endswith("www.darty.com")
    assert captured["audit_event"]["organization_id"] == 123


def test_admin_can_update_csv_review_source_mapping(authenticated_client, monkeypatch):
    captured = {}

    def fake_update_review_source(organization_id, source_id, payload):
        captured["organization_id"] = organization_id
        captured["source_id"] = source_id
        captured["config"] = payload.config
        return {
            "source_id": source_id,
            "label": "CSV",
            "category": "Import fichier",
            "status": "active",
            "supports_analysis": True,
            "is_configured": True,
            "is_enabled": True,
            "can_configure": True,
            "last_error": None,
            "config": payload.config,
            "updated_at": None,
            "description": "Import CSV",
            "setup_hint": "Mapping des colonnes",
            "required_fields": ["verbatim"],
            "optional_fields": ["rating"],
            "column_aliases": {"verbatim": ["avis"]},
            "primary_action": "Importer un fichier CSV",
        }

    monkeypatch.setattr(
        "app.api.routes.review_sources.update_review_source",
        fake_update_review_source,
    )
    monkeypatch.setattr(
        "app.api.routes.review_sources.record_audit_event",
        lambda **kwargs: captured.setdefault("audit_event", kwargs),
    )

    response = authenticated_client.patch(
        "/review-sources/csv",
        json={
            "enabled": True,
            "config": {
                "column_mapping": {
                    "verbatim": "commentaire",
                    "rating": "note",
                    "author": "client",
                }
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["config"]["column_mapping"]["verbatim"] == "commentaire"
    assert captured["organization_id"] == 123
    assert captured["source_id"] == "csv"
    assert captured["config"]["column_mapping"]["rating"] == "note"
    assert captured["audit_event"]["organization_id"] == 123


def test_member_cannot_update_review_source(member_client):
    response = member_client.patch(
        "/review-sources/csv",
        json={"enabled": False},
    )

    assert response.status_code == 403
    assert "administrateurs" in response.json()["detail"]


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
    monkeypatch.setattr(
        "app.api.routes.analysis_runs.is_source_available",
        lambda organization_id, source_id: True,
    )
    monkeypatch.setattr(
        "app.api.routes.analysis_runs.assert_can_create_analysis",
        lambda organization_id, estimated_reviews=None: None,
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


def test_create_trustpilot_run_requires_active_source(authenticated_client, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.analysis_runs.is_source_available",
        lambda organization_id, source_id: False,
    )

    response = authenticated_client.post(
        "/analysis-runs",
        json={
            "company": "https://fr.trustpilot.com/review/www.darty.com",
            "pages_per_star": 1,
            "execute_immediately": False,
        },
    )

    assert response.status_code == 400
    assert "source d'avis n'est pas active" in response.json()["detail"]


def test_compare_runs_uses_organization_scope(authenticated_client, monkeypatch):
    captured = {}

    def fake_get_runs_comparison(run_ids, organization_id):
        captured["run_ids"] = run_ids
        captured["organization_id"] = organization_id
        return {
            "run_ids": run_ids,
            "companies": [],
            "highlights": {
                "best_health": None,
                "highest_negative_rate": None,
                "most_reviews": None,
                "shared_priority": None,
            },
            "common_topics": [],
        }

    monkeypatch.setattr(
        "app.api.routes.analysis_runs.assert_feature_enabled",
        lambda organization_id, feature: None,
    )
    monkeypatch.setattr(
        "app.api.routes.analysis_runs.get_runs_comparison",
        fake_get_runs_comparison,
    )

    response = authenticated_client.get("/analysis-runs/compare?run_ids=1,2")

    assert response.status_code == 200
    assert captured == {"run_ids": [1, 2], "organization_id": 123}


def test_compare_runs_requires_plan_feature(authenticated_client, monkeypatch):
    def fake_assert_feature_enabled(organization_id, feature):
        assert feature == "benchmark"
        raise FeatureNotAvailableError("Fonctionnalite indisponible avec le plan Free.")

    monkeypatch.setattr(
        "app.api.routes.analysis_runs.assert_feature_enabled",
        fake_assert_feature_enabled,
    )

    response = authenticated_client.get("/analysis-runs/compare?run_ids=1,2")

    assert response.status_code == 403
    assert "plan Free" in response.json()["detail"]


def test_create_trustpilot_run_respects_usage_limits(authenticated_client, monkeypatch):
    def fake_assert_can_create_analysis(organization_id, estimated_reviews=None):
        assert organization_id == 123
        assert estimated_reviews == 120
        raise UsageLimitError(
            "Limite du plan atteinte pour les analyses mensuelles: 3/3."
        )

    monkeypatch.setattr(
        "app.api.routes.analysis_runs.assert_can_create_analysis",
        fake_assert_can_create_analysis,
    )
    monkeypatch.setattr(
        "app.api.routes.analysis_runs.is_source_available",
        lambda organization_id, source_id: True,
    )

    response = authenticated_client.post(
        "/analysis-runs",
        json={
            "company": "https://fr.trustpilot.com/review/www.darty.com",
            "pages_per_star": 1,
            "execute_immediately": False,
        },
    )

    assert response.status_code == 403
    assert "analyses mensuelles" in response.json()["detail"]


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


def test_preview_csv_endpoint_uses_saved_mapping_profile(authenticated_client, monkeypatch):
    csv_content = (
        "stars_count;customer_review\n"
        "5;Produit conforme et livraison rapide\n"
        "1;Service client impossible a joindre\n"
    ).encode("utf-8")

    monkeypatch.setattr(
        "app.api.routes.analysis_runs.get_csv_column_mapping_profile",
        lambda organization_id: {
            "rating": "stars_count",
            "verbatim": "customer_review",
        },
    )

    response = authenticated_client.post(
        "/analysis-runs/preview-csv",
        files={"file": ("reviews.csv", csv_content, "text/csv")},
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
    monkeypatch.setattr(
        "app.api.routes.analysis_runs.is_source_available",
        lambda organization_id, source_id: True,
    )
    monkeypatch.setattr(
        "app.api.routes.analysis_runs.assert_can_import_csv",
        lambda organization_id, review_count: None,
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


def test_import_csv_respects_usage_limits(authenticated_client, monkeypatch):
    def fake_assert_can_import_csv(organization_id, review_count):
        assert organization_id == 123
        assert review_count == 2
        raise UsageLimitError(
            "Limite du plan atteinte pour les avis par import CSV: 0/1."
        )

    monkeypatch.setattr(
        "app.api.routes.analysis_runs.assert_can_import_csv",
        fake_assert_can_import_csv,
    )

    response = authenticated_client.post(
        "/analysis-runs/import-csv",
        data={"company": "Client CSV"},
        files={
            "file": (
                "client.csv",
                b"avis,note\nTres bon,5\nTres mauvais,1\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 403
    assert "avis par import CSV" in response.json()["detail"]


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


def test_model_training_requires_plan_feature(authenticated_client, monkeypatch):
    def fake_assert_feature_enabled(organization_id, feature):
        assert feature == "model_training"
        raise FeatureNotAvailableError("Fonctionnalite indisponible avec le plan Pro.")

    monkeypatch.setattr(
        "app.api.routes.model_training.assert_feature_enabled",
        fake_assert_feature_enabled,
    )

    response = authenticated_client.post(
        "/model-training/runs",
        json={"feedback_sample_weight": None, "execute_immediately": False},
    )

    assert response.status_code == 403
    assert "plan Pro" in response.json()["detail"]


def test_list_business_alerts(authenticated_client, monkeypatch):
    captured = {}

    def fake_list_business_alerts(organization_id, status, limit, offset):
        captured["organization_id"] = organization_id
        captured["status"] = status
        captured["limit"] = limit
        captured["offset"] = offset
        return [sample_alert()]

    monkeypatch.setattr(
        "app.api.routes.analysis_runs.list_business_alerts",
        fake_list_business_alerts,
    )

    response = authenticated_client.get("/analysis-runs/alerts?status=open&limit=5")

    assert response.status_code == 200
    assert response.json()[0]["alert_type"] == "negative_share_high"
    assert captured == {
        "organization_id": 123,
        "status": "open",
        "limit": 5,
        "offset": 0,
    }


def test_member_can_list_business_alerts(member_client, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.analysis_runs.list_business_alerts",
        lambda organization_id, status, limit, offset: [sample_alert()],
    )

    response = member_client.get("/analysis-runs/alerts")

    assert response.status_code == 200
    assert response.json()[0]["status"] == "open"


def test_admin_can_update_business_alert_status(authenticated_client, monkeypatch):
    captured = {}

    def fake_update_business_alert_status(alert_id, organization_id, status):
        captured["alert_id"] = alert_id
        captured["organization_id"] = organization_id
        captured["status"] = status
        return sample_alert(alert_id=alert_id, status=status)

    monkeypatch.setattr(
        "app.api.routes.analysis_runs.update_business_alert_status",
        fake_update_business_alert_status,
    )
    monkeypatch.setattr(
        "app.api.routes.analysis_runs.record_audit_event",
        lambda **kwargs: captured.setdefault("audit_event_type", kwargs["event_type"]),
    )

    response = authenticated_client.patch(
        "/analysis-runs/alerts/9",
        json={"status": "acknowledged"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "acknowledged"
    assert captured == {
        "alert_id": 9,
        "organization_id": 123,
        "status": "acknowledged",
        "audit_event_type": "business_alert.status_updated",
    }


def test_member_cannot_update_business_alert_status(member_client):
    response = member_client.patch(
        "/analysis-runs/alerts/9",
        json={"status": "resolved"},
    )

    assert response.status_code == 403


def test_admin_can_refresh_run_business_alerts(authenticated_client, monkeypatch):
    captured = {}

    def fake_upsert_business_alerts_for_run(run_id, organization_id):
        captured["run_id"] = run_id
        captured["organization_id"] = organization_id
        return [sample_alert(run_id=run_id)]

    monkeypatch.setattr(
        "app.api.routes.analysis_runs.get_analysis_run",
        lambda run_id, organization_id: sample_run(run_id=run_id, status="completed"),
    )
    monkeypatch.setattr(
        "app.api.routes.analysis_runs.upsert_business_alerts_for_run",
        fake_upsert_business_alerts_for_run,
    )
    monkeypatch.setattr(
        "app.api.routes.analysis_runs.record_audit_event",
        lambda **kwargs: captured.setdefault("audit_event_type", kwargs["event_type"]),
    )

    response = authenticated_client.post("/analysis-runs/42/alerts/refresh")

    assert response.status_code == 200
    assert response.json()[0]["run_id"] == 42
    assert captured == {
        "run_id": 42,
        "organization_id": 123,
        "audit_event_type": "business_alert.generated",
    }


def test_member_cannot_refresh_run_business_alerts(member_client):
    response = member_client.post("/analysis-runs/42/alerts/refresh")

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
