from psycopg2.extras import Json

from app.api.database import get_cursor


def serialize_organization_settings(row):
    return {
        "organization_id": int(row["organization_id"]),
        "name": row["name"],
        "slug": row["slug"],
        "plan": row.get("plan") or "business",
        "default_source": row.get("default_source") or "trustpilot",
        "default_pages_per_star": int(row.get("default_pages_per_star") or 1),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def get_organization_settings(organization_id: int):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                organization_id,
                name,
                slug,
                plan,
                default_source,
                default_pages_per_star,
                created_at,
                updated_at
            FROM organizations
            WHERE organization_id = %s;
            """,
            (organization_id,),
        )
        row = cursor.fetchone()
        return serialize_organization_settings(row) if row else None


def update_organization_settings(organization_id: int, payload):
    name = payload.name.strip() if payload.name is not None else None

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            """
            UPDATE organizations
            SET name = COALESCE(%s, name),
                default_source = COALESCE(%s, default_source),
                default_pages_per_star = COALESCE(%s, default_pages_per_star),
                updated_at = NOW()
            WHERE organization_id = %s
            RETURNING
                organization_id,
                name,
                slug,
                plan,
                default_source,
                default_pages_per_star,
                created_at,
                updated_at;
            """,
            (
                name,
                payload.default_source,
                payload.default_pages_per_star,
                organization_id,
            ),
        )
        row = cursor.fetchone()
        return serialize_organization_settings(row) if row else None


def serialize_audit_event(row):
    return {
        "audit_event_id": int(row["audit_event_id"]),
        "event_type": row["event_type"],
        "actor_email": row.get("actor_email"),
        "summary": row["summary"],
        "entity_type": row.get("entity_type"),
        "entity_id": row.get("entity_id"),
        "metadata": row.get("metadata") or {},
        "created_at": row.get("created_at"),
    }


def record_audit_event(
    *,
    organization_id: int,
    actor_user=None,
    event_type: str,
    summary: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    metadata: dict | None = None,
):
    try:
        with get_cursor(commit=True) as cursor:
            cursor.execute(
                """
                INSERT INTO audit_events (
                    organization_id,
                    user_id,
                    actor_email,
                    event_type,
                    entity_type,
                    entity_id,
                    summary,
                    metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING
                    audit_event_id,
                    event_type,
                    actor_email,
                    summary,
                    entity_type,
                    entity_id,
                    metadata,
                    created_at;
                """,
                (
                    organization_id,
                    getattr(actor_user, "user_id", None),
                    getattr(actor_user, "email", None),
                    event_type,
                    entity_type,
                    entity_id,
                    summary,
                    Json(metadata or {}),
                ),
            )
            return serialize_audit_event(cursor.fetchone())
    except Exception:
        # Audit logging is useful but should not make the business action fail.
        return None


def list_audit_events(organization_id: int, limit=30, offset=0):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                audit_event_id,
                event_type,
                actor_email,
                summary,
                entity_type,
                entity_id,
                metadata,
                created_at
            FROM audit_events
            WHERE organization_id = %s
            ORDER BY audit_event_id DESC
            LIMIT %s OFFSET %s;
            """,
            (organization_id, limit, offset),
        )
        return [serialize_audit_event(row) for row in cursor.fetchall()]
