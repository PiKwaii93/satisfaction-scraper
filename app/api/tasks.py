from app.api.celery_app import celery_app
from app.api.database import ensure_product_schema
from app.api.services.alert_service import generate_business_alerts_for_run
from app.api.services.analysis_service import execute_analysis_run, get_analysis_run
from app.api.services.training_service import (
    execute_model_training_run,
    get_model_training_run,
)


@celery_app.task(
    bind=True,
    name="app.api.tasks.analyze_run",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=2,
)
def analyze_run(self, run_id, skip_scrape=False):
    ensure_product_schema(max_attempts=5, delay_seconds=2)
    run = execute_analysis_run(run_id=run_id, skip_scrape=skip_scrape)
    if run is None:
        run = get_analysis_run(run_id)
    if run and run["status"] == "completed":
        try:
            generate_business_alerts_for_run(run_id)
        except Exception:
            pass
    return {"run_id": run_id, "status": run["status"] if run else "unknown"}


@celery_app.task(
    bind=True,
    name="app.api.tasks.train_model_run",
)
def train_model_run(self, training_run_id):
    ensure_product_schema(max_attempts=5, delay_seconds=2)
    run = execute_model_training_run(training_run_id=training_run_id)
    if run is None:
        run = get_model_training_run(training_run_id)
    return {
        "training_run_id": training_run_id,
        "status": run["status"] if run else "unknown",
    }
