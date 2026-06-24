import json

from psycopg2.extras import Json

from app.api.database import get_cursor
from app.api.services.analysis_service import (
    get_analysis_run,
    get_distribution_count,
    get_run_summary,
    get_run_trend,
    normalize_label,
    percentage,
)
from app.api.services.insights import TOPIC_LABELS


NEGATIVE_LABEL = "N\u00e9gatif"
POSITIVE_LABEL = "Positif"


def serialize_business_alert(row):
    if row is None:
        return None

    metadata = row.get("metadata") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}

    return {
        "alert_id": row["alert_id"],
        "organization_id": row["organization_id"],
        "run_id": row.get("run_id"),
        "company_id": row.get("company_id"),
        "company_name": row.get("company_name"),
        "alert_type": row["alert_type"],
        "severity": row["severity"],
        "title": row["title"],
        "message": row["message"],
        "status": row["status"],
        "metadata": metadata,
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "acknowledged_at": row.get("acknowledged_at"),
        "resolved_at": row.get("resolved_at"),
    }


def _float(value, default=0.0):
    if value is None:
        return default
    return float(value)


def _int(value, default=0):
    if value is None:
        return default
    return int(value)


def _candidate(alert_type, severity, title, message, metadata=None):
    return {
        "alert_type": alert_type,
        "severity": severity,
        "title": title,
        "message": message,
        "metadata": metadata or {},
    }


def _topic_label(topic):
    if not topic:
        return "Sujet"
    return TOPIC_LABELS.get(topic, str(topic).replace("_", " ").capitalize())


def _build_snapshot_alerts(summary):
    kpis = summary["kpis"]
    insights = summary["business_insights"]
    review_count = _int(kpis.get("review_count"))
    text_count = _int(kpis.get("text_count"))
    responded_count = _int(kpis.get("responded_count"))
    average_confidence = _float(kpis.get("average_confidence"))
    health_score = _int(insights.get("health_score"))
    negative_count = get_distribution_count(
        summary["sentiment_distribution"],
        NEGATIVE_LABEL,
    )
    negative_rate = percentage(negative_count, review_count)
    alerts = []

    if negative_rate >= 50:
        alerts.append(
            _candidate(
                "negative_share_high",
                "critical",
                "Part d'avis negatifs elevee",
                (
                    f"{negative_rate:.1f}% des avis sont negatifs "
                    f"({negative_count}/{review_count})."
                ),
                {
                    "negative_count": negative_count,
                    "negative_rate": negative_rate,
                    "review_count": review_count,
                },
            )
        )
    elif negative_rate >= 35:
        alerts.append(
            _candidate(
                "negative_share_high",
                "warning",
                "Part d'avis negatifs a surveiller",
                (
                    f"{negative_rate:.1f}% des avis sont negatifs "
                    f"({negative_count}/{review_count})."
                ),
                {
                    "negative_count": negative_count,
                    "negative_rate": negative_rate,
                    "review_count": review_count,
                },
            )
        )

    if health_score < 40:
        alerts.append(
            _candidate(
                "health_score_low",
                "critical",
                "Score sante critique",
                f"Le score sante du run est de {health_score}/100.",
                {"health_score": health_score},
            )
        )
    elif health_score < 60:
        alerts.append(
            _candidate(
                "health_score_low",
                "warning",
                "Score sante faible",
                f"Le score sante du run est de {health_score}/100.",
                {"health_score": health_score},
            )
        )

    if average_confidence and average_confidence < 0.65:
        alerts.append(
            _candidate(
                "low_ai_confidence",
                "warning",
                "Confiance IA basse",
                f"La confiance moyenne du modele est de {average_confidence:.2f}.",
                {"average_confidence": round(average_confidence, 3)},
            )
        )

    top_topic = (summary.get("top_topics") or [None])[0]
    if top_topic and review_count:
        topic_count = _int(top_topic.get("count"))
        topic_share = percentage(topic_count, review_count)
        topic = top_topic.get("topic")
        if topic_count >= 8 and topic_share >= 20:
            alerts.append(
                _candidate(
                    "dominant_irritant",
                    "warning" if topic_share < 35 else "critical",
                    "Irritant dominant",
                    (
                        f"{_topic_label(topic)} concentre "
                        f"{topic_count} occurrence(s), soit {topic_share:.1f}% du run."
                    ),
                    {
                        "topic": topic,
                        "topic_count": topic_count,
                        "topic_share": topic_share,
                    },
                )
            )

    if review_count >= 10 and responded_count == 0 and negative_count >= 3:
        alerts.append(
            _candidate(
                "no_company_response",
                "warning",
                "Absence de reponse entreprise",
                (
                    "Aucun avis ne semble avoir recu de reponse entreprise "
                    f"sur ce lot de {review_count} avis."
                ),
                {
                    "responded_count": responded_count,
                    "negative_count": negative_count,
                    "review_count": review_count,
                },
            )
        )

    if text_count < review_count * 0.5 and review_count >= 10:
        alerts.append(
            _candidate(
                "low_text_coverage",
                "info",
                "Peu de verbatims exploitables",
                (
                    f"{text_count}/{review_count} avis contiennent un texte exploitable."
                ),
                {"text_count": text_count, "review_count": review_count},
            )
        )

    return alerts


def _build_trend_alerts(trend):
    if not trend or not trend.get("has_previous"):
        return []

    alerts = []
    negative_change = next(
        (
            row
            for row in trend.get("sentiment", [])
            if normalize_label(row.get("label")) == normalize_label(NEGATIVE_LABEL)
        ),
        None,
    )
    if negative_change and _float(negative_change.get("delta_rate")) >= 5:
        delta_rate = _float(negative_change.get("delta_rate"))
        alerts.append(
            _candidate(
                "negative_share_rising",
                "critical" if delta_rate >= 10 else "warning",
                "Hausse des avis negatifs",
                f"La part d'avis negatifs augmente de {delta_rate:.1f} points.",
                {
                    "delta_rate": delta_rate,
                    "delta_count": _int(negative_change.get("delta_count")),
                    "current_rate": _float(negative_change.get("current_rate")),
                    "previous_rate": _float(negative_change.get("previous_rate")),
                },
            )
        )

    health_metric = next(
        (metric for metric in trend.get("metrics", []) if metric.get("metric") == "health_score"),
        None,
    )
    if health_metric and health_metric.get("delta") is not None:
        health_delta = _float(health_metric.get("delta"))
        if health_delta <= -5:
            alerts.append(
                _candidate(
                    "health_score_drop",
                    "critical" if health_delta <= -10 else "warning",
                    "Score sante en baisse",
                    f"Le score sante baisse de {abs(health_delta):.1f} point(s).",
                    {
                        "delta": health_delta,
                        "current_value": health_metric.get("current_value"),
                        "previous_value": health_metric.get("previous_value"),
                    },
                )
            )

    rising_topic = next(
        (
            topic
            for topic in trend.get("rising_topics", [])
            if _int(topic.get("delta_count")) >= 3
        ),
        None,
    )
    if rising_topic:
        delta_count = _int(rising_topic.get("delta_count"))
        topic = rising_topic.get("topic")
        alerts.append(
            _candidate(
                "rising_irritant",
                "critical" if delta_count >= 8 else "warning",
                "Irritant en hausse",
                (
                    f"{_topic_label(topic)} augmente "
                    f"de {delta_count} occurrence(s)."
                ),
                {
                    "topic": topic,
                    "delta_count": delta_count,
                    "current_count": _int(rising_topic.get("current_count")),
                    "previous_count": _int(rising_topic.get("previous_count")),
                },
            )
        )

    new_topic = next(
        (
            topic
            for topic in trend.get("new_topics", [])
            if _int(topic.get("current_count")) >= 5
        ),
        None,
    )
    if new_topic:
        current_count = _int(new_topic.get("current_count"))
        topic = new_topic.get("topic")
        alerts.append(
            _candidate(
                "new_irritant",
                "warning",
                "Nouvel irritant detecte",
                (
                    f"{_topic_label(topic)} apparait avec "
                    f"{current_count} occurrence(s)."
                ),
                {
                    "topic": topic,
                    "current_count": current_count,
                },
            )
        )

    return alerts


def build_business_alert_candidates(run_id, organization_id):
    summary = get_run_summary(run_id, organization_id=organization_id)
    if summary is None:
        return []
    if summary["run"]["status"] != "completed":
        return []

    candidates = _build_snapshot_alerts(summary)
    try:
        candidates.extend(_build_trend_alerts(get_run_trend(run_id, organization_id)))
    except ValueError:
        pass

    seen = set()
    deduped = []
    for candidate in candidates:
        alert_type = candidate["alert_type"]
        if alert_type in seen:
            continue
        seen.add(alert_type)
        deduped.append(candidate)
    return deduped


def upsert_business_alerts_for_run(run_id, organization_id):
    run = get_analysis_run(run_id, organization_id=organization_id)
    if run is None:
        return []

    candidates = build_business_alert_candidates(run_id, organization_id)
    alerts = []
    with get_cursor(commit=True) as cursor:
        for candidate in candidates:
            cursor.execute(
                """
                INSERT INTO business_alerts (
                    organization_id,
                    run_id,
                    company_id,
                    alert_type,
                    severity,
                    title,
                    message,
                    metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (organization_id, run_id, alert_type)
                DO UPDATE SET
                    severity = EXCLUDED.severity,
                    title = EXCLUDED.title,
                    message = EXCLUDED.message,
                    metadata = EXCLUDED.metadata,
                    status = CASE
                        WHEN business_alerts.status = 'resolved' THEN 'open'
                        ELSE business_alerts.status
                    END,
                    updated_at = NOW(),
                    resolved_at = CASE
                        WHEN business_alerts.status = 'resolved' THEN NULL
                        ELSE business_alerts.resolved_at
                    END
                RETURNING *;
                """,
                (
                    organization_id,
                    run_id,
                    run["company_id"],
                    candidate["alert_type"],
                    candidate["severity"],
                    candidate["title"],
                    candidate["message"],
                    Json(candidate["metadata"]),
                ),
            )
            alerts.append(serialize_business_alert(cursor.fetchone()))
    return alerts


def generate_business_alerts_for_run(run_id):
    run = get_analysis_run(run_id)
    if run is None or run["status"] != "completed":
        return []
    return upsert_business_alerts_for_run(
        run_id=run_id,
        organization_id=run["organization_id"],
    )


def list_business_alerts(organization_id, status="open", limit=20, offset=0):
    filters = ["ba.organization_id = %s"]
    params = [organization_id]
    if status:
        filters.append("ba.status = %s")
        params.append(status)
    params.extend([limit, offset])

    with get_cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                ba.*,
                c.company_name
            FROM business_alerts ba
            LEFT JOIN companies c ON c.company_id = ba.company_id
            WHERE {" AND ".join(filters)}
            ORDER BY
                CASE ba.severity
                    WHEN 'critical' THEN 1
                    WHEN 'warning' THEN 2
                    ELSE 3
                END,
                ba.created_at DESC,
                ba.alert_id DESC
            LIMIT %s OFFSET %s;
            """,
            params,
        )
        return [serialize_business_alert(row) for row in cursor.fetchall()]


def update_business_alert_status(alert_id, organization_id, status):
    if status not in {"open", "acknowledged", "resolved"}:
        raise ValueError("Statut d'alerte invalide.")

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            """
            UPDATE business_alerts
            SET status = %s,
                acknowledged_at = CASE
                    WHEN %s = 'acknowledged' THEN COALESCE(acknowledged_at, NOW())
                    WHEN %s = 'open' THEN NULL
                    ELSE acknowledged_at
                END,
                resolved_at = CASE
                    WHEN %s = 'resolved' THEN COALESCE(resolved_at, NOW())
                    WHEN %s = 'open' THEN NULL
                    ELSE resolved_at
                END,
                updated_at = NOW()
            WHERE alert_id = %s
              AND organization_id = %s
            RETURNING *;
            """,
            (
                status,
                status,
                status,
                status,
                status,
                alert_id,
                organization_id,
            ),
        )
        return serialize_business_alert(cursor.fetchone())
