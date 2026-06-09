from app.api.celery_app import celery_app


def enqueue_analysis_run(run_id, skip_scrape=False, task_id=None):
    task_id = task_id or f"analysis-run-{run_id}"
    celery_app.send_task(
        "app.api.tasks.analyze_run",
        args=[run_id, skip_scrape],
        task_id=task_id,
    )
    return task_id
