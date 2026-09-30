"""Benchmark local assaini du snapshot v53, sans écriture de modèle ni MLflow.

Usage : python -m scripts.benchmark_ml_optimization
Le CSV d'entrée reste privé et ignoré par Git ; la sortie ne contient que des agrégats.
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold

from app.train_model import (
    FEEDBACK_DATASET_SOURCE,
    LABEL_TO_TARGET,
    MANUAL_DATASET_SOURCE,
    RATING_FEATURE_WEIGHT,
    TRAINING_SNAPSHOT_PATH,
    build_evaluation_keys,
    build_model,
    compute_training_dataset_hash,
    deduplicate_training_dataframe,
    split_training_dataframe,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "evidence" / "ml_optimization_summary.json"
V53_DATASET_HASH = "deb2f21da31b6c64c999fd539b79192e26d2fd1c71e820f31884294c0e9984cd"
CANDIDATES = [
    ("text_only", None),
    ("text_rating_0_10", 0.10),
    ("text_rating_0_25_v53", RATING_FEATURE_WEIGHT),
    ("text_rating_0_50", 0.50),
    ("text_rating_1_00", 1.00),
]


def load_snapshot(path):
    frame = pd.read_csv(path, encoding="utf-8-sig")
    required = {"id", "verbatim", "rating", "manual_label", "dataset_source", "sample_weight"}
    if missing := required.difference(frame.columns):
        raise ValueError(f"Colonnes manquantes : {sorted(missing)}")
    if frame[list(required)].isna().any().any():
        raise ValueError("Valeur manquante dans le snapshot")
    if not frame["manual_label"].isin(LABEL_TO_TARGET).all():
        raise ValueError("Étiquette inconnue")
    frame["target"] = frame["manual_label"].map(LABEL_TO_TARGET)
    # Le CSV rend les IDs hétérogènes sous forme de chaînes. La fonction de
    # hash v53 avait reçu les IDs manuels comme entiers avant export CSV.
    frame["id"] = frame["id"].astype(object)
    manual = frame["dataset_source"].eq(MANUAL_DATASET_SOURCE)
    if not frame.loc[manual, "id"].map(lambda value: str(value).isdigit()).all():
        raise ValueError("ID manuel non numérique : reconstruction v53 impossible")
    frame.loc[manual, "id"] = frame.loc[manual, "id"].map(int)
    if not frame["dataset_source"].isin([MANUAL_DATASET_SOURCE, FEEDBACK_DATASET_SOURCE]).all():
        raise ValueError("Source de données inconnue")
    if not frame.loc[manual, "sample_weight"].eq(1.0).all():
        raise ValueError("Poids manuel inattendu")
    if not frame.loc[~manual, "sample_weight"].eq(6.0).all():
        raise ValueError("Poids feedback inattendu")
    return frame


def candidate_model(weight):
    if weight is not None:
        return build_model(rating_weight=weight)
    # Même architecture de référence, avec la branche note retirée du
    # ColumnTransformer ; classifieur et TF-IDF restent identiques.
    model = build_model(rating_weight=RATING_FEATURE_WEIGHT)
    text_branch = model.named_steps["features"].transformers[0]
    model.named_steps["features"].transformers = [text_branch]
    model.named_steps["features"].transformer_weights = {"text": 1.0}
    return model


def metrics(y_true, y_pred):
    labels = [0, 1, 2]
    values = f1_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    return {
        "macro_f1": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1_negative": float(values[0]),
        "f1_neutral": float(values[1]),
        "f1_positive": float(values[2]),
    }


def run(dataset_path, output_path):
    raw = load_snapshot(dataset_path)
    file_sha256 = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    deduped = deduplicate_training_dataframe(raw)
    removed = int(deduped.attrs["deduplication"]["removed_rows"])
    logical_hash = compute_training_dataset_hash(deduped)
    train, test = split_training_dataframe(deduped, test_size=0.2, random_state=42)
    if set(build_evaluation_keys(train)) & set(build_evaluation_keys(test)):
        raise AssertionError("Fuite entre train et test")
    x_train = train[["verbatim", "rating"]]
    y_train = train["target"].to_numpy()
    w_train = train["sample_weight"].to_numpy()
    folds = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    rows = []
    for name, rating_weight in CANDIDATES:
        fold_metrics = []
        for fit_idx, val_idx in folds.split(x_train, y_train):
            model = candidate_model(rating_weight)
            model.fit(x_train.iloc[fit_idx], y_train[fit_idx], clf__sample_weight=w_train[fit_idx])
            prediction = model.predict(x_train.iloc[val_idx])
            fold_metrics.append(metrics(y_train[val_idx], prediction))
        means = {key: float(np.mean([fold[key] for fold in fold_metrics])) for key in fold_metrics[0]}
        rows.append({
            "name": name,
            "rating_weight": rating_weight,
            "tfidf": {"ngram_range": [1, 2], "min_df": 2, "sublinear_tf": True},
            "classifier": {"type": "LogisticRegression", "solver": "lbfgs", "max_iter": 1000, "class_weight": "balanced"},
            "cv_mean": means,
            "cv_macro_f1_std": float(np.std([fold["macro_f1"] for fold in fold_metrics])),
            "cv_fold_macro_f1": [fold["macro_f1"] for fold in fold_metrics],
        })
    ranked = sorted(rows, key=lambda row: (-row["cv_mean"]["macro_f1"], row["name"]))
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
    winner = ranked[0]
    model = candidate_model(winner["rating_weight"])
    model.fit(x_train, y_train, clf__sample_weight=w_train)
    y_test = test["target"].to_numpy()
    prediction = model.predict(test[["verbatim", "rating"]])
    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "file_sha256": file_sha256,
            "logical_sha256": logical_hash,
            "matches_v53_logical_sha256": logical_hash == V53_DATASET_HASH,
            "rows_before_deduplication": len(raw),
            "duplicates_removed": removed,
            "rows_after_deduplication": len(deduped),
            "manual_rows": int(deduped.dataset_source.eq(MANUAL_DATASET_SOURCE).sum()),
            "feedback_rows": int(deduped.dataset_source.eq(FEEDBACK_DATASET_SOURCE).sum()),
        },
        "protocol": {
            "python": sys.version.split()[0],
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "random_state": 42,
            "test_size": 0.2,
            "split": "stratified_after_global_deduplication",
            "train_rows": len(train),
            "test_rows": len(test),
            "selection": "3-fold stratified CV on training partition only; rank by mean macro-F1",
            "feedback_sample_weight": 6.0,
            "final_test_evaluations": 1,
            "test_classes": {str(label): int((y_test == label).sum()) for label in (0, 1, 2)},
        },
        "candidates": rows,
        "winner": winner["name"],
        "winner_test": {**metrics(y_test, prediction), "confusion_matrix_labels_0_1_2": confusion_matrix(y_test, prediction, labels=[0, 1, 2]).tolist()},
        "production_model_unchanged": True,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=TRAINING_SNAPSHOT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(args.dataset, args.output)
    print(json.dumps({"dataset": result["dataset"], "winner": result["winner"], "winner_test": result["winner_test"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
