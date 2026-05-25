import json
import os
import pickle
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

try:
    import mlflow
    import mlflow.sklearn
    from mlflow.client import MlflowClient
except ImportError:
    mlflow = None
    MlflowClient = None

try:
    import psycopg2
except ImportError:
    psycopg2 = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANNOTATIONS_TRAINING_PATH = PROJECT_ROOT / "annotations_training.csv"
ANNOTATIONS_PATH = PROJECT_ROOT / "annotations_manual_labels.csv"
ANNOTATIONS_COMPLETE_PATH = PROJECT_ROOT / "annotations_complete.csv"
REVIEWS_JSON_PATH = PROJECT_ROOT / "data" / "showroom_reviews.json"
MODEL_OUTPUT_PATH = PROJECT_ROOT / "app" / "models" / "sentiment_model.pkl"
RATING_FEATURE_WEIGHT = 0.25

LABEL_TO_TARGET = {
    "Négatif": 0,
    "Neutre": 1,
    "Positif": 2,
}
TARGET_TO_LABEL = {value: key for key, value in LABEL_TO_TARGET.items()}
TARGET_NAMES = [TARGET_TO_LABEL[i] for i in sorted(TARGET_TO_LABEL)]


def build_model(rating_weight=RATING_FEATURE_WEIGHT):
    """Pipeline texte + note client pour limiter les contresens métier."""
    return Pipeline(
        [
            (
                "features",
                ColumnTransformer(
                    [
                        (
                            "text",
                            TfidfVectorizer(
                                ngram_range=(1, 2),
                                min_df=2,
                                sublinear_tf=True,
                            ),
                            "verbatim",
                        ),
                        (
                            "rating",
                            OneHotEncoder(handle_unknown="ignore"),
                            ["rating"],
                        ),
                    ],
                    transformer_weights={
                        "text": 1.0,
                        "rating": rating_weight,
                    },
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    solver="lbfgs",
                    max_iter=1000,
                    class_weight="balanced",
                ),
            ),
        ]
    )


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


def apply_business_guardrails(label, score, text, rating=None):
    """Corrige les sorties manifestement risquées pour un dashboard satisfaction."""
    normalized_text = text or ""
    rating_value = int(rating) if rating is not None and not pd.isna(rating) else None
    has_negative_signal = bool(NEGATIVE_SIGNAL_RE.search(normalized_text))
    has_strong_negative_signal = bool(
        STRONG_NEGATIVE_SIGNAL_RE.search(normalized_text)
    ) and not re.search(r"\b(?:pas|plus)\s+trop\s+long", normalized_text, re.IGNORECASE)
    has_strong_positive_signal = bool(STRONG_POSITIVE_SIGNAL_RE.search(normalized_text))
    has_resolved_positive_signal = bool(
        RESOLVED_POSITIVE_SIGNAL_RE.search(normalized_text)
    )
    has_mixed_positive_signal = bool(
        MIXED_POSITIVE_SIGNAL_RE.search(normalized_text)
    )
    has_positive_double_negation = bool(
        re.search(
            r"\b(?:jamais(?:\s+[ée]t[ée])?|n[’']ai jamais(?:\s+[ée]t[ée])?|"
            r"ne suis pas|pas(?:\s+du tout|\s+vraiment|\s+[ée]t[ée])?)"
            r"\s+d[ée][çc]u(?:e|s|es)?",
            normalized_text,
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


def load_annotations(path=ANNOTATIONS_PATH):
    if not path.exists():
        raise FileNotFoundError(f"Fichier d'annotations introuvable: {path}")

    annotations = pd.read_csv(path, encoding="utf-8-sig")
    required_columns = {"id", "manual_label"}
    missing_columns = required_columns.difference(annotations.columns)
    if missing_columns:
        raise ValueError(
            "Colonnes manquantes dans annotations_manual_labels.csv: "
            f"{sorted(missing_columns)}"
        )

    columns_to_keep = ["id", "manual_label"]
    if "justification_courte" in annotations.columns:
        columns_to_keep.append("justification_courte")

    annotations = annotations[columns_to_keep].copy()
    annotations["id"] = pd.to_numeric(annotations["id"], errors="raise").astype(int)
    annotations["manual_label"] = annotations["manual_label"].astype(str).str.strip()

    unknown_labels = sorted(set(annotations["manual_label"]) - set(LABEL_TO_TARGET))
    if unknown_labels:
        raise ValueError(f"Labels manuels inconnus: {unknown_labels}")

    return annotations


def load_complete_annotations(path):
    if not path.exists():
        raise FileNotFoundError(f"Fichier d'annotations complet introuvable: {path}")

    annotations = pd.read_csv(path, encoding="utf-8-sig")
    required_columns = {"id", "manual_label", "verbatim"}
    missing_columns = required_columns.difference(annotations.columns)
    if missing_columns:
        raise ValueError(
            f"Colonnes manquantes dans {path.name}: "
            f"{sorted(missing_columns)}"
        )

    annotations = annotations.copy()
    annotations["id"] = pd.to_numeric(annotations["id"], errors="raise").astype(int)
    annotations["manual_label"] = annotations["manual_label"].astype(str).str.strip()

    unknown_labels = sorted(set(annotations["manual_label"]) - set(LABEL_TO_TARGET))
    if unknown_labels:
        raise ValueError(f"Labels manuels inconnus: {unknown_labels}")

    return annotations


def load_reviews_from_json(path=REVIEWS_JSON_PATH):
    if not path.exists():
        raise FileNotFoundError(f"Fichier JSON introuvable: {path}")

    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    reviews = payload.get("reviews", [])
    rows = []
    for source_id, review in enumerate(reviews):
        rows.append(
            {
                "id": source_id,
                "verbatim": review.get("verbatim", ""),
                "rating": review.get("rating"),
                "author_name": review.get("author"),
                "review_date": review.get("date"),
            }
        )

    return pd.DataFrame(rows)


def validate_annotation_alignment(df, mismatch_threshold=0.10):
    if "justification_courte" not in df.columns or "rating" not in df.columns:
        return

    checked_count = 0
    mismatches = []
    for row in df.itertuples(index=False):
        match = re.search(
            r"note\s*(\d)\s*/\s*5",
            str(row.justification_courte),
            flags=re.IGNORECASE,
        )
        if not match or pd.isna(row.rating):
            continue

        checked_count += 1
        annotated_rating = int(match.group(1))
        source_rating = int(row.rating)
        if annotated_rating != source_rating:
            mismatches.append((int(row.id), annotated_rating, source_rating))

    if not checked_count:
        return

    mismatch_ratio = len(mismatches) / checked_count
    if mismatch_ratio <= mismatch_threshold:
        return

    examples = ", ".join(
        f"id={source_id} annotation_note={annotation_rating}/5 json_rating={json_rating}/5"
        for source_id, annotation_rating, json_rating in mismatches[:10]
    )
    raise ValueError(
        "Les annotations ne semblent pas correspondre au JSON actuellement chargé. "
        f"{len(mismatches)}/{checked_count} notes mentionnées dans les justifications "
        f"ne correspondent pas au rating joint par id ({mismatch_ratio:.1%}). "
        f"Exemples: {examples}. "
        "Il faut réutiliser le fichier source exact annoté, ou enrichir le CSV "
        "d'annotations avec un identifiant stable/verbatim pour permettre une jointure fiable."
    )


def load_reviews_from_database():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 n'est pas installé dans cet environnement.")

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres_db"),
        database=os.getenv("DB_NAME", "satisfaction_client"),
        user=os.getenv("DB_USER", "admin"),
        password=os.getenv("DB_PASSWORD", "password123"),
    )
    try:
        # Les annotations du CSV sont indexées de 0 à 1199, comme l'ordre du JSON.
        # En base, review_id est SERIAL et démarre à 1 après l'ETL.
        return pd.read_sql(
            """
            SELECT
                review_id - 1 AS id,
                verbatim,
                rating,
                author_name,
                review_date
            FROM fact_reviews
            ORDER BY review_id;
            """,
            conn,
        )
    finally:
        conn.close()


def load_reviews_source():
    try:
        reviews = load_reviews_from_json()
        print(f"[+] Verbatims chargés depuis {REVIEWS_JSON_PATH} ({len(reviews)} lignes).")
        return reviews
    except FileNotFoundError as json_error:
        print(f"[-] {json_error}")
        print("[*] Tentative de chargement depuis PostgreSQL...")
        reviews = load_reviews_from_database()
        print(f"[+] Verbatims chargés depuis PostgreSQL ({len(reviews)} lignes).")
        return reviews


def build_annotated_dataframe():
    for annotations_path in (ANNOTATIONS_TRAINING_PATH, ANNOTATIONS_COMPLETE_PATH):
        if not annotations_path.exists():
            continue

        df = load_complete_annotations(annotations_path)
        df["verbatim"] = df["verbatim"].fillna("").astype(str).str.strip()
        df["target"] = df["manual_label"].map(LABEL_TO_TARGET)

        print(
            "[+] Annotations complètes chargées depuis "
            f"{annotations_path} ({len(df)} lignes)."
        )
        print("[+] Distribution ground truth complète:")
        print(df["manual_label"].value_counts().reindex(TARGET_NAMES, fill_value=0))

        return df

    annotations = load_annotations()
    reviews = load_reviews_source()

    df = annotations.merge(reviews, on="id", how="left", validate="one_to_one")
    missing_reviews = df["verbatim"].isna().sum()
    if missing_reviews:
        missing_ids = df.loc[df["verbatim"].isna(), "id"].head(10).tolist()
        raise ValueError(
            f"{missing_reviews} annotation(s) sans verbatim source. "
            f"Exemples d'id: {missing_ids}"
        )

    df["verbatim"] = df["verbatim"].fillna("").astype(str).str.strip()
    df["target"] = df["manual_label"].map(LABEL_TO_TARGET)
    validate_annotation_alignment(df)

    print(f"[+] Annotations jointes: {len(annotations)} lignes.")
    print("[+] Distribution ground truth complète:")
    print(df["manual_label"].value_counts().reindex(TARGET_NAMES, fill_value=0))

    return df


def build_training_dataframe(annotated_df):
    df = annotated_df.copy()

    empty_verbatims = (df["verbatim"] == "").sum()
    if empty_verbatims:
        print(
            "[!] "
            f"{empty_verbatims} annotation(s) ont un verbatim vide et sont ignorées "
            "pour l'entraînement."
        )
        df = df[df["verbatim"] != ""].copy()

    print(f"[+] Lignes utilisées pour l'entraînement: {len(df)} lignes.")
    print("[+] Distribution utilisée pour l'entraînement:")
    print(df["manual_label"].value_counts().reindex(TARGET_NAMES, fill_value=0))

    return df


def print_evaluation_metrics(model, x_test, y_test):
    y_pred = model.predict(x_test)

    print("\n=== Métriques d'évaluation sur le jeu de test ===")
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print(
        classification_report(
            y_test,
            y_pred,
            labels=sorted(TARGET_TO_LABEL),
            target_names=TARGET_NAMES,
            digits=4,
            zero_division=0,
        )
    )


def serialize_model(model, output_path=MODEL_OUTPUT_PATH):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as file:
        pickle.dump(model, file)
    print(f"[+] Modèle sérialisé localement: {output_path}")


def log_model_to_mlflow(model, accuracy):
    if mlflow is None or MlflowClient is None:
        raise RuntimeError("mlflow n'est pas installé dans cet environnement.")

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))

    with mlflow.start_run():
        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_param("rating_feature_weight", RATING_FEATURE_WEIGHT)
        model_info = mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="sentiment_model",
            registered_model_name="sentiment_model",
        )

        client = MlflowClient()
        client.set_registered_model_alias(
            name="sentiment_model",
            alias="production",
            version=model_info.registered_model_version,
        )

        print(
            "[+] Modèle déployé sur MLflow "
            f"(v{model_info.registered_model_version}, alias production)."
        )


def synchronize_database_predictions(model):
    if psycopg2 is None:
        raise RuntimeError("psycopg2 n'est pas installé dans cet environnement.")

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres_db"),
        database=os.getenv("DB_NAME", "satisfaction_client"),
        user=os.getenv("DB_USER", "admin"),
        password=os.getenv("DB_PASSWORD", "password123"),
    )

    try:
        cursor = conn.cursor()

        cursor.execute("SELECT review_id, rating, verbatim FROM fact_reviews")
        rows = cursor.fetchall()

        predicted_count = 0
        for review_id, rating, verbatim in rows:
            if not verbatim or not isinstance(verbatim, str) or not verbatim.strip():
                rating_value = int(rating) if rating is not None else 3
                if rating_value <= 2:
                    label = "Négatif"
                elif rating_value == 3:
                    label = "Neutre"
                else:
                    label = "Positif"

                cursor.execute(
                    """
                    UPDATE fact_reviews
                    SET sentiment_label = %s, sentiment_score = %s
                    WHERE review_id = %s
                    """,
                    (label, 1.0, review_id),
                )
                predicted_count += 1
                continue

            features = pd.DataFrame([{"verbatim": verbatim, "rating": rating}])
            probabilities = model.predict_proba(features)[0]
            class_idx = int(np.argmax(probabilities))
            label = TARGET_TO_LABEL[class_idx]
            score = round(float(probabilities[class_idx]), 2)
            label, score = apply_business_guardrails(label, score, verbatim, rating)

            cursor.execute(
                """
                UPDATE fact_reviews
                SET sentiment_label = %s, sentiment_score = %s
                WHERE review_id = %s
                """,
                (label, score, review_id),
            )
            predicted_count += 1

        conn.commit()
        cursor.close()
        print(f"[+] Base synchronisée: {predicted_count} avis prédits par le modèle.")
    finally:
        conn.close()


def train_and_log_model(test_size=0.2, random_state=42):
    print("[*] Démarrage de l'entraînement depuis annotations_manual_labels.csv...")
    print(f"[*] Pondération de la note client: {RATING_FEATURE_WEIGHT}")

    annotated_df = build_annotated_dataframe()
    df = build_training_dataframe(annotated_df)
    feature_columns = ["verbatim", "rating"]
    x_train, x_test, y_train, y_test = train_test_split(
        df[feature_columns],
        df["target"],
        test_size=test_size,
        random_state=random_state,
        stratify=df["target"],
    )

    evaluation_model = build_model()
    evaluation_model.fit(x_train, y_train)

    y_pred = evaluation_model.predict(x_test)
    accuracy = accuracy_score(y_test, y_pred)
    print_evaluation_metrics(evaluation_model, x_test, y_test)

    final_model = build_model()
    final_model.fit(df[feature_columns], df["target"])
    print("[+] Modèle final réentraîné sur 100% des verbatims annotés non vides.")

    serialize_model(final_model)

    try:
        log_model_to_mlflow(final_model, accuracy)
    except Exception as exc:
        print(f"[-] MLflow indisponible ou non configuré: {exc}")
        print("[*] Le modèle local sérialisé reste disponible.")

    try:
        synchronize_database_predictions(final_model)
    except Exception as exc:
        print(f"[-] Synchronisation PostgreSQL ignorée: {exc}")


if __name__ == "__main__":
    train_and_log_model()
