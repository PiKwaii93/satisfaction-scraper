import re
from collections import Counter


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
