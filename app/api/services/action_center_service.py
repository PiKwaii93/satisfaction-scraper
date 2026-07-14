from app.api.database import get_cursor


def _int(value, default=0):
    if value is None:
        return default
    return int(value)


def _item(
    item_id,
    item_type,
    severity,
    title,
    message,
    *,
    action_label=None,
    action_target=None,
    requires_admin=False,
    created_at=None,
):
    return {
        "item_id": item_id,
        "item_type": item_type,
        "severity": severity,
        "title": title,
        "message": message,
        "action_label": action_label,
        "action_target": action_target or {},
        "requires_admin": requires_admin,
        "created_at": created_at,
    }


def _count_feedback_ready(cursor, organization_id):
    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM review_feedback rf
        JOIN reviews r ON r.review_id = rf.review_id
        JOIN analysis_runs ar ON ar.run_id = r.run_id
        WHERE ar.organization_id = %s
          AND COALESCE(r.verbatim, '') <> '';
        """,
        (organization_id,),
    )
    return _int(cursor.fetchone()["count"])


def get_action_center(organization_id: int, role: str = "member", limit=8):
    is_admin = role == "admin"

    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(*) AS open_alerts,
                COALESCE(
                    SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END),
                    0
                ) AS critical_alerts
            FROM business_alerts
            WHERE organization_id = %s
              AND status = 'open';
            """,
            (organization_id,),
        )
        alert_counts = cursor.fetchone()

        cursor.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE status = 'failed') AS failed_runs,
                COUNT(*) FILTER (WHERE status IN ('pending', 'running')) AS active_runs,
                COUNT(*) FILTER (
                    WHERE status = 'completed'
                      AND finished_at >= NOW() - INTERVAL '7 days'
                ) AS recent_completed_runs
            FROM analysis_runs
            WHERE organization_id = %s;
            """,
            (organization_id,),
        )
        run_counts = cursor.fetchone()

        pending_invitations = 0
        training_ready_corrections = 0
        if is_admin:
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM users
                WHERE organization_id = %s
                  AND account_status = 'pending';
                """,
                (organization_id,),
            )
            pending_invitations = _int(cursor.fetchone()["count"])
            training_ready_corrections = _count_feedback_ready(cursor, organization_id)

            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM upgrade_requests
                WHERE organization_id = %s
                  AND status IN ('pending', 'approved');
                """,
                (organization_id,),
            )
            pending_upgrade_requests = _int(cursor.fetchone()["count"])
        else:
            pending_upgrade_requests = 0

        items = []

        cursor.execute(
            """
            SELECT
                ba.alert_id,
                ba.run_id,
                ba.severity,
                ba.title,
                ba.message,
                ba.created_at,
                c.company_name
            FROM business_alerts ba
            LEFT JOIN companies c ON c.company_id = ba.company_id
            WHERE ba.organization_id = %s
              AND ba.status = 'open'
            ORDER BY
                CASE ba.severity
                    WHEN 'critical' THEN 0
                    WHEN 'warning' THEN 1
                    ELSE 2
                END,
                ba.alert_id DESC
            LIMIT 3;
            """,
            (organization_id,),
        )
        for alert in cursor.fetchall():
            items.append(
                _item(
                    f"alert:{alert['alert_id']}",
                    "business_alert",
                    alert["severity"],
                    alert["title"],
                    alert["message"],
                    action_label="Ouvrir le run" if alert.get("run_id") else None,
                    action_target={
                        "alert_id": alert["alert_id"],
                        "run_id": alert.get("run_id"),
                    },
                    created_at=alert.get("created_at"),
                )
            )

        cursor.execute(
            """
            SELECT
                ar.run_id,
                ar.error_message,
                ar.updated_at,
                ar.created_at,
                c.company_name
            FROM analysis_runs ar
            JOIN companies c ON c.company_id = ar.company_id
            WHERE ar.organization_id = %s
              AND ar.status = 'failed'
            ORDER BY ar.updated_at DESC, ar.run_id DESC
            LIMIT 2;
            """,
            (organization_id,),
        )
        for run in cursor.fetchall():
            items.append(
                _item(
                    f"failed_run:{run['run_id']}",
                    "failed_run",
                    "critical",
                    "Analyse echouee",
                    (
                        f"{run['company_name']} n'a pas termine son analyse."
                        if not run.get("error_message")
                        else f"{run['company_name']}: {run['error_message']}"
                    ),
                    action_label="Ouvrir le run",
                    action_target={"run_id": run["run_id"]},
                    requires_admin=True,
                    created_at=run.get("updated_at") or run.get("created_at"),
                )
            )

        if is_admin and pending_invitations:
            items.append(
                _item(
                    "pending_invitations",
                    "pending_invitation",
                    "warning",
                    "Invitations en attente",
                    f"{pending_invitations} invitation(s) n'ont pas encore ete activees.",
                    action_label="Voir les membres",
                    action_target={"section": "client_space"},
                    requires_admin=True,
                )
            )

        if is_admin and pending_upgrade_requests:
            cursor.execute(
                """
                SELECT
                    upgrade_request_id,
                    requested_plan,
                    current_plan,
                    status,
                    requested_by_email,
                    created_at
                FROM upgrade_requests
                WHERE organization_id = %s
                  AND status IN ('pending', 'approved')
                ORDER BY upgrade_request_id DESC
                LIMIT 2;
                """,
                (organization_id,),
            )
            for upgrade_request in cursor.fetchall():
                items.append(
                    _item(
                        f"upgrade_request:{upgrade_request['upgrade_request_id']}",
                        "upgrade_request",
                        "info",
                        "Demande d'upgrade",
                        (
                            f"{upgrade_request['requested_by_email'] or 'Un utilisateur'} "
                            f"demande le plan {upgrade_request['requested_plan']} "
                            f"depuis {upgrade_request['current_plan']}."
                        ),
                        action_label="Voir le plan",
                        action_target={
                            "section": "client_space",
                            "upgrade_request_id": upgrade_request["upgrade_request_id"],
                        },
                        requires_admin=True,
                        created_at=upgrade_request.get("created_at"),
                    )
                )

        if is_admin and training_ready_corrections:
            items.append(
                _item(
                    "training_feedback_ready",
                    "training_feedback",
                    "info",
                    "Corrections pretes pour l'IA",
                    (
                        f"{training_ready_corrections} correction(s) peuvent "
                        "alimenter le prochain reentrainement."
                    ),
                    action_label="Voir qualite IA",
                    action_target={"section": "ai_quality"},
                    requires_admin=True,
                )
            )

        cursor.execute(
            """
            SELECT
                ar.run_id,
                ar.status,
                ar.total_reviews,
                ar.updated_at,
                ar.created_at,
                c.company_name
            FROM analysis_runs ar
            JOIN companies c ON c.company_id = ar.company_id
            WHERE ar.organization_id = %s
              AND ar.status IN ('pending', 'running')
            ORDER BY ar.updated_at DESC, ar.run_id DESC
            LIMIT 2;
            """,
            (organization_id,),
        )
        for run in cursor.fetchall():
            items.append(
                _item(
                    f"active_run:{run['run_id']}",
                    "active_run",
                    "info",
                    "Analyse en cours",
                    f"{run['company_name']} est encore en traitement.",
                    action_label="Suivre",
                    action_target={"run_id": run["run_id"]},
                    created_at=run.get("updated_at") or run.get("created_at"),
                )
            )

        cursor.execute(
            """
            SELECT
                ar.run_id,
                ar.total_reviews,
                ar.finished_at,
                ar.created_at,
                c.company_name
            FROM analysis_runs ar
            JOIN companies c ON c.company_id = ar.company_id
            WHERE ar.organization_id = %s
              AND ar.status = 'completed'
            ORDER BY ar.finished_at DESC NULLS LAST, ar.run_id DESC
            LIMIT 2;
            """,
            (organization_id,),
        )
        for run in cursor.fetchall():
            items.append(
                _item(
                    f"completed_run:{run['run_id']}",
                    "completed_run",
                    "success",
                    "Analyse terminee",
                    (
                        f"{run['company_name']} est disponible "
                        f"avec {_int(run.get('total_reviews'))} avis."
                    ),
                    action_label="Ouvrir",
                    action_target={"run_id": run["run_id"]},
                    created_at=run.get("finished_at") or run.get("created_at"),
                )
            )

    return {
        "counts": {
            "open_alerts": _int(alert_counts["open_alerts"]),
            "critical_alerts": _int(alert_counts["critical_alerts"]),
            "failed_runs": _int(run_counts["failed_runs"]),
            "active_runs": _int(run_counts["active_runs"]),
            "pending_invitations": pending_invitations,
            "pending_upgrade_requests": pending_upgrade_requests,
            "training_ready_corrections": training_ready_corrections,
            "recent_completed_runs": _int(run_counts["recent_completed_runs"]),
        },
        "items": items[:limit],
    }
