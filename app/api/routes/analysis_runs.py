import csv
from io import StringIO

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from fastapi.responses import StreamingResponse

from app.api.schemas import (
    AnalysisRunCreate,
    AnalysisRunEventResponse,
    AnalysisRunResponse,
    AnalysisRunsComparisonResponse,
    ErrorResponse,
    FeedbackQualityResponse,
    ReviewFeedbackCreate,
    ReviewFeedbackResponse,
    ReviewListResponse,
)
from app.api.security import require_api_key
from app.api.services.analysis_service import (
    ActiveAnalysisRunError,
    create_analysis_run,
    create_csv_analysis_run,
    delete_review_feedback,
    get_feedback_export_rows,
    get_feedback_quality_summary,
    get_analysis_run,
    get_export_rows,
    get_run_events,
    get_run_reviews,
    get_run_summary,
    get_runs_comparison,
    list_analysis_runs,
    queue_analysis_run,
    save_review_feedback,
)


router = APIRouter(
    prefix="/analysis-runs",
    tags=["analysis-runs"],
    dependencies=[Depends(require_api_key)],
    responses={
        401: {"model": ErrorResponse, "description": "API key manquante"},
        403: {"model": ErrorResponse, "description": "API key invalide"},
    },
)


@router.post(
    "",
    response_model=AnalysisRunResponse,
    status_code=201,
    summary="Créer une analyse",
    description="Crée un run d'analyse et l'envoie dans la file Celery si demandé.",
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse, "description": "Analyse identique deja active"},
    },
)
def create_run(payload: AnalysisRunCreate):
    try:
        run = create_analysis_run(payload)
    except ActiveAnalysisRunError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return run


@router.post(
    "/import-csv",
    response_model=AnalysisRunResponse,
    status_code=201,
    summary="Importer un CSV d'avis",
    description=(
        "Importe un fichier CSV d'avis clients et lance l'analyse IA sur les "
        "verbatims fournis."
    ),
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse, "description": "Import CSV deja actif"},
    },
)
async def import_csv_run(
    company: str = Form(..., min_length=2),
    file: UploadFile = File(...),
):
    try:
        content = await file.read()
        if not content:
            raise ValueError("Le fichier CSV est vide.")
        run = create_csv_analysis_run(
            company_input=company,
            file_bytes=content,
            original_filename=file.filename,
        )
    except ActiveAnalysisRunError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return run


@router.get(
    "",
    response_model=list[AnalysisRunResponse],
    summary="Lister les analyses",
    description="Retourne les analyses historisées, de la plus récente à la plus ancienne.",
)
def list_runs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return list_analysis_runs(limit=limit, offset=offset)


@router.get(
    "/compare",
    response_model=AnalysisRunsComparisonResponse,
    summary="Comparer plusieurs analyses",
    description="Compare 2 a 4 runs termines pour produire un benchmark entreprise.",
    responses={400: {"model": ErrorResponse}},
)
def compare_runs(
    run_ids: str = Query(
        ...,
        description="Identifiants de runs separes par des virgules, ex: 1,2,3",
    ),
):
    try:
        parsed_run_ids = [
            int(run_id.strip())
            for run_id in run_ids.split(",")
            if run_id.strip()
        ]
        return get_runs_comparison(parsed_run_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/feedback/quality",
    response_model=FeedbackQualityResponse,
    summary="Consulter la qualité IA",
    description="Agrège les corrections humaines pour piloter le prochain réentraînement.",
)
def get_feedback_quality(recent_limit: int = Query(default=8, ge=1, le=50)):
    return get_feedback_quality_summary(recent_limit=recent_limit)


@router.get(
    "/{run_id}",
    response_model=AnalysisRunResponse,
    summary="Consulter une analyse",
    responses={404: {"model": ErrorResponse}},
)
def get_run(run_id: int):
    run = get_analysis_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    return run


@router.post(
    "/{run_id}/execute",
    response_model=AnalysisRunResponse,
    summary="Relancer une analyse",
    description="Replace un run existant dans la file Celery.",
    responses={404: {"model": ErrorResponse}},
)
def execute_run(run_id: int, skip_scrape: bool = False):
    if get_analysis_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")

    try:
        queue_analysis_run(run_id, skip_scrape=skip_scrape)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return get_analysis_run(run_id)


@router.get(
    "/{run_id}/reviews",
    response_model=ReviewListResponse,
    summary="Lister les avis analysés",
    description="Retourne les avis d'un run, avec filtre optionnel par sentiment.",
    responses={404: {"model": ErrorResponse}},
)
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


@router.post(
    "/{run_id}/reviews/{review_id}/feedback",
    response_model=ReviewFeedbackResponse,
    summary="Corriger le sentiment d'un avis",
    description="Enregistre ou remplace une correction humaine pour alimenter le futur dataset d'entrainement.",
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def save_feedback(run_id: int, review_id: int, payload: ReviewFeedbackCreate):
    if get_analysis_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")

    try:
        feedback = save_review_feedback(run_id, review_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if feedback is None:
        raise HTTPException(status_code=404, detail="Avis introuvable")
    return feedback


@router.delete(
    "/{run_id}/reviews/{review_id}/feedback",
    status_code=204,
    summary="Supprimer une correction",
    responses={404: {"model": ErrorResponse}},
)
def delete_feedback(run_id: int, review_id: int):
    if get_analysis_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    if not delete_review_feedback(run_id, review_id):
        raise HTTPException(status_code=404, detail="Correction introuvable")
    return Response(status_code=204)


@router.get(
    "/{run_id}/events",
    response_model=list[AnalysisRunEventResponse],
    summary="Suivre le journal d'exécution",
    description="Retourne les événements métier émis pendant l'analyse.",
    responses={404: {"model": ErrorResponse}},
)
def list_events(
    run_id: int,
    limit: int = Query(default=100, ge=1, le=500),
):
    if get_analysis_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    return get_run_events(run_id, limit=limit)


@router.get(
    "/{run_id}/summary",
    summary="Consulter le rapport synthétique",
    responses={404: {"model": ErrorResponse}},
)
def get_summary(run_id: int):
    summary = get_run_summary(run_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    return summary


@router.get(
    "/{run_id}/feedback/export",
    summary="Exporter les corrections humaines en CSV",
    responses={404: {"model": ErrorResponse}},
)
def export_feedback(run_id: int):
    if get_analysis_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")

    rows = get_feedback_export_rows(run_id)
    buffer = StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "review_id",
            "run_id",
            "company_name",
            "rating",
            "author_name",
            "raw_date",
            "predicted_label",
            "corrected_label",
            "sentiment_score",
            "feedback_comment",
            "feedback_updated_at",
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
            "Content-Disposition": f'attachment; filename="analysis_run_{run_id}_feedback.csv"'
        },
    )


@router.get(
    "/{run_id}/export",
    summary="Exporter les avis en CSV",
    responses={404: {"model": ErrorResponse}},
)
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
            "corrected_label",
            "feedback_comment",
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
