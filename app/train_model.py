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
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANNOTATIONS_TRAINING_PATH = PROJECT_ROOT / "annotations_training.csv"
ANNOTATIONS_PATH = PROJECT_ROOT / "annotations_manual_labels.csv"
ANNOTATIONS_COMPLETE_PATH = PROJECT_ROOT / "annotations_complete.csv"
REVIEWS_JSON_PATH = PROJECT_ROOT / "data" / "showroom_reviews.json"
MODEL_OUTPUT_PATH = PROJECT_ROOT / "app" / "models" / "sentiment_model.pkl"
TRAINING_SNAPSHOT_PATH = (
    PROJECT_ROOT / "data" / "training" / "sentiment_training_dataset.csv"
)
RATING_FEATURE_WEIGHT = 0.25
DEFAULT_FEEDBACK_SAMPLE_WEIGHT = 6.0

LABEL_TO_TARGET = {
    "Négatif": 0,
    "Neutre": 1,
    "Positif": 2,
}
TARGET_TO_LABEL = {value: key for key, value in LABEL_TO_TARGET.items()}
TARGET_NAMES = [TARGET_TO_LABEL[i] for i in sorted(TARGET_TO_LABEL)]
MANUAL_DATASET_SOURCE = "manual_annotations"
FEEDBACK_DATASET_SOURCE = "review_feedback"


def get_feedback_sample_weight():
    raw_value = os.getenv(
        "FEEDBACK_SAMPLE_WEIGHT", str(DEFAULT_FEEDBACK_SAMPLE_WEIGHT)
    )
    try:
        weight = float(raw_value)
    except ValueError:
        print(
            "[!] FEEDBACK_SAMPLE_WEIGHT invalide "
            f"({raw_value!r}), valeur par défaut utilisée: "
            f"{DEFAULT_FEEDBACK_SAMPLE_WEIGHT}."
        )
        return DEFAULT_FEEDBACK_SAMPLE_WEIGHT

    if weight < 1.0:
        print(
            "[!] FEEDBACK_SAMPLE_WEIGHT doit être >= 1.0, "
            f"valeur par défaut utilisée: {DEFAULT_FEEDBACK_SAMPLE_WEIGHT}."
        )
        return DEFAULT_FEEDBACK_SAMPLE_WEIGHT

    return weight


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


def get_database_connection():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 n'est pas installé dans cet environnement.")

    return psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres_db"),
        database=os.getenv("DB_NAME", "satisfaction_client"),
        user=os.getenv("DB_USER", "admin"),
        password=os.getenv("DB_PASSWORD", "password123"),
    )


def load_reviews_from_database():
    conn = get_database_connection()
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


def normalize_verbatim_for_dedupe(value):
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def ensure_training_metadata_columns(df, dataset_source):
    df = df.copy()
    defaults = {
        "rating": np.nan,
        "author_name": pd.NA,
        "review_date": pd.NA,
        "company_name": pd.NA,
        "source_run_id": pd.NA,
        "source_review_id": pd.NA,
        "predicted_label": pd.NA,
        "feedback_comment": pd.NA,
        "feedback_updated_at": pd.NA,
    }
    for column, default_value in defaults.items():
        if column not in df.columns:
            df[column] = default_value

    df["dataset_source"] = dataset_source
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    return df


def load_feedback_annotations_from_database():
    try:
        conn = get_database_connection()
    except Exception as exc:
        print(f"[-] Corrections humaines indisponibles: {exc}")
        return pd.DataFrame()

    try:
        query = """
        SELECT
            rf.feedback_id,
            rf.review_id AS source_review_id,
            r.run_id AS source_run_id,
            c.company_name,
            c.trustpilot_slug,
            r.rating,
            r.author_name,
            COALESCE(r.review_date::text, r.raw_date) AS review_date,
            r.verbatim,
            rf.predicted_label,
            rf.corrected_label AS manual_label,
            rf.comment AS feedback_comment,
            rf.updated_at AS feedback_updated_at
        FROM review_feedback rf
        JOIN reviews r ON r.review_id = rf.review_id
        JOIN analysis_runs ar ON ar.run_id = r.run_id
        JOIN companies c ON c.company_id = r.company_id
        ORDER BY rf.updated_at, rf.feedback_id;
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            feedback = pd.DataFrame(cursor.fetchall())
    except Exception as exc:
        print(f"[-] Chargement des corrections humaines ignoré: {exc}")
        return pd.DataFrame()
    finally:
        conn.close()

    if feedback.empty:
        print("[*] Aucune correction humaine trouvée en base.")
        return feedback

    feedback["manual_label"] = feedback["manual_label"].astype(str).str.strip()
    unknown_labels = sorted(set(feedback["manual_label"]) - set(LABEL_TO_TARGET))
    if unknown_labels:
        raise ValueError(f"Labels de correction inconnus: {unknown_labels}")

    feedback["verbatim"] = feedback["verbatim"].fillna("").astype(str).str.strip()
    empty_verbatims = (feedback["verbatim"] == "").sum()
    if empty_verbatims:
        print(
            "[!] "
            f"{empty_verbatims} correction(s) ont un verbatim vide et sont ignorées."
        )
        feedback = feedback[feedback["verbatim"] != ""].copy()

    if feedback.empty:
        print("[*] Aucune correction humaine exploitable après nettoyage.")
        return feedback

    feedback["rating"] = pd.to_numeric(feedback["rating"], errors="coerce")
    feedback["target"] = feedback["manual_label"].map(LABEL_TO_TARGET)
    feedback["id"] = "feedback:" + feedback["source_review_id"].astype(str)
    feedback = ensure_training_metadata_columns(feedback, FEEDBACK_DATASET_SOURCE)

    before_deduplication = len(feedback)
    feedback["_dedupe_key"] = (
        feedback["verbatim"].map(normalize_verbatim_for_dedupe)
        + "|"
        + feedback["rating"].fillna("NA").astype(str)
    )
    feedback = (
        feedback.sort_values("feedback_updated_at")
        .drop_duplicates(subset=["_dedupe_key"], keep="last")
        .drop(columns=["_dedupe_key"])
        .copy()
    )
    deduplicated_count = before_deduplication - len(feedback)
    if deduplicated_count:
        print(
            "[!] "
            f"{deduplicated_count} correction(s) doublon ont été ignorées "
            "pour ne pas surpondérer les mêmes avis."
        )

    print(f"[+] Corrections humaines chargées depuis PostgreSQL: {len(feedback)} lignes.")
    print("[+] Distribution corrections humaines:")
    print(feedback["manual_label"].value_counts().reindex(TARGET_NAMES, fill_value=0))

    return feedback


def build_annotated_dataframe():
    for annotations_path in (ANNOTATIONS_TRAINING_PATH, ANNOTATIONS_COMPLETE_PATH):
        if not annotations_path.exists():
            continue

        df = load_complete_annotations(annotations_path)
        df["verbatim"] = df["verbatim"].fillna("").astype(str).str.strip()
        df["target"] = df["manual_label"].map(LABEL_TO_TARGET)
        df = ensure_training_metadata_columns(df, MANUAL_DATASET_SOURCE)

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
    df = ensure_training_metadata_columns(df, MANUAL_DATASET_SOURCE)
    validate_annotation_alignment(df)

    print(f"[+] Annotations jointes: {len(annotations)} lignes.")
    print("[+] Distribution ground truth complète:")
    print(df["manual_label"].value_counts().reindex(TARGET_NAMES, fill_value=0))

    return df


def build_combined_annotated_dataframe(include_feedback=True):
    manual_df = build_annotated_dataframe()

    frames = [manual_df]
    if include_feedback:
        feedback_df = load_feedback_annotations_from_database()
        if not feedback_df.empty:
            frames.append(feedback_df)

    frames_for_concat = [frame.dropna(axis=1, how="all") for frame in frames]
    combined_df = pd.concat(frames_for_concat, ignore_index=True, sort=False)
    combined_df["manual_label"] = combined_df["manual_label"].astype(str).str.strip()
    combined_df["target"] = combined_df["manual_label"].map(LABEL_TO_TARGET)
    combined_df = ensure_training_metadata_columns(
        combined_df,
        dataset_source=combined_df.get("dataset_source", MANUAL_DATASET_SOURCE),
    )

    print("[+] Sources du dataset combiné:")
    print(combined_df["dataset_source"].value_counts())
    print("[+] Distribution ground truth combinée:")
    print(combined_df["manual_label"].value_counts().reindex(TARGET_NAMES, fill_value=0))

    return combined_df


def write_training_dataset_snapshot(df, output_path=TRAINING_SNAPSHOT_PATH):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_columns = [
        "id",
        "dataset_source",
        "company_name",
        "source_run_id",
        "source_review_id",
        "rating",
        "manual_label",
        "predicted_label",
        "feedback_comment",
        "feedback_updated_at",
        "sample_weight",
        "verbatim",
    ]
    available_columns = [column for column in snapshot_columns if column in df.columns]
    df[available_columns].to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"[+] Snapshot dataset d'entraînement: {output_path}")


def apply_sample_weights(df, feedback_sample_weight):
    df = df.copy()
    df["sample_weight"] = 1.0

    if "dataset_source" not in df.columns:
        return df

    feedback_mask = df["dataset_source"].fillna("") == FEEDBACK_DATASET_SOURCE
    df.loc[feedback_mask, "sample_weight"] = feedback_sample_weight

    feedback_rows = int(feedback_mask.sum())
    effective_feedback_rows = float(df.loc[feedback_mask, "sample_weight"].sum())
    effective_total_rows = float(df["sample_weight"].sum())

    if feedback_rows:
        print(
            "[+] Pondération corrections humaines: "
            f"x{feedback_sample_weight:g} "
            f"({feedback_rows} ligne(s), poids effectif {effective_feedback_rows:g})."
        )
    else:
        print("[*] Aucune correction humaine à pondérer.")
    print(f"[+] Poids effectif total d'entraînement: {effective_total_rows:g}.")

    return df


def build_training_dataframe(annotated_df, feedback_sample_weight=None):
    df = annotated_df.copy()
    if feedback_sample_weight is None:
        feedback_sample_weight = get_feedback_sample_weight()

    empty_verbatims = (df["verbatim"] == "").sum()
    if empty_verbatims:
        print(
            "[!] "
            f"{empty_verbatims} annotation(s) ont un verbatim vide et sont ignorées "
            "pour l'entraînement."
        )
        df = df[df["verbatim"] != ""].copy()

    print(f"[+] Lignes utilisées pour l'entraînement: {len(df)} lignes.")
    if "dataset_source" in df.columns:
        print("[+] Lignes utilisées par source:")
        print(df["dataset_source"].value_counts())
    print("[+] Distribution utilisée pour l'entraînement:")
    print(df["manual_label"].value_counts().reindex(TARGET_NAMES, fill_value=0))
    df = apply_sample_weights(df, feedback_sample_weight)
    write_training_dataset_snapshot(df)

    return df


def print_evaluation_metrics(model, x_test, y_test, source_test=None):
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

    if source_test is None:
        return

    source_series = pd.Series(source_test, index=y_test.index).fillna("unknown")
    y_pred_series = pd.Series(y_pred, index=y_test.index)
    print("\n=== Métriques par source du jeu de test ===")
    for source_name in sorted(source_series.unique()):
        source_mask = source_series == source_name
        source_count = int(source_mask.sum())
        if source_count == 0:
            continue

        print(f"\n--- Source: {source_name} ({source_count} lignes test) ---")
        print(
            "Accuracy: "
            f"{accuracy_score(y_test[source_mask], y_pred_series[source_mask]):.4f}"
        )
        print(
            classification_report(
                y_test[source_mask],
                y_pred_series[source_mask],
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


def log_model_to_mlflow(model, accuracy, training_metadata=None):
    if mlflow is None or MlflowClient is None:
        raise RuntimeError("mlflow n'est pas installé dans cet environnement.")

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))

    with mlflow.start_run():
        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_param("rating_feature_weight", RATING_FEATURE_WEIGHT)
        if training_metadata:
            for key, value in training_metadata.items():
                if isinstance(value, (int, float, np.integer, np.floating)):
                    mlflow.log_metric(key, float(value))
                else:
                    mlflow.log_param(key, value)

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
    conn = get_database_connection()

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
    print(
        "[*] Démarrage de l'entraînement depuis annotations manuelles "
        "+ corrections humaines..."
    )
    print(f"[*] Pondération de la note client: {RATING_FEATURE_WEIGHT}")
    feedback_sample_weight = get_feedback_sample_weight()
    print(
        "[*] Pondération des corrections humaines: "
        f"x{feedback_sample_weight:g}"
    )

    annotated_df = build_combined_annotated_dataframe(include_feedback=True)
    df = build_training_dataframe(
        annotated_df, feedback_sample_weight=feedback_sample_weight
    )
    feature_columns = ["verbatim", "rating"]
    source_series = df["dataset_source"].fillna("unknown")
    sample_weights = df["sample_weight"]
    (
        x_train,
        x_test,
        y_train,
        y_test,
        sample_weight_train,
        _sample_weight_test,
        _source_train,
        source_test,
    ) = train_test_split(
        df[feature_columns],
        df["target"],
        sample_weights,
        source_series,
        test_size=test_size,
        random_state=random_state,
        stratify=df["target"],
    )

    evaluation_model = build_model()
    evaluation_model.fit(x_train, y_train, clf__sample_weight=sample_weight_train)

    y_pred = evaluation_model.predict(x_test)
    accuracy = accuracy_score(y_test, y_pred)
    print_evaluation_metrics(evaluation_model, x_test, y_test, source_test)

    final_model = build_model()
    final_model.fit(
        df[feature_columns],
        df["target"],
        clf__sample_weight=sample_weights,
    )
    print("[+] Modèle final réentraîné sur 100% des verbatims annotés non vides.")

    serialize_model(final_model)

    source_counts = df["dataset_source"].value_counts()
    training_metadata = {
        "training_rows": int(len(df)),
        "training_manual_rows": int(source_counts.get(MANUAL_DATASET_SOURCE, 0)),
        "training_feedback_rows": int(source_counts.get(FEEDBACK_DATASET_SOURCE, 0)),
        "feedback_sample_weight": float(feedback_sample_weight),
        "training_effective_rows": float(df["sample_weight"].sum()),
        "training_sources": ",".join(sorted(source_counts.index.astype(str))),
    }

    try:
        log_model_to_mlflow(final_model, accuracy, training_metadata)
    except Exception as exc:
        print(f"[-] MLflow indisponible ou non configuré: {exc}")
        print("[*] Le modèle local sérialisé reste disponible.")

    try:
        synchronize_database_predictions(final_model)
    except Exception as exc:
        print(f"[-] Synchronisation PostgreSQL ignorée: {exc}")


if __name__ == "__main__":
    train_and_log_model()
