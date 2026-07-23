import json
from datetime import date, timedelta

from app.api.database import get_cursor
from app.api.schemas import (
    CustomerActionCommentCreate,
    CustomerActionCreate,
    CustomerActionUpdate,
)
from app.api.services.insights import TOPIC_LABELS, TOPIC_RECOMMENDATIONS


ACTION_STATUSES = {"open", "in_progress", "resolved", "ignored"}
OPEN_ACTION_STATUSES = {"open", "in_progress"}
ACTION_PRIORITIES = {"low", "medium", "high", "critical"}
TOPIC_IMPACT_ALERT_TYPES = {"dominant_irritant", "rising_irritant", "new_irritant"}
NEGATIVE_SHARE_IMPACT_ALERT_TYPES = {"negative_share_high", "negative_share_rising"}
HEALTH_IMPACT_ALERT_TYPES = {"health_score_low", "health_score_drop"}
RESPONSE_IMPACT_ALERT_TYPES = {"no_company_response"}
CONFIDENCE_IMPACT_ALERT_TYPES = {"low_ai_confidence"}


def _priority_from_alert(alert):
    severity = (alert or {}).get("severity")
    if severity == "critical":
        return "critical"
    if severity == "warning":
        return "high"
    return "medium"


def _alert_metadata(alert):
    metadata = (alert or {}).get("metadata") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    return metadata if isinstance(metadata, dict) else {}


def _topic_label(topic):
    if not topic:
        return "irritant"
    return TOPIC_LABELS.get(topic, str(topic).replace("_", " ").capitalize())


def _due_date_for_priority(priority):
    days_by_priority = {
        "critical": 2,
        "high": 5,
        "medium": 10,
        "low": 20,
    }
    return date.today() + timedelta(days=days_by_priority.get(priority, 10))


def _notes_for_playbook(title, steps, metrics):
    lines = [title, "", "Checklist"]
    lines.extend(f"- {step}" for step in steps)
    lines.extend(["", "Mesure de succes"])
    lines.extend(f"- {metric}" for metric in metrics)
    return "\n".join(lines)


def _build_customer_action_playbook(alert):
    if not alert:
        return {}

    alert_type = alert.get("alert_type")
    metadata = _alert_metadata(alert)
    topic = metadata.get("topic")
    priority = _priority_from_alert(alert)
    topic_label = _topic_label(topic)
    message = alert.get("message") or "Signal client detecte."

    if alert_type in {"dominant_irritant", "rising_irritant", "new_irritant"}:
        recommendation = TOPIC_RECOMMENDATIONS.get(
            topic,
            "Qualifier les avis concernes et prioriser les irritants recurrents.",
        )
        return {
            "title": f"Reduire l'irritant {topic_label}",
            "description": f"{message} Objectif: transformer ce signal en plan de reduction mesurable.",
            "priority": priority,
            "owner_name": "Responsable experience client",
            "due_date": _due_date_for_priority(priority),
            "notes": _notes_for_playbook(
                f"Playbook {topic_label}",
                [
                    "Isoler les avis representatifs du signal.",
                    recommendation,
                    "Identifier le parcours, produit ou equipe concerne.",
                    "Definir une action corrective et un responsable.",
                    "Recontroler le signal sur la prochaine analyse.",
                ],
                [
                    "Baisse du volume d'avis associes a cet irritant.",
                    "Baisse de la part d'avis negatifs sur le prochain run.",
                ],
            ),
        }

    if alert_type in {"negative_share_high", "negative_share_rising"}:
        return {
            "title": "Reduire la part d'avis negatifs",
            "description": f"{message} Objectif: traiter les causes racines et prioriser les clients a risque.",
            "priority": priority,
            "owner_name": "Responsable service client",
            "due_date": _due_date_for_priority(priority),
            "notes": _notes_for_playbook(
                "Playbook avis negatifs",
                [
                    "Lire les avis les plus recents et les plus critiques.",
                    "Regrouper les irritants dominants par theme.",
                    "Identifier les cas clients a recontacter rapidement.",
                    "Partager les causes racines avec l'equipe operationnelle.",
                    "Verifier l'evolution du negatif sur le prochain run.",
                ],
                [
                    "Diminution de la part d'avis negatifs.",
                    "Nombre de cas critiques recontactes.",
                ],
            ),
        }

    if alert_type in {"health_score_low", "health_score_drop"}:
        return {
            "title": "Redresser le score sante client",
            "description": f"{message} Objectif: restaurer les signaux de satisfaction prioritaires.",
            "priority": priority,
            "owner_name": "Responsable satisfaction client",
            "due_date": _due_date_for_priority(priority),
            "notes": _notes_for_playbook(
                "Playbook score sante",
                [
                    "Comparer les irritants du run avec la derniere analyse.",
                    "Choisir les deux signaux qui pesent le plus sur le score.",
                    "Ouvrir une action operationnelle par signal prioritaire.",
                    "Suivre la correction jusqu'a la prochaine analyse.",
                ],
                [
                    "Hausse du score sante.",
                    "Reduction du nombre d'alertes critiques.",
                ],
            ),
        }

    if alert_type == "no_company_response":
        return {
            "title": "Relancer la reponse aux avis publics",
            "description": f"{message} Objectif: remettre une boucle de reponse visible pour les clients.",
            "priority": priority,
            "owner_name": "Equipe relation client",
            "due_date": _due_date_for_priority(priority),
            "notes": _notes_for_playbook(
                "Playbook reponse entreprise",
                [
                    "Identifier les avis negatifs sans reponse.",
                    "Rediger des reponses courtes, factuelles et personnalisees.",
                    "Prioriser les avis recents et les cas non resolus.",
                    "Mesurer le taux de reponse sur le prochain run.",
                ],
                [
                    "Hausse du nombre d'avis avec reponse entreprise.",
                    "Reduction des avis critiques sans suivi visible.",
                ],
            ),
        }

    if alert_type == "low_ai_confidence":
        return {
            "title": "Verifier la qualite des predictions IA",
            "description": f"{message} Objectif: auditer les cas incertains avant reentrainement.",
            "priority": priority,
            "owner_name": "Referent data",
            "due_date": _due_date_for_priority(priority),
            "notes": _notes_for_playbook(
                "Playbook qualite IA",
                [
                    "Filtrer les avis a faible score de confiance.",
                    "Corriger les labels manifestement incoherents.",
                    "Comparer note, verbatim et sentiment predit.",
                    "Relancer un reentrainement si le volume corrige est suffisant.",
                ],
                [
                    "Hausse de la confiance moyenne.",
                    "Baisse des corrections necessaires sur le prochain run.",
                ],
            ),
        }

    return {
        "title": alert.get("title") or "Traiter le signal client",
        "description": message,
        "priority": priority,
        "owner_name": "Equipe service client",
        "due_date": _due_date_for_priority(priority),
        "notes": _notes_for_playbook(
            "Playbook generique",
            [
                "Qualifier le signal et son impact client.",
                "Identifier les avis ou parcours concernes.",
                "Definir une action corrective mesurable.",
                "Recontroler le signal apres correction.",
            ],
            [
                "Signal stabilise ou en baisse.",
                "Action documentee dans le plan client.",
            ],
        ),
    }


def _normalize_text(value):
    return (
        str(value or "")
        .replace("Ã©", "e")
        .replace("Ã¨", "e")
        .replace("Ãª", "e")
        .replace("Ã ", "a")
        .strip()
        .lower()
    )


def _round_metric(value):
    if value is None:
        return None
    return round(float(value), 1)


def _metric_value(summary, metric_key, topic=None):
    if not summary:
        return None

    kpis = summary.get("kpis") or {}
    review_count = float(kpis.get("review_count") or 0)

    if metric_key == "negative_share":
        if review_count <= 0:
            return 0.0
        for row in summary.get("sentiment_distribution") or []:
            label = _normalize_text(row.get("label"))
            if label in {"negatif", "negative"}:
                return float(row.get("count") or 0) * 100 / review_count
        return 0.0

    if metric_key == "health_score":
        return float((summary.get("business_insights") or {}).get("health_score") or 0)

    if metric_key == "topic_count":
        for row in summary.get("top_topics") or []:
            if row.get("topic") == topic:
                return float(row.get("count") or 0)
        return 0.0

    if metric_key == "response_rate":
        if review_count <= 0:
            return 0.0
        return float(kpis.get("responded_count") or 0) * 100 / review_count

    if metric_key == "average_confidence":
        value = float(kpis.get("average_confidence") or 0)
        return value * 100 if value <= 1 else value

    return None


def _impact_status_for_delta(metric_key, delta):
    if delta is None:
        return "not_measurable"
    if abs(float(delta)) < 1:
        return "stable"
    if metric_key in {"negative_share", "topic_count"}:
        return "improved" if delta < 0 else "degraded"
    return "improved" if delta > 0 else "degraded"


def _impact_label(status):
    labels = {
        "not_measurable": "A mesurer",
        "improved": "Amelioration",
        "stable": "Stable",
        "degraded": "Degradation",
    }
    return labels.get(status, "Stable")


def _impact_metric_for_action(alert_type, metadata):
    if alert_type in TOPIC_IMPACT_ALERT_TYPES:
        topic = metadata.get("topic")
        return "topic_count", f"Irritant {_topic_label(topic)}", "avis", topic
    if alert_type in NEGATIVE_SHARE_IMPACT_ALERT_TYPES:
        return "negative_share", "Part d'avis negatifs", "pts", None
    if alert_type in HEALTH_IMPACT_ALERT_TYPES:
        return "health_score", "Score sante", "/100", None
    if alert_type in RESPONSE_IMPACT_ALERT_TYPES:
        return "response_rate", "Taux de reponse entreprise", "pts", None
    if alert_type in CONFIDENCE_IMPACT_ALERT_TYPES:
        return "average_confidence", "Confiance IA moyenne", "pts", None
    return "health_score", "Score sante", "/100", None


def _impact_summary(status, metric_label):
    if status == "not_measurable":
        return "Relance une analyse de la meme entreprise pour mesurer l'impact."
    if status == "improved":
        return f"{metric_label} s'ameliore entre le run d'origine et le run suivant."
    if status == "degraded":
        return f"{metric_label} se degrade entre le run d'origine et le run suivant."
    return f"{metric_label} reste stable entre le run d'origine et le run suivant."


def _build_action_impact(cursor, organization_id, row):
    run_id = row.get("impact_run_id") or row.get("run_id")
    company_id = row.get("impact_company_id")
    metadata = _alert_metadata({"metadata": row.get("alert_metadata")})
    metric_key, metric_label, unit, topic = _impact_metric_for_action(
        row.get("alert_type"), metadata
    )
    base = {
        "status": "not_measurable",
        "label": _impact_label("not_measurable"),
        "summary": _impact_summary("not_measurable", metric_label),
        "metric_label": metric_label,
        "unit": unit,
        "baseline_run_id": run_id,
        "comparison_run_id": None,
        "baseline_value": None,
        "comparison_value": None,
        "delta": None,
    }
    if not run_id or not company_id:
        return base

    cursor.execute(
        """
        SELECT run_id
        FROM analysis_runs
        WHERE organization_id = %s
          AND company_id = %s
          AND status = 'completed'
          AND run_id > %s
        ORDER BY run_id ASC
        LIMIT 1;
        """,
        (organization_id, company_id, run_id),
    )
    comparison = cursor.fetchone()
    if not comparison:
        return base

    from app.api.services.analysis_service import get_run_summary

    try:
        baseline_summary = get_run_summary(run_id, organization_id=organization_id)
        comparison_summary = get_run_summary(
            comparison["run_id"], organization_id=organization_id
        )
    except ValueError:
        return base

    baseline_value = _round_metric(_metric_value(baseline_summary, metric_key, topic))
    comparison_value = _round_metric(_metric_value(comparison_summary, metric_key, topic))
    delta = (
        _round_metric(comparison_value - baseline_value)
        if baseline_value is not None and comparison_value is not None
        else None
    )
    status = _impact_status_for_delta(metric_key, delta)
    return {
        "status": status,
        "label": _impact_label(status),
        "summary": _impact_summary(status, metric_label),
        "metric_label": metric_label,
        "unit": unit,
        "baseline_run_id": run_id,
        "comparison_run_id": comparison["run_id"],
        "baseline_value": baseline_value,
        "comparison_value": comparison_value,
        "delta": delta,
    }


def _serialize_action(row, impact=None):
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
        "impact": impact,
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
            ba.metadata AS alert_metadata,
            COALESCE(ca.run_id, ba.run_id) AS impact_run_id,
            COALESCE(ba.company_id, ar.company_id) AS impact_company_id,
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
    return _serialize_action(row, _build_action_impact(cursor, organization_id, row))


def _get_alert(cursor, organization_id, alert_id):
    cursor.execute(
        """
        SELECT
            alert_id,
            organization_id,
            run_id,
            company_id,
            severity,
            alert_type,
            title,
            message,
            metadata
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
                ba.metadata AS alert_metadata,
                COALESCE(ca.run_id, ba.run_id) AS impact_run_id,
                COALESCE(ba.company_id, ar.company_id) AS impact_company_id,
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
        return [
            _serialize_action(row, _build_action_impact(cursor, organization_id, row))
            for row in cursor.fetchall()
        ]


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

        playbook = _build_customer_action_playbook(alert)

        title = data.get("title") or playbook.get("title") or (alert.get("title") if alert else None)
        if not title:
            title = "Action client"

        description = data.get("description")
        if description is None:
            description = playbook.get("description")
        if description is None and alert:
            description = alert.get("message")

        priority = data.get("priority") or playbook.get("priority") or _priority_from_alert(alert)
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
                data.get("owner_name") or playbook.get("owner_name"),
                data.get("due_date") or playbook.get("due_date"),
                data.get("notes") or playbook.get("notes"),
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
