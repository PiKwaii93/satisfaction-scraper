from psycopg2.extras import Json

from app.api.database import get_cursor
from app.api.services.usage_limits import normalize_plan


OPEN_UPGRADE_STATUSES = {"pending", "approved"}


def serialize_upgrade_request(row):
    return {
        "upgrade_request_id": int(row["upgrade_request_id"]),
        "organization_id": int(row["organization_id"]),
        "organization_name": row.get("organization_name"),
        "organization_slug": row.get("organization_slug"),
        "requested_plan": row["requested_plan"],
        "current_plan": row["current_plan"],
        "status": row["status"],
        "source": row.get("source"),
        "note": row.get("note"),
        "metadata": row.get("metadata") or {},
        "requested_by_email": row.get("requested_by_email"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "handled_at": row.get("handled_at"),
    }


def create_upgrade_request(organization_id: int, user, payload):
    requested_plan = normalize_plan(payload.requested_plan)

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            """
            SELECT plan
            FROM organizations
            WHERE organization_id = %s;
            """,
            (organization_id,),
        )
        organization = cursor.fetchone()
        current_plan = normalize_plan(organization["plan"] if organization else None)

        if requested_plan == current_plan:
            raise ValueError("Ce plan est deja actif pour l'organisation.")

        cursor.execute(
            """
            SELECT *
            FROM upgrade_requests
            WHERE organization_id = %s
              AND requested_plan = %s
              AND status IN ('pending', 'approved')
            ORDER BY upgrade_request_id DESC
            LIMIT 1;
            """,
            (organization_id, requested_plan),
        )
        existing = cursor.fetchone()
        if existing:
            return serialize_upgrade_request(existing)

        cursor.execute(
            """
            INSERT INTO upgrade_requests (
                organization_id,
                requested_by_user_id,
                requested_by_email,
                current_plan,
                requested_plan,
                source,
                note,
                metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *;
            """,
            (
                organization_id,
                user.user_id,
                user.email,
                current_plan,
                requested_plan,
                payload.source,
                payload.note,
                Json(payload.metadata or {}),
            ),
        )
        return serialize_upgrade_request(cursor.fetchone())


def list_upgrade_requests(organization_id: int, status: str = "open", limit=20, offset=0):
    filters = ["organization_id = %s"]
    params = [organization_id]

    if status == "open":
        filters.append("status IN ('pending', 'approved')")
    elif status != "all":
        filters.append("status = %s")
        params.append(status)

    params.extend([limit, offset])
    with get_cursor() as cursor:
        cursor.execute(
            f"""
            SELECT *
            FROM upgrade_requests
            WHERE {' AND '.join(filters)}
            ORDER BY upgrade_request_id DESC
            LIMIT %s OFFSET %s;
            """,
            tuple(params),
        )
        return [serialize_upgrade_request(row) for row in cursor.fetchall()]


def update_upgrade_request_status(
    organization_id: int,
    upgrade_request_id: int,
    status: str,
):
    with get_cursor(commit=True) as cursor:
        cursor.execute(
            """
            UPDATE upgrade_requests
            SET status = %s,
                handled_at = CASE
                    WHEN %s IN ('approved', 'rejected', 'completed', 'cancelled')
                    THEN NOW()
                    ELSE handled_at
                END,
                updated_at = NOW()
            WHERE organization_id = %s
              AND upgrade_request_id = %s
            RETURNING *;
            """,
            (status, status, organization_id, upgrade_request_id),
        )
        row = cursor.fetchone()
        return serialize_upgrade_request(row) if row else None


def list_platform_upgrade_requests(status: str = "open", limit=50, offset=0):
    filters = []
    params = []

    if status == "open":
        filters.append("ur.status IN ('pending', 'approved')")
    elif status != "all":
        filters.append("ur.status = %s")
        params.append(status)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    params.extend([limit, offset])

    with get_cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                ur.*,
                o.name AS organization_name,
                o.slug AS organization_slug
            FROM upgrade_requests ur
            JOIN organizations o ON o.organization_id = ur.organization_id
            {where_clause}
            ORDER BY ur.upgrade_request_id DESC
            LIMIT %s OFFSET %s;
            """,
            tuple(params),
        )
        return [serialize_upgrade_request(row) for row in cursor.fetchall()]


def update_platform_upgrade_request_status(upgrade_request_id: int, status: str):
    with get_cursor(commit=True) as cursor:
        cursor.execute(
            """
            UPDATE upgrade_requests
            SET status = %s,
                handled_at = CASE
                    WHEN %s IN ('approved', 'rejected', 'completed', 'cancelled')
                    THEN NOW()
                    ELSE handled_at
                END,
                updated_at = NOW()
            WHERE upgrade_request_id = %s
            RETURNING *;
            """,
            (status, status, upgrade_request_id),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        if status == "approved":
            requested_plan = normalize_plan(row["requested_plan"])
            cursor.execute(
                """
                UPDATE organizations
                SET plan = %s,
                    plan_updated_at = NOW(),
                    updated_at = NOW()
                WHERE organization_id = %s;
                """,
                (requested_plan, row["organization_id"]),
            )
            row["current_plan"] = requested_plan

        cursor.execute(
            """
            SELECT
                ur.*,
                o.name AS organization_name,
                o.slug AS organization_slug
            FROM upgrade_requests ur
            JOIN organizations o ON o.organization_id = ur.organization_id
            WHERE ur.upgrade_request_id = %s;
            """,
            (upgrade_request_id,),
        )
        return serialize_upgrade_request(cursor.fetchone())
