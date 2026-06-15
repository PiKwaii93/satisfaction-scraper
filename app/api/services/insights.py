import re
from collections import Counter


TOPIC_LABELS = {
    "livraison": "Livraison",
    "delai": "Delais",
    "sav": "Service client",
    "remboursement": "Remboursement",
    "retour": "Retours",
    "qualite_produit": "Qualite produit",
    "prix": "Prix",
    "site_app": "Site / application",
}

TOPIC_RECOMMENDATIONS = {
    "livraison": "Auditer les transporteurs, les points relais et les messages de suivi de commande.",
    "delai": "Clarifier les delais annonces et isoler les parcours ou l'attente depasse la promesse client.",
    "sav": "Prioriser les tickets non resolus et mesurer le temps de premiere reponse du support.",
    "remboursement": "Rendre le remboursement plus previsible avec des statuts visibles et des delais annonces.",
    "retour": "Simplifier le parcours retour et reduire les frictions sur les demandes d'echange.",
    "qualite_produit": "Identifier les references les plus citees et renforcer les controles qualite ou les fiches produit.",
    "prix": "Verifier la perception des frais annexes et mieux expliciter la valeur du service.",
    "site_app": "Rejouer les parcours de commande signales et corriger les irritants d'interface prioritaires.",
}

TOPIC_IMPACTS = {
    "livraison": "Risque direct sur la confiance et la repetition d'achat.",
    "delai": "Risque de frustration eleve car l'attente degrade toute l'experience.",
    "sav": "Risque de perte client quand le probleme initial reste sans resolution claire.",
    "remboursement": "Risque financier percu et escalation rapide vers des avis publics.",
    "retour": "Risque de blocage post-achat et de baisse de conversion future.",
    "qualite_produit": "Risque sur la promesse produit et sur la credibilite de la marque.",
    "prix": "Risque de sentiment d'injustice si les frais ou tarifs semblent mal expliques.",
    "site_app": "Risque d'abandon ou de contact support inutile pendant le parcours.",
}

TOPIC_PATTERNS = {
    "livraison": re.compile(
        r"\b(livraison|livr[eé]|colis|transporteur|relais|exp[eé]dition)\b",
        re.IGNORECASE,
    ),
    "delai": re.compile(
        r"\b(retard|d[eé]lai|attente|trop long(?:ue)?s?|temps)\b",
        re.IGNORECASE,
    ),
    "sav": re.compile(
        r"\b(service client|sav|support|conseiller|r[eé]clamation|contact)\b",
        re.IGNORECASE,
    ),
    "remboursement": re.compile(
        r"\b(rembours|avoir|compensation|indemnis|pr[eé]l[eè]vement)\b",
        re.IGNORECASE,
    ),
    "retour": re.compile(
        r"\b(retour|renvoi|r[eé]exp[eé]dition|[eé]change)\b",
        re.IGNORECASE,
    ),
    "qualite_produit": re.compile(
        r"\b(qualit[eé]|produit|article|cass[eé]|ab[iî]m[eé]|d[eé]fectueux|conforme|taille)\b",
        re.IGNORECASE,
    ),
    "prix": re.compile(
        r"\b(prix|cher|frais|promo|promotion|tarif)\b",
        re.IGNORECASE,
    ),
    "site_app": re.compile(
        r"\b(site|application|appli|commande en ligne|compte client|plateforme)\b",
        re.IGNORECASE,
    ),
}


def detect_topics(text):
    if not text:
        return []

    return [
        topic
        for topic, pattern in TOPIC_PATTERNS.items()
        if pattern.search(text)
    ]


def summarize_topics(rows):
    counter = Counter()
    for row in rows:
        counter.update(row.get("topics", []))
    return [{"topic": topic, "count": count} for topic, count in counter.most_common()]


def _as_float(value, default=0.0):
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value, default=0):
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _label_kind(label):
    normalized = str(label or "").strip().lower()
    if normalized.startswith("p"):
        return "positive"
    if normalized.startswith("n") and "gatif" in normalized:
        return "negative"
    if normalized.startswith("n") and "eutre" in normalized:
        return "neutral"
    return normalized


def _sentiment_count(rows, kind):
    return sum(
        _as_int(row.get("count"))
        for row in rows
        if _label_kind(row.get("label") or row.get("sentiment_label")) == kind
    )


def _severity(negative_count, total_reviews, topic_negative_ratio):
    global_ratio = negative_count / max(total_reviews, 1)
    if negative_count >= 12 or global_ratio >= 0.18 or topic_negative_ratio >= 0.7:
        return "critique"
    if negative_count >= 6 or global_ratio >= 0.09 or topic_negative_ratio >= 0.5:
        return "elevee"
    return "moderee"


def _risk_level(health_score, negative_ratio):
    if health_score < 40 or negative_ratio >= 0.55:
        return "critique"
    if health_score < 60 or negative_ratio >= 0.35:
        return "eleve"
    if health_score < 78 or negative_ratio >= 0.2:
        return "modere"
    return "faible"


def _serialize_review_example(row):
    return {
        "review_id": row.get("review_id"),
        "rating": row.get("rating"),
        "sentiment_label": row.get("sentiment_label"),
        "sentiment_score": _as_float(row.get("sentiment_score")),
        "verbatim": row.get("verbatim"),
    }


def _group_examples(rows, max_per_topic=2):
    grouped = {}
    for row in rows:
        topic = row.get("topic")
        if not topic:
            continue
        grouped.setdefault(topic, [])
        if len(grouped[topic]) < max_per_topic:
            grouped[topic].append(_serialize_review_example(row))
    return grouped


def build_business_insights(
    kpis,
    sentiment_distribution,
    topic_sentiment_distribution,
    negative_topic_examples,
    positive_topic_examples,
    critical_reviews,
    rating_text_mismatches,
):
    review_count = _as_int(kpis.get("review_count"))
    average_rating = _as_float(kpis.get("average_rating"))
    average_confidence = _as_float(kpis.get("average_confidence"))
    responded_count = _as_int(kpis.get("responded_count"))
    text_count = _as_int(kpis.get("text_count"))

    negative_count = _sentiment_count(sentiment_distribution, "negative")
    neutral_count = _sentiment_count(sentiment_distribution, "neutral")
    positive_count = _sentiment_count(sentiment_distribution, "positive")
    negative_ratio = negative_count / max(review_count, 1)
    neutral_ratio = neutral_count / max(review_count, 1)
    positive_ratio = positive_count / max(review_count, 1)
    mismatch_count = len(rating_text_mismatches)

    if review_count == 0:
        health_score = 0
    else:
        health_score = round(
            100
            - (negative_ratio * 90)
            - (neutral_ratio * 12)
            + (positive_ratio * 5)
            + ((average_rating - 3) * 12)
            - ((mismatch_count / review_count) * 15)
        )
        health_score = max(0, min(100, health_score))
    risk_level = _risk_level(health_score, negative_ratio)

    topic_stats = {}
    for row in topic_sentiment_distribution:
        topic = row.get("topic")
        if not topic:
            continue
        stats = topic_stats.setdefault(
            topic,
            {"topic": topic, "negative": 0, "neutral": 0, "positive": 0, "total": 0},
        )
        count = _as_int(row.get("count"))
        stats["total"] += count
        stats[_label_kind(row.get("sentiment_label"))] = (
            stats.get(_label_kind(row.get("sentiment_label")), 0) + count
        )

    negative_examples = _group_examples(negative_topic_examples)
    positive_examples = _group_examples(positive_topic_examples, max_per_topic=1)

    ranked_issues = sorted(
        topic_stats.values(),
        key=lambda item: (item["negative"], item["total"]),
        reverse=True,
    )
    priorities = []
    for stats in ranked_issues:
        if stats["negative"] <= 0:
            continue
        topic = stats["topic"]
        topic_negative_ratio = stats["negative"] / max(stats["total"], 1)
        priorities.append(
            {
                "rank": len(priorities) + 1,
                "topic": topic,
                "title": f"Reduire l'irritant {TOPIC_LABELS.get(topic, topic)}",
                "severity": _severity(
                    stats["negative"],
                    review_count,
                    topic_negative_ratio,
                ),
                "negative_reviews": stats["negative"],
                "share_of_reviews": round((stats["negative"] / max(review_count, 1)) * 100, 1),
                "impact": TOPIC_IMPACTS.get(topic, "Risque de degradation de l'experience client."),
                "recommendation": TOPIC_RECOMMENDATIONS.get(
                    topic,
                    "Analyser les verbatims associes et definir une action corrective ciblee.",
                ),
                "examples": negative_examples.get(topic, []),
            }
        )
        if len(priorities) == 4:
            break

    ranked_strengths = sorted(
        topic_stats.values(),
        key=lambda item: (item["positive"], item["total"]),
        reverse=True,
    )
    strengths = []
    for stats in ranked_strengths:
        if stats["positive"] <= 0:
            continue
        topic = stats["topic"]
        strengths.append(
            {
                "topic": topic,
                "title": f"Capitaliser sur {TOPIC_LABELS.get(topic, topic)}",
                "positive_reviews": stats["positive"],
                "recommendation": "Conserver ce point fort dans la promesse client et l'utiliser comme preuve dans la communication.",
                "examples": positive_examples.get(topic, []),
            }
        )
        if len(strengths) == 3:
            break

    watchpoints = []
    if mismatch_count:
        mismatch_label = "avis combine" if mismatch_count == 1 else "avis combinent"
        watchpoints.append(
            {
                "title": "Ecart note / texte",
                "message": f"{mismatch_count} {mismatch_label} une note et un texte qui racontent des signaux differents.",
                "level": "warning",
            }
        )
    if review_count and text_count / review_count < 0.75:
        watchpoints.append(
            {
                "title": "Verbatims manquants",
                "message": "Une partie importante des avis n'a pas de texte, l'analyse qualitative est donc moins riche.",
                "level": "warning",
            }
        )
    if negative_count and responded_count == 0:
        watchpoints.append(
            {
                "title": "Absence de reponses publiques",
                "message": "Aucun avis ne semble avoir recu de reponse entreprise dans ce lot.",
                "level": "warning",
            }
        )
    if average_confidence and average_confidence < 0.65:
        watchpoints.append(
            {
                "title": "Confiance IA a surveiller",
                "message": "Le score moyen du modele est modere, certains avis meritent une lecture humaine.",
                "level": "info",
            }
        )

    if priorities:
        next_actions = [
            priority["recommendation"] for priority in priorities[:3]
        ]
    elif positive_count > negative_count:
        next_actions = [
            "Identifier les formulations positives recurrentes pour renforcer la promesse commerciale.",
            "Continuer la veille sur les irritants faibles afin de detecter une degradation rapide.",
        ]
    else:
        next_actions = [
            "Lire les avis critiques les mieux scores pour confirmer les causes principales.",
            "Annoter quelques avis supplementaires si le contexte metier semble different du dataset d'entrainement.",
        ]

    executive_summary = (
        f"{review_count} avis analyses: {negative_count} negatifs, "
        f"{neutral_count} neutres et {positive_count} positifs. "
        f"Le niveau de risque est {risk_level}, avec un score sante de {health_score}/100."
    )

    return {
        "health_score": health_score,
        "risk_level": risk_level,
        "executive_summary": executive_summary,
        "priorities": priorities,
        "strengths": strengths,
        "watchpoints": watchpoints,
        "next_actions": next_actions,
        "critical_review_count": len(critical_reviews),
    }
