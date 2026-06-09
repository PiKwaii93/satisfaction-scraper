import csv
from io import StringIO

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.schemas import (
    AnalysisRunCreate,
    AnalysisRunEventResponse,
    AnalysisRunResponse,
    ReviewListResponse,
)
from app.api.services.analysis_service import (
    create_analysis_run,
    get_analysis_run,
    get_export_rows,
    get_run_events,
    get_run_reviews,
    get_run_summary,
    list_analysis_runs,
    queue_analysis_run,
)


router = APIRouter(prefix="/analysis-runs", tags=["analysis-runs"])


@router.post("", response_model=AnalysisRunResponse, status_code=201)
def create_run(payload: AnalysisRunCreate):
    try:
        run = create_analysis_run(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return run


@router.get("", response_model=list[AnalysisRunResponse])
def list_runs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return list_analysis_runs(limit=limit, offset=offset)


@router.get("/{run_id}", response_model=AnalysisRunResponse)
def get_run(run_id: int):
    run = get_analysis_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    return run


@router.post("/{run_id}/execute", response_model=AnalysisRunResponse)
def execute_run(run_id: int, skip_scrape: bool = False):
    if get_analysis_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")

    try:
        queue_analysis_run(run_id, skip_scrape=skip_scrape)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return get_analysis_run(run_id)


@router.get("/{run_id}/reviews", response_model=ReviewListResponse)
def list_reviews(
    run_id: int,
    sentiment: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    if get_analysis_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    return get_run_reviews(
        run_id=run_id,
        sentiment=sentiment,
        limit=limit,
        offset=offset,
    )


@router.get("/{run_id}/events", response_model=list[AnalysisRunEventResponse])
def list_events(
    run_id: int,
    limit: int = Query(default=100, ge=1, le=500),
):
    if get_analysis_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    return get_run_events(run_id, limit=limit)


@router.get("/{run_id}/summary")
def get_summary(run_id: int):
    summary = get_run_summary(run_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    return summary


@router.get("/{run_id}/export")
def export_reviews(run_id: int):
    if get_analysis_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")

    rows = get_export_rows(run_id)
    buffer = StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "review_id",
            "rating",
            "author_name",
            "raw_date",
            "sentiment_label",
            "sentiment_score",
            "company_responded",
            "topics",
            "verbatim",
        ],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                **row,
                "topics": ",".join(row.get("topics", [])),
            }
        )

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="analysis_run_{run_id}.csv"'
        },
    )
