from datetime import datetime

import pytest

from app.api.services import customer_action_service as service


class FakeCursor:
    def __init__(self, action_organization_id=123):
        self.action_organization_id = action_organization_id
        self.executed = []
        self.row = None
        self.rows = []

    def execute(self, query, params):
        self.executed.append((query, params))
        if "FROM customer_actions ca" in query:
            organization_id, action_id = params
            self.rows = []
            self.row = (
                {
                    "action_id": action_id,
                    "organization_id": organization_id,
                    "alert_id": None,
                    "run_id": None,
                    "company_name": None,
                    "alert_title": None,
                    "alert_type": None,
                    "alert_metadata": None,
                    "impact_run_id": None,
                    "impact_company_id": None,
                    "title": "Traiter les avis negatifs",
                    "description": None,
                    "priority": "high",
                    "status": "open",
                    "owner_name": None,
                    "due_date": None,
                    "notes": None,
                    "created_by_email": "admin@example.test",
                    "updated_by_email": None,
                    "created_at": datetime(2026, 8, 27, 7, 0),
                    "updated_at": datetime(2026, 8, 27, 7, 0),
                    "resolved_at": None,
                }
                if organization_id == self.action_organization_id and action_id == 4
                else None
            )
        elif "FROM audit_events" in query:
            self.row = None
            audit_rows = [
                {
                    "audit_event_id": 10,
                    "organization_id": 123,
                    "actor_email": "admin@example.test",
                    "event_type": "customer_action.created",
                    "entity_id": 4,
                    "summary": "Action client creee.",
                    "metadata": {"status": "open"},
                    "created_at": datetime(2026, 8, 27, 8, 0),
                },
                {
                    "audit_event_id": 12,
                    "organization_id": 123,
                    "actor_email": "member@example.test",
                    "event_type": "customer_action.comment_created",
                    "entity_id": 4,
                    "summary": "Commentaire ajoute a une action client.",
                    "metadata": {"comment_id": 3},
                    "created_at": datetime(2026, 8, 27, 9, 0),
                },
                {
                    "audit_event_id": 11,
                    "organization_id": 123,
                    "actor_email": "admin@example.test",
                    "event_type": "customer_action.updated",
                    "entity_id": 4,
                    "summary": "Action client mise a jour.",
                    "metadata": {"status": "resolved"},
                    "created_at": datetime(2026, 8, 27, 10, 0),
                },
            ]
            if "event_type <> 'customer_action.comment_created'" in query:
                audit_rows = [
                    row
                    for row in audit_rows
                    if row["event_type"] != "customer_action.comment_created"
                ]
            self.rows = audit_rows
        elif "FROM customer_action_comments" in query:
            self.row = None
            self.rows = [
                {
                    "comment_id": 3,
                    "action_id": 4,
                    "organization_id": 123,
                    "author_user_id": 2,
                    "author_name": "Member Demo",
                    "author_email": "member@example.test",
                    "body": "Client relance.",
                    "created_at": datetime(2026, 8, 27, 9, 0),
                }
            ]
        else:
            self.row = None
            self.rows = []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class FakeCursorContext:
    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return self.cursor

    def __exit__(self, exc_type, exc, tb):
        return False


def test_list_customer_action_timeline_merges_audit_events_and_comments(monkeypatch):
    cursor = FakeCursor()

    monkeypatch.setattr(service, "_build_action_impact", lambda cursor, org, row: None)
    monkeypatch.setattr(service, "get_cursor", lambda: FakeCursorContext(cursor))

    items = service.list_customer_action_timeline(4, 123, limit=10)

    assert [item["item_id"] for item in items] == [
        "audit-10",
        "comment-3",
        "audit-11",
    ]
    assert items[1]["body"] == "Client relance."
    assert "audit-12" not in [item["item_id"] for item in items]
    assert cursor.executed[0][1] == (123, 4)
    assert cursor.executed[1][1] == (123, 4, 10)
    assert cursor.executed[2][1] == (123, 4, 10)


def test_list_customer_action_timeline_requires_action_in_organization(monkeypatch):
    cursor = FakeCursor()

    monkeypatch.setattr(service, "_build_action_impact", lambda cursor, org, row: None)
    monkeypatch.setattr(service, "get_cursor", lambda: FakeCursorContext(cursor))

    with pytest.raises(ValueError, match="Action client introuvable"):
        service.list_customer_action_timeline(4, 999)

    assert len(cursor.executed) == 1
    assert cursor.executed[0][1] == (999, 4)
