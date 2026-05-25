import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from train_model import (
    TARGET_NAMES,
    TARGET_TO_LABEL,
    apply_business_guardrails,
    build_annotated_dataframe,
    build_training_dataframe,
)

try:
    import psycopg2
except ImportError:
    psycopg2 = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "external" / "sentiment_mode_comparison.csv"


def build_text_rating_model(rating_weight=1.0):
    transformer_weights = None
    if rating_weight != 1.0:
        transformer_weights = {"text": 1.0, "rating": rating_weight}

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
                    transformer_weights=transformer_weights,
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


def build_text_only_model():
    return Pipeline(
        [
            (
                "text",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=2,
                    sublinear_tf=True,
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


def rating_fallback_label(rating):
    rating_value = int(rating) if pd.notna(rating) else 3
    if rating_value <= 2:
        return TARGET_TO_LABEL[0], 1.0
    if rating_value == 3:
        return TARGET_TO_LABEL[1], 1.0
    return TARGET_TO_LABEL[2], 1.0


def fit_models(training_df, rating_weight):
    text_rating_model = build_text_rating_model()
    weak_rating_model = build_text_rating_model(rating_weight=rating_weight)
    text_only_model = build_text_only_model()

    feature_columns = ["verbatim", "rating"]
    text_rating_model.fit(training_df[feature_columns], training_df["target"])
    weak_rating_model.fit(training_df[feature_columns], training_df["target"])
    text_only_model.fit(training_df["verbatim"], training_df["target"])

    return {
        "text_rating": text_rating_model,
        "weak_rating": weak_rating_model,
        "text_only": text_only_model,
    }


def print_holdout_metrics(training_df, rating_weight, test_size=0.2, random_state=42):
    feature_columns = ["verbatim", "rating"]
    x_train, x_test, y_train, y_test = train_test_split(
        training_df[feature_columns],
        training_df["target"],
        test_size=test_size,
        random_state=random_state,
        stratify=training_df["target"],
    )

    experiments = [
        ("Mode actuel: texte + note", build_text_rating_model(), x_train, x_test),
        (
            f"Mode note faible: texte + note x{rating_weight}",
            build_text_rating_model(rating_weight=rating_weight),
            x_train,
            x_test,
        ),
        (
            "Mode texte seul",
            build_text_only_model(),
            x_train["verbatim"],
            x_test["verbatim"],
        ),
    ]

    print("\n=== Evaluation 80/20 sur annotations_training.csv ===")
    for title, model, train_features, test_features in experiments:
        model.fit(train_features, y_train)
        y_pred = model.predict(test_features)
        print(f"\n--- {title} ---")
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


def load_reviews_from_database():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is not installed in this environment.")

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres_db"),
        database=os.getenv("DB_NAME", "satisfaction_client"),
        user=os.getenv("DB_USER", "admin"),
        password=os.getenv("DB_PASSWORD", "password123"),
    )
    try:
        return pd.read_sql(
            """
            SELECT
                review_id,
                rating,
                sentiment_label AS dashboard_label,
                sentiment_score AS dashboard_score,
                verbatim
            FROM fact_reviews
            ORDER BY review_id;
            """,
            conn,
        )
    finally:
        conn.close()


def load_reviews_from_json(json_path):
    import json

    with Path(json_path).open("r", encoding="utf-8") as file:
        payload = json.load(file)

    rows = []
    for review_id, review in enumerate(payload.get("reviews", []), start=1):
        rows.append(
            {
                "review_id": review_id,
                "rating": review.get("rating", 3),
                "dashboard_label": "",
                "dashboard_score": "",
                "verbatim": review.get("verbatim", ""),
            }
        )
    return pd.DataFrame(rows)


def load_reviews_from_csv(csv_path):
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    if "sentiment_label" in df.columns and "dashboard_label" not in df.columns:
        df = df.rename(columns={"sentiment_label": "dashboard_label"})
    if "sentiment_score" in df.columns and "dashboard_score" not in df.columns:
        df = df.rename(columns={"sentiment_score": "dashboard_score"})
    return df


def load_comparison_source(args):
    if args.source == "db":
        return load_reviews_from_database()
    if args.source == "json":
        if not args.json_path:
            raise ValueError("--json-path is required with --source json")
        return load_reviews_from_json(args.json_path)
    if args.source == "csv":
        if not args.csv_path:
            raise ValueError("--csv-path is required with --source csv")
        return load_reviews_from_csv(args.csv_path)
    raise ValueError(f"Unknown source: {args.source}")


def predict_label_and_score(model, features):
    probabilities = model.predict_proba(features)[0]
    probability_index = int(np.argmax(probabilities))
    target = int(model.classes_[probability_index])
    label = TARGET_TO_LABEL[target]
    score = round(float(probabilities[probability_index]), 2)
    return label, score


def predict_for_reviews(reviews_df, models):
    rows = reviews_df.copy()
    rows["verbatim"] = rows["verbatim"].fillna("").astype(str).str.strip()
    rows["rating"] = pd.to_numeric(rows["rating"], errors="coerce").fillna(3).astype(int)

    for prefix in ("text_rating", "weak_rating", "text_only"):
        rows[f"{prefix}_label"] = ""
        rows[f"{prefix}_score"] = 0.0

    for idx, row in rows.iterrows():
        verbatim = row["verbatim"]
        rating = int(row["rating"])

        if not verbatim:
            label, score = rating_fallback_label(rating)
            rows.at[idx, "text_rating_label"] = label
            rows.at[idx, "text_rating_score"] = score
            rows.at[idx, "weak_rating_label"] = label
            rows.at[idx, "weak_rating_score"] = score
            rows.at[idx, "text_only_label"] = "Texte vide"
            rows.at[idx, "text_only_score"] = 0.0
            continue

        rating_features = pd.DataFrame([{"verbatim": verbatim, "rating": rating}])
        for prefix in ("text_rating", "weak_rating"):
            label, score = predict_label_and_score(models[prefix], rating_features)
            label, score = apply_business_guardrails(label, score, verbatim, rating)
            rows.at[idx, f"{prefix}_label"] = label
            rows.at[idx, f"{prefix}_score"] = score

        label, score = predict_label_and_score(models["text_only"], [verbatim])
        label, score = apply_business_guardrails(label, score, verbatim, None)
        rows.at[idx, "text_only_label"] = label
        rows.at[idx, "text_only_score"] = score

    rows["current_vs_text_only_diff"] = (
        rows["text_rating_label"] != rows["text_only_label"]
    ) & (rows["text_only_label"] != "Texte vide")
    rows["weak_vs_text_only_diff"] = (
        rows["weak_rating_label"] != rows["text_only_label"]
    ) & (rows["text_only_label"] != "Texte vide")
    rows["dashboard_vs_text_only_diff"] = (
        rows.get("dashboard_label", "") != rows["text_only_label"]
    ) & (rows["text_only_label"] != "Texte vide")

    return rows


def print_external_summary(comparison_df):
    non_empty = comparison_df[comparison_df["text_only_label"] != "Texte vide"]
    print("\n=== Comparaison sur la source externe ===")
    print(f"Lignes totales: {len(comparison_df)}")
    print(f"Verbatims non vides compares: {len(non_empty)}")
    print(f"Verbatims vides exclus du texte seul: {len(comparison_df) - len(non_empty)}")

    for column in (
        "dashboard_label",
        "text_rating_label",
        "weak_rating_label",
        "text_only_label",
    ):
        if column in comparison_df.columns:
            print(f"\nDistribution {column}:")
            print(comparison_df[column].value_counts(dropna=False).to_string())

    if len(non_empty):
        agreement = (
            non_empty["text_rating_label"] == non_empty["text_only_label"]
        ).mean()
        weak_agreement = (
            non_empty["weak_rating_label"] == non_empty["text_only_label"]
        ).mean()
        print(f"\nAccord mode actuel vs texte seul: {agreement:.1%}")
        print(f"Accord note faible vs texte seul: {weak_agreement:.1%}")

        print("\nDesaccords mode actuel vs texte seul par note:")
        disagreements = non_empty[non_empty["current_vs_text_only_diff"]]
        if disagreements.empty:
            print("Aucun desaccord.")
        else:
            print(disagreements["rating"].value_counts().sort_index().to_string())

            preview_columns = [
                "review_id",
                "rating",
                "text_rating_label",
                "weak_rating_label",
                "text_only_label",
                "verbatim",
            ]
            print("\nExemples de desaccords:")
            for row in disagreements[preview_columns].head(15).itertuples(index=False):
                text = str(row.verbatim).replace("\n", " ")[:180]
                print(
                    f"- id={row.review_id} note={row.rating} "
                    f"actuel={row.text_rating_label} note_faible={row.weak_rating_label} "
                    f"texte_seul={row.text_only_label} | {text}"
                )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Compare the current sentiment approach against text-only and "
            "reduced-rating variants without updating MLflow or PostgreSQL."
        )
    )
    parser.add_argument(
        "--source",
        choices=["db", "json", "csv"],
        default="db",
        help="Reviews to compare. Use db after loading an external company in the dashboard.",
    )
    parser.add_argument("--json-path")
    parser.add_argument("--csv-path")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--rating-weight", type=float, default=0.25)
    args = parser.parse_args()

    print("[*] Loading annotated training data...")
    annotated_df = build_annotated_dataframe()
    training_df = build_training_dataframe(annotated_df)

    print_holdout_metrics(training_df, rating_weight=args.rating_weight)

    print("\n[*] Training temporary comparison models on 100% of annotated non-empty text...")
    models = fit_models(training_df, rating_weight=args.rating_weight)

    print(f"[*] Loading comparison source: {args.source}")
    reviews_df = load_comparison_source(args)
    comparison_df = predict_for_reviews(reviews_df, models)
    print_external_summary(comparison_df)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    comparison_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\n[+] CSV de comparaison genere: {output_path}")


if __name__ == "__main__":
    main()
