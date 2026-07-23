from app.api.database import get_cursor
from app.api.schemas import (
    CustomerActionCommentCreate,
    CustomerActionCreate,
    CustomerActionUpdate,
)


ACTION_STATUSES = {"open", "in_progress", "resolved", "ignored"}
OPEN_ACTION_STATUSES = {"open", "in_progress"}
ACTION_PRIORITIES = {"low", "medium", "high", "critical"}


def _priority_from_alert(alert):
    severity = (alert or {}).get("severity")
    if severity == "critical":
        return "critical"
    if severity == "warning":
        return "high"
    return "medium"


def _serialize_action(row):
    return {
        "action_id": row["action_id"],
        "organization_id": row["organization_id"],
        "alert_id": row.get("alert_id"),
        "run_id": row.get("run_id"),
        "company_name": row.get("company_name"),
        "alert_title": row.get("alert_title"),
        "alert_type": row.get("alert_type"),
        "title": row["title"],
        "description": row.get("description"),
        "priority": row["priority"],
        "status": row["status"],
        "owner_name": row.get("owner_name"),
        "due_date": row.get("due_date"),
        "notes": row.get("notes"),
        "created_by_email": row.get("created_by_email"),
        "updated_by_email": row.get("updated_by_email"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "resolved_at": row.get("resolved_at"),
    }


def _serialize_comment(row):
    return {
        "comment_id": row["comment_id"],
        "action_id": row["action_id"],
        "organization_id": row["organization_id"],
        "author_user_id": row.get("author_user_id"),
        "author_name": row.get("author_name") or row.get("author_email"),
        "body": row["body"],
        "created_at": row.get("created_at"),
    }


def _select_action(cursor, organization_id, action_id):
    cursor.execute(
        """
        SELECT
            ca.*,
            ba.title AS alert_title,
            ba.alert_type,
            COALESCE(ca_alert.company_name, ca_run.company_name) AS company_name,
            creator.email AS created_by_email,
            updater.email AS updated_by_email
        FROM customer_actions ca
        LEFT JOIN business_alerts ba ON ba.alert_id = ca.alert_id
        LEFT JOIN companies ca_alert ON ca_alert.company_id = ba.company_id
        LEFT JOIN analysis_runs ar ON ar.run_id = ca.run_id
        LEFT JOIN companies ca_run ON ca_run.company_id = ar.company_id
        LEFT JOIN users creator ON creator.user_id = ca.created_by_user_id
        LEFT JOIN users updater ON updater.user_id = ca.updated_by_user_id
        WHERE ca.organization_id = %s
          AND ca.action_id = %s;
        """,
        (organization_id, action_id),
    )
    row = cursor.fetchone()
    if not row:
        raise ValueError("Action client introuvable.")
    return _serialize_action(row)


def _get_alert(cursor, organization_id, alert_id):
    cursor.execute(
        """
        SELECT alert_id, organization_id, run_id, company_id, severity, title, message
        FROM business_alerts
        WHERE organization_id = %s
          AND alert_id = %s;
        """,
        (organization_id, alert_id),
    )
    row = cursor.fetchone()
    if not row:
        raise ValueError("Alerte introuvable pour cette organisation.")
    return row


def _get_run(cursor, organization_id, run_id):
    cursor.execute(
        """
        SELECT run_id
        FROM analysis_runs
        WHERE organization_id = %s
          AND run_id = %s;
        """,
        (organization_id, run_id),
    )
    row = cursor.fetchone()
    if not row:
        raise ValueError("Run introuvable pour cette organisation.")
    return row


def list_customer_actions(organization_id: int, status="open", limit=30, offset=0):
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))

    params = [organization_id]
    status_clause = ""
    if status and status != "all":
        if status not in ACTION_STATUSES:
            raise ValueError("Statut d'action invalide.")
        status_clause = "AND ca.status = %s"
        params.append(status)

    params.extend([limit, offset])
    with get_cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                ca.*,
                ba.title AS alert_title,
                ba.alert_type,
                COALESCE(ca_alert.company_name, ca_run.company_name) AS company_name,
                creator.email AS created_by_email,
                updater.email AS updated_by_email
            FROM customer_actions ca
            LEFT JOIN business_alerts ba ON ba.alert_id = ca.alert_id
            LEFT JOIN companies ca_alert ON ca_alert.company_id = ba.company_id
            LEFT JOIN analysis_runs ar ON ar.run_id = ca.run_id
            LEFT JOIN companies ca_run ON ca_run.company_id = ar.company_id
            LEFT JOIN users creator ON creator.user_id = ca.created_by_user_id
            LEFT JOIN users updater ON updater.user_id = ca.updated_by_user_id
            WHERE ca.organization_id = %s
              {status_clause}
            ORDER BY
                CASE ca.priority
                    WHEN 'critical' THEN 0
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    ELSE 3
                END,
                ca.due_date ASC NULLS LAST,
                ca.updated_at DESC,
                ca.action_id DESC
            LIMIT %s OFFSET %s;
            """,
            tuple(params),
        )
        return [_serialize_action(row) for row in cursor.fetchall()]


def create_customer_action(
    organization_id: int,
    actor_user_id: int,
    payload: CustomerActionCreate,
):
    data = payload.model_dump(exclude_unset=True)
    alert = None
    run_id = data.get("run_id")
    alert_id = data.get("alert_id")

    with get_cursor(commit=True) as cursor:
        if alert_id is not None:
            alert = _get_alert(cursor, organization_id, alert_id)
            cursor.execute(
                """
                SELECT action_id
                FROM customer_actions
                WHERE organization_id = %s
                  AND alert_id = %s;
                """,
                (organization_id, alert_id),
            )
            existing = cursor.fetchone()
            if existing:
                return _select_action(cursor, organization_id, existing["action_id"])

            if run_id is None:
                run_id = alert.get("run_id")

        if run_id is not None:
            _get_run(cursor, organization_id, run_id)

        title = data.get("title") or (alert.get("title") if alert else None)
        if not title:
            title = "Action client"

        description = data.get("description")
        if description is None and alert:
            description = alert.get("message")

        priority = data.get("priority") or _priority_from_alert(alert)
        if priority not in ACTION_PRIORITIES:
            raise ValueError("Priorite d'action invalide.")

        status = data.get("status") or "open"
        if status not in ACTION_STATUSES:
            raise ValueError("Statut d'action invalide.")

        cursor.execute(
            """
            INSERT INTO customer_actions (
                organization_id,
                alert_id,
                run_id,
                title,
                description,
                priority,
                status,
                owner_name,
                due_date,
                notes,
                created_by_user_id,
                updated_by_user_id,
                resolved_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    CASE WHEN %s = 'resolved' THEN NOW() ELSE NULL END)
            RETURNING action_id;
            """,
            (
                organization_id,
                alert_id,
                run_id,
                title,
                description,
                priority,
                status,
                data.get("owner_name"),
                data.get("due_date"),
                data.get("notes"),
                actor_user_id,
                actor_user_id,
                status,
            ),
        )
        action_id = cursor.fetchone()["action_id"]
        return _select_action(cursor, organization_id, action_id)


def update_customer_action(
    action_id: int,
    organization_id: int,
    actor_user_id: int,
    payload: CustomerActionUpdate,
):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        with get_cursor() as cursor:
            return _select_action(cursor, organization_id, action_id)

    updates = []
    params = []
    for field in [
        "title",
        "description",
        "priority",
        "status",
        "owner_name",
        "due_date",
        "notes",
    ]:
        if field not in data:
            continue
        if field == "priority" and data[field] not in ACTION_PRIORITIES:
            raise ValueError("Priorite d'action invalide.")
        if field == "status" and data[field] not in ACTION_STATUSES:
            raise ValueError("Statut d'action invalide.")
        updates.append(f"{field} = %s")
        params.append(data[field])

    if "status" in data:
        if data["status"] == "resolved":
            updates.append("resolved_at = COALESCE(resolved_at, NOW())")
        else:
            updates.append("resolved_at = NULL")

    updates.extend(["updated_by_user_id = %s", "updated_at = NOW()"])
    params.extend([actor_user_id, organization_id, action_id])

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            f"""
            UPDATE customer_actions
            SET {", ".join(updates)}
            WHERE organization_id = %s
              AND action_id = %s
            RETURNING action_id;
            """,
            tuple(params),
        )
        if not cursor.fetchone():
            raise ValueError("Action client introuvable.")
        return _select_action(cursor, organization_id, action_id)


def list_customer_action_comments(action_id: int, organization_id: int, limit=30):
    limit = max(1, min(int(limit), 100))

    with get_cursor() as cursor:
        _select_action(cursor, organization_id, action_id)
        cursor.execute(
            """
            SELECT
                cac.*,
                users.full_name AS author_name,
                users.email AS author_email
            FROM customer_action_comments cac
            LEFT JOIN users ON users.user_id = cac.author_user_id
            WHERE cac.organization_id = %s
              AND cac.action_id = %s
            ORDER BY cac.created_at ASC, cac.comment_id ASC
            LIMIT %s;
            """,
            (organization_id, action_id, limit),
        )
        return [_serialize_comment(row) for row in cursor.fetchall()]


def create_customer_action_comment(
    action_id: int,
    organization_id: int,
    author_user_id: int,
    payload: CustomerActionCommentCreate,
):
    body = payload.body.strip()
    if not body:
        raise ValueError("Commentaire obligatoire.")

    with get_cursor(commit=True) as cursor:
        _select_action(cursor, organization_id, action_id)
        cursor.execute(
            """
            INSERT INTO customer_action_comments (
                action_id,
                organization_id,
                author_user_id,
                body
            )
            VALUES (%s, %s, %s, %s)
            RETURNING comment_id;
            """,
            (action_id, organization_id, author_user_id, body),
        )
        comment_id = cursor.fetchone()["comment_id"]
        cursor.execute(
            """
            SELECT
                cac.*,
                users.full_name AS author_name,
                users.email AS author_email
            FROM customer_action_comments cac
            LEFT JOIN users ON users.user_id = cac.author_user_id
            WHERE cac.organization_id = %s
              AND cac.comment_id = %s;
            """,
            (organization_id, comment_id),
        )
        return _serialize_comment(cursor.fetchone())
