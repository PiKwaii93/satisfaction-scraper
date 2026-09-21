"""Seed an empty MLflow registry from the reviewed, versioned model artifact."""

import hashlib
import os
import pickle
from pathlib import Path

import mlflow
import mlflow.sklearn
import pandas as pd
from mlflow.client import MlflowClient


MODEL_NAME = "sentiment_model"
PRODUCTION_ALIAS = "production"
MODEL_URI = f"models:/{MODEL_NAME}@{PRODUCTION_ALIAS}"
DEFAULT_MODEL_PATH = Path(__file__).resolve().parents[1] / "app/models/sentiment_model.pkl"
DEFAULT_HASH_PATH = DEFAULT_MODEL_PATH.with_suffix(".sha256")


def load_verified_model(model_path, hash_path):
    model_path = Path(model_path)
    hash_path = Path(hash_path)
    expected_hash = hash_path.read_text(encoding="ascii").split()[0].lower()
    actual_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError(f"Empreinte du modele invalide: {model_path}")
    with model_path.open("rb") as file:
        model = pickle.load(file)
    sample = pd.DataFrame([{"verbatim": "Service parfait et livraison rapide", "rating": 5}])
    model.predict(sample)
    return model, actual_hash


def bootstrap_model(client=None, model_path=None, hash_path=None):
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
    client = client or MlflowClient()
    try:
        existing = client.get_model_version_by_alias(MODEL_NAME, PRODUCTION_ALIAS)
    except Exception as exc:
        # A missing model/alias is expected on a fresh registry; other errors must surface.
        if "RESOURCE_DOES_NOT_EXIST" not in str(exc) and "not found" not in str(exc).lower():
            raise
    else:
        mlflow.sklearn.load_model(MODEL_URI)
        print(f"Existing production model v{existing.version}; no new version created.")
        return existing

    model_path = Path(model_path or os.getenv("MODEL_BOOTSTRAP_PATH", DEFAULT_MODEL_PATH))
    hash_path = Path(hash_path or os.getenv("MODEL_BOOTSTRAP_SHA256_PATH", DEFAULT_HASH_PATH))
    model, digest = load_verified_model(model_path, hash_path)

    with mlflow.start_run(run_name="cold-start-model-bootstrap"):
        mlflow.set_tag("bootstrap", "versioned-local-artifact")
        mlflow.set_tag("model_sha256", digest)
        mlflow.set_tag("model_source", "app/models/sentiment_model.pkl")
        info = mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path=MODEL_NAME,
            registered_model_name=MODEL_NAME,
        )
        version = info.registered_model_version
        if version is None:
            raise RuntimeError("MLflow did not return a registered model version.")
        # Check the immutable version before assigning the alias.
        mlflow.sklearn.load_model(f"models:/{MODEL_NAME}/{version}")
        client.set_registered_model_alias(MODEL_NAME, PRODUCTION_ALIAS, version)

    loaded = mlflow.sklearn.load_model(MODEL_URI)
    loaded.predict(pd.DataFrame([{"verbatim": "Service parfait", "rating": 5}]))
    print(f"Bootstrapped {MODEL_URI} v{version} from SHA-256 {digest}.")
    return client.get_model_version_by_alias(MODEL_NAME, PRODUCTION_ALIAS)


if __name__ == "__main__":
    bootstrap_model()
