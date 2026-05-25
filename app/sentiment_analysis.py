import os
import re

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd


mlflow_url = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
mlflow.set_tracking_uri(mlflow_url)

MODEL_LOADED = False
model = None

NEGATIVE_SIGNAL_RE = re.compile(
    r"\b("
    r"retard|retard[ée]e?|trop long(?:ue)?s?|longue?s?|non conforme|non compl[èe]te|"
    r"endommag[ée]s?|perfor[ée]s?|coll[ée]s?|cass[ée]s?|ab[iî]m[ée]s?|d[ée][çc]u(?:e|s|es)?|"
    r"impossible|probl[eè]me|souci|mauvais|honteux|"
    r"pas re[çc]u|aucune nouvelle|frais.*cher|cher[s]?|"
    r"retour|remboursement|r[ée]clamation"
    r")\b",
    flags=re.IGNORECASE,
)

STRONG_NEGATIVE_SIGNAL_RE = re.compile(
    r"\b("
    r"retard de livraison|trop long(?:ue)?s?|non conforme|non compl[èe]te|"
    r"commande incompl[èe]te|pas re[çc]u|non re[çc]u|colis non re[çc]u|"
    r"endommag[ée]s?|perfor[ée]s?|cass[ée]s?|ab[iî]m[ée]s?|"
    r"un peu d[ée][çc]u(?:e|s|es)?.{0,40}qualit[ée]|"
    r"tr[eè]s d[ée][çc]u(?:e|s|es)?.{0,40}qualit[ée]"
    r")\b",
    flags=re.IGNORECASE,
)

STRONG_POSITIVE_SIGNAL_RE = re.compile(
    r"\b("
    r"tr[eè]s satisfait|extr[êe]mement satisfaite?|toujours satisfaite?|"
    r"tr[eè]s bon|parfait|conforme|rapide|pas trop long(?:ue)?s?|"
    r"jamais (?:[ée]t[ée] )?d[ée][çc]u(?:e|s|es)?|pas d[ée][çc]u(?:e|s|es)?|"
    r"sans probl[eè]me|pas de probl[eè]me|jamais eu de probl[eè]me"
    r")\b",
    flags=re.IGNORECASE,
)

RESOLVED_POSITIVE_SIGNAL_RE = re.compile(
    r"\b("
    r"probl[eè]me (?:r[ée]solu|r[eé]gl[ée])|"
    r"(?:r[ée]solu|r[eé]gl[ée]).{0,40}probl[eè]me|"
    r"rembours[ée]?.{0,45}(?:rapidement|24\s*h|sur ma carte|sans probl[eè]me)|"
    r"a fait (?:le maximum|tout pour)|tout pour me satisfaire|"
    r"enti[eè]re satisfaction|"
    r"avis g[ée]n[ée]ral reste tr[eè]s positif|"
    r"absolument g[ée]nial|je recommande vivement|"
    r"tr[eè]s efficace|livraison est respect[ée]e|"
    r"au top|je remercie.{0,100}efficac|"
    r"retour.{0,140}(?:technicien|efficac|fonctionnait|repartir)"
    r")\b",
    flags=re.IGNORECASE,
)


MIXED_POSITIVE_SIGNAL_RE = re.compile(
    r"\b("
    r"mini soucis?.{0,100}(?:super enseigne|je met[s]?\s+10|tout le reste)|"
    r"petit bug.{0,120}rien de (?:tr[eè]s )?grave|"
    r"rien de (?:tr[eè]s )?grave|"
    r"probl[eè]me.{0,100}(?:conseill[ée]|expliqu[ée])|"
    r"conseill[ée].{0,100}expliqu[ée]|"
    r"super enseigne|je met[s]?\s+10 pour tout le reste"
    r")\b",
    flags=re.IGNORECASE,
)


try:
    print("\n--- CHARGEMENT DU MODÈLE DEPUIS LE REGISTRE ---")
    model_uri = "models:/sentiment_model@production"
    model = mlflow.sklearn.load_model(model_uri)
    MODEL_LOADED = True
    print("[+] Modèle ML multi-classe chargé avec succès depuis MLflow !\n")
except Exception as e:
    print(f"\n[-] Attention : Impossible de charger le modèle ML ({e}).")
    print("[-] Bascule vers le mode fallback (TextBlob).")
    MODEL_LOADED = False


def apply_business_guardrails(label, score, text, rating=None):
    """Évite les faux positifs évidents sur les avis à problème explicite."""
    rating_value = int(rating) if rating is not None else None
    has_negative_signal = bool(NEGATIVE_SIGNAL_RE.search(text or ""))
    has_strong_negative_signal = bool(
        STRONG_NEGATIVE_SIGNAL_RE.search(text or "")
    ) and not re.search(r"\b(?:pas|plus)\s+trop\s+long", text or "", re.IGNORECASE)
    has_strong_positive_signal = bool(STRONG_POSITIVE_SIGNAL_RE.search(text or ""))
    has_resolved_positive_signal = bool(
        RESOLVED_POSITIVE_SIGNAL_RE.search(text or "")
    )
    has_mixed_positive_signal = bool(
        MIXED_POSITIVE_SIGNAL_RE.search(text or "")
    )
    has_positive_double_negation = bool(
        re.search(
            r"\b(?:jamais(?:\s+[ée]t[ée])?|n[’']ai jamais(?:\s+[ée]t[ée])?|"
            r"ne suis pas|pas(?:\s+du tout|\s+vraiment|\s+[ée]t[ée])?)"
            r"\s+d[ée][çc]u(?:e|s|es)?",
            text or "",
            re.IGNORECASE,
        )
    )

    if (
        rating_value is not None
        and rating_value >= 3
        and label in {"Négatif", "Neutre"}
        and has_positive_double_negation
        and not has_strong_negative_signal
    ):
        return "Positif", max(score, 0.55)

    if (
        rating_value is not None
        and rating_value >= 4
        and label in {"Négatif", "Positif"}
        and has_mixed_positive_signal
    ):
        return "Positif", max(score, 0.60)

    if (
        rating_value is not None
        and rating_value >= 4
        and label in {"Négatif", "Positif"}
        and has_resolved_positive_signal
        and not has_strong_negative_signal
    ):
        return "Positif", max(score, 0.60)

    if (
        rating_value is not None
        and rating_value >= 4
        and label in {"Négatif", "Positif"}
        and has_strong_positive_signal
        and not has_strong_negative_signal
        and score < 0.75
    ):
        return "Positif", max(score, 0.55)

    if rating_value is not None and rating_value <= 2 and label == "Positif":
        return "Négatif", max(score, 0.55)

    if has_strong_negative_signal and label == "Positif":
        return "Négatif", max(score, 0.55)

    if has_negative_signal and label == "Positif" and score < 0.75:
        return "Négatif", max(score, 0.55)

    if has_negative_signal and label == "Neutre" and rating_value is not None and rating_value <= 3:
        return "Négatif", max(score, 0.50)

    if score < 0.45:
        return "Neutre", score

    return label, score


def get_sentiment(text, rating=None):
    """
    Analyse le sentiment en renvoyant une étiquette parmi
    ['Négatif', 'Neutre', 'Positif'] et un score de confiance.
    """
    if not text or not isinstance(text, str) or not text.strip():
        rating_value = int(rating) if rating is not None else 3
        if rating_value <= 2:
            return "Négatif", 1.0
        if rating_value == 3:
            return "Neutre", 1.0
        return "Positif", 1.0

    if MODEL_LOADED and model is not None:
        try:
            features = pd.DataFrame(
                [{"verbatim": text, "rating": rating if rating is not None else 3}]
            )
            probabilities = model.predict_proba(features)[0]
            class_idx = int(np.argmax(probabilities))
            labels = ["Négatif", "Neutre", "Positif"]
            label = labels[class_idx]
            score = round(float(probabilities[class_idx]), 2)

            return apply_business_guardrails(label, score, text, rating)
        except Exception as e:
            print(f"[-] Erreur lors de la prédiction : {e}")
            return "Neutre", 0.0

    from textblob import TextBlob

    analysis = TextBlob(text)
    score = analysis.sentiment.polarity

    if score > 0.1:
        label = "Positif"
        confidence = round(score, 2)
    elif score < -0.1:
        label = "Négatif"
        confidence = round(abs(score), 2)
    else:
        label = "Neutre"
        confidence = 0.0

    return apply_business_guardrails(label, confidence, text, rating)
