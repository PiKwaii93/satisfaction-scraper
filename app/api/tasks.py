from app.api.celery_app import celery_app
from app.api.database import ensure_product_schema
from app.api.services.analysis_service import execute_analysis_run


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
    execute_analysis_run(run_id=run_id, skip_scrape=skip_scrape)
    return {"run_id": run_id, "status": "completed"}
