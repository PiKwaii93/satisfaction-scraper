import os
from datetime import datetime

from app.api.database import get_cursor


ACTIVE_TRAINING_STATUSES = ("pending", "running")
DEFAULT_FEEDBACK_SAMPLE_WEIGHT = 6.0
MODEL_NAME = "sentiment_model"
PRODUCTION_ALIAS = "production"
PRODUCTION_MODEL_URI = f"models:/{MODEL_NAME}@{PRODUCTION_ALIAS}"


class ActiveModelTrainingRunError(ValueError):
    pass


def _isoformat(value):
    return value.isoformat() if value else None


def _safe_float(value):
    return float(value) if value is not None else None


def _safe_int(value):
    return int(value) if value is not None else 0


def get_default_feedback_sample_weight():
    try:
        return max(
            1.0,
            float(os.getenv("FEEDBACK_SAMPLE_WEIGHT", DEFAULT_FEEDBACK_SAMPLE_WEIGHT)),
        )
    except ValueError:
        return DEFAULT_FEEDBACK_SAMPLE_WEIGHT


def serialize_training_run(row):
    if row is None:
        return None

    started_at = row.get("started_at")
    finished_at = row.get("finished_at")
    execution_duration_seconds = None
    if started_at:
        end_at = finished_at or datetime.now()
        execution_duration_seconds = max(
            0,
            int((end_at - started_at).total_seconds()),
        )

    return {
        "training_run_id": row["training_run_id"],
        "status": row["status"],
        "celery_task_id": row.get("celery_task_id"),
        "trigger_source": row.get("trigger_source") or "api",
        "feedback_sample_weight": _safe_float(row.get("feedback_sample_weight")),
        "training_rows": _safe_int(row.get("training_rows")),
        "training_manual_rows": _safe_int(row.get("training_manual_rows")),
        "training_feedback_rows": _safe_int(row.get("training_feedback_rows")),
        "training_effective_rows": _safe_float(row.get("training_effective_rows")),
        "accuracy": _safe_float(row.get("accuracy")),
        "macro_f1": _safe_float(row.get("macro_f1")),
        "weighted_f1": _safe_float(row.get("weighted_f1")),
        "model_version": row.get("model_version"),
        "mlflow_run_id": row.get("mlflow_run_id"),
        "model_uri": row.get("model_uri"),
        "error_message": row.get("error_message"),
        "created_at": _isoformat(row.get("created_at")),
        "started_at": _isoformat(started_at),
        "finished_at": _isoformat(finished_at),
        "execution_duration_seconds": execution_duration_seconds,
    }


def _get_training_run_row(training_run_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT *
            FROM model_training_runs
            WHERE training_run_id = %s;
            """,
            (training_run_id,),
        )
        return cursor.fetchone()


def get_model_training_run(training_run_id):
    return serialize_training_run(_get_training_run_row(training_run_id))


def list_model_training_runs(limit=10, offset=0):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT *
            FROM model_training_runs
            ORDER BY created_at DESC, training_run_id DESC
            LIMIT %s OFFSET %s;
            """,
            (limit, offset),
        )
        return [serialize_training_run(row) for row in cursor.fetchall()]


def get_active_model_training_run():
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT *
            FROM model_training_runs
            WHERE status = ANY(%s)
            ORDER BY created_at DESC, training_run_id DESC
            LIMIT 1;
            """,
            (list(ACTIVE_TRAINING_STATUSES),),
        )
        return serialize_training_run(cursor.fetchone())


def enqueue_model_training_run(training_run_id, task_id=None):
    from app.api.celery_app import celery_app

    task_id = task_id or f"model-training-run-{training_run_id}"
    celery_app.send_task(
        "app.api.tasks.train_model_run",
        args=[training_run_id],
        task_id=task_id,
    )
    return task_id


def create_model_training_run(payload):
    active_run = get_active_model_training_run()
    if active_run:
        raise ActiveModelTrainingRunError(
            "Un entrainement du modele est deja en file ou en cours."
        )

    feedback_sample_weight = (
        payload.feedback_sample_weight
        if payload.feedback_sample_weight is not None
        else get_default_feedback_sample_weight()
    )

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO model_training_runs (
                status,
                trigger_source,
                feedback_sample_weight,
                model_uri
            )
            VALUES ('pending', 'api', %s, %s)
            RETURNING training_run_id;
            """,
            (feedback_sample_weight, PRODUCTION_MODEL_URI),
        )
        training_run_id = cursor.fetchone()["training_run_id"]
        task_id = f"model-training-run-{training_run_id}"
        cursor.execute(
            """
            UPDATE model_training_runs
            SET celery_task_id = %s, updated_at = NOW()
            WHERE training_run_id = %s;
            """,
            (task_id, training_run_id),
        )

    if payload.execute_immediately:
        enqueue_model_training_run(training_run_id, task_id=task_id)

    return get_model_training_run(training_run_id)


def _set_training_run_failed(training_run_id, error_message):
    with get_cursor(commit=True) as cursor:
        cursor.execute(
            """
            UPDATE model_training_runs
            SET
                status = 'failed',
                error_message = %s,
                finished_at = NOW(),
                updated_at = NOW()
            WHERE training_run_id = %s;
            """,
            (str(error_message)[:2000], training_run_id),
        )


def execute_model_training_run(training_run_id):
    row = _get_training_run_row(training_run_id)
    if row is None:
        return None

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            """
            UPDATE model_training_runs
            SET
                status = 'running',
                started_at = COALESCE(started_at, NOW()),
                error_message = NULL,
                updated_at = NOW()
            WHERE training_run_id = %s;
            """,
            (training_run_id,),
        )

    feedback_sample_weight = row.get("feedback_sample_weight")
    previous_feedback_weight = os.environ.get("FEEDBACK_SAMPLE_WEIGHT")
    if feedback_sample_weight is not None:
        os.environ["FEEDBACK_SAMPLE_WEIGHT"] = str(feedback_sample_weight)

    try:
        from app import train_model

        result = train_model.train_and_log_model() or {}
        with get_cursor(commit=True) as cursor:
            cursor.execute(
                """
                UPDATE model_training_runs
                SET
                    status = 'completed',
                    training_rows = %s,
                    training_manual_rows = %s,
                    training_feedback_rows = %s,
                    training_effective_rows = %s,
                    feedback_sample_weight = %s,
                    accuracy = %s,
                    macro_f1 = %s,
                    weighted_f1 = %s,
                    model_version = %s,
                    mlflow_run_id = %s,
                    model_uri = %s,
                    finished_at = NOW(),
                    updated_at = NOW()
                WHERE training_run_id = %s;
                """,
                (
                    int(result.get("training_rows") or 0),
                    int(result.get("training_manual_rows") or 0),
                    int(result.get("training_feedback_rows") or 0),
                    float(result.get("training_effective_rows") or 0),
                    float(result.get("feedback_sample_weight") or feedback_sample_weight or 0),
                    _safe_float(result.get("accuracy")),
                    _safe_float(result.get("macro_f1")),
                    _safe_float(result.get("weighted_f1")),
                    result.get("model_version"),
                    result.get("mlflow_run_id"),
                    result.get("model_uri") or PRODUCTION_MODEL_URI,
                    training_run_id,
                ),
            )
        try:
            from app import sentiment_analysis

            sentiment_analysis.reload_model()
        except Exception as exc:
            print(f"[-] Rechargement du modele apres entrainement ignore: {exc}")
        return get_model_training_run(training_run_id)
    except Exception as exc:
        _set_training_run_failed(training_run_id, exc)
        raise
    finally:
        if previous_feedback_weight is None:
            os.environ.pop("FEEDBACK_SAMPLE_WEIGHT", None)
        else:
            os.environ["FEEDBACK_SAMPLE_WEIGHT"] = previous_feedback_weight


def get_production_model_info():
    try:
        import mlflow
        from mlflow.client import MlflowClient

        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
        client = MlflowClient()
        model_version = client.get_model_version_by_alias(
            MODEL_NAME,
            PRODUCTION_ALIAS,
        )
        return {
            "name": MODEL_NAME,
            "alias": PRODUCTION_ALIAS,
            "version": str(model_version.version),
            "run_id": model_version.run_id,
            "source": model_version.source,
            "model_uri": PRODUCTION_MODEL_URI,
        }
    except Exception:
        return None


def get_model_training_overview(limit=6):
    runs = list_model_training_runs(limit=limit, offset=0)
    return {
        "production_model": get_production_model_info(),
        "latest_run": runs[0] if runs else None,
        "active_run": next(
            (run for run in runs if run["status"] in ACTIVE_TRAINING_STATUSES),
            None,
        ),
        "runs": runs,
    }
