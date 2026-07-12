import csv
import json
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

from app.api.auth import AuthenticatedUser, require_current_user, require_org_admin
from app.api.schemas import (
    AnalysisRunCreate,
    AnalysisRunEventResponse,
    AnalysisRunResponse,
    AnalysisRunTrendResponse,
    AnalysisRunsComparisonResponse,
    BusinessAlertResponse,
    BusinessAlertStatusUpdate,
    CsvImportPreviewResponse,
    ErrorResponse,
    FeedbackQualityResponse,
    ReviewFeedbackCreate,
    ReviewFeedbackResponse,
    ReviewListResponse,
)
from app.api.services.alert_service import (
    list_business_alerts,
    update_business_alert_status,
    upsert_business_alerts_for_run,
)
from app.api.services.analysis_service import (
    ActiveAnalysisRunError,
    build_csv_import_preview,
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
    get_run_trend,
    get_runs_comparison,
    list_analysis_runs,
    queue_analysis_run,
    save_review_feedback,
)
from app.api.services.organization_service import record_audit_event
from app.api.services.review_sources import is_source_available
from app.api.services.usage_limits import (
    REVIEWS_PER_TRUSTPILOT_PAGE_ESTIMATE,
    FeatureNotAvailableError,
    UsageLimitError,
    assert_can_create_analysis,
    assert_can_import_csv,
    assert_feature_enabled,
)


router = APIRouter(
    prefix="/analysis-runs",
    tags=["analysis-runs"],
    responses={
        401: {"model": ErrorResponse, "description": "Authentification requise"},
        403: {"model": ErrorResponse, "description": "Acces refuse"},
    },
)


def parse_csv_column_mapping(column_mapping: str | None):
    if not column_mapping:
        return None

    try:
        payload = json.loads(column_mapping)
    except json.JSONDecodeError as exc:
        raise ValueError("Mapping CSV invalide: JSON attendu.") from exc

    if not isinstance(payload, dict):
        raise ValueError("Mapping CSV invalide: objet JSON attendu.")

    allowed_fields = {"verbatim", "rating", "author", "date", "company_responded"}
    return {
        str(field): (str(column).strip() if column is not None else "")
        for field, column in payload.items()
        if field in allowed_fields
    }


def require_source_available(organization_id: int, source_id: str):
    if not is_source_available(organization_id, source_id):
        raise HTTPException(
            status_code=400,
            detail=(
                "Cette source d'avis n'est pas active pour l'organisation. "
                "Active-la depuis les sources d'avis avant de lancer une analyse."
            ),
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
def create_run(
    payload: AnalysisRunCreate,
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    require_org_admin(current_user)
    require_source_available(current_user.organization_id, payload.source)
    try:
        estimated_reviews = (
            len(payload.stars) * payload.pages_per_star * REVIEWS_PER_TRUSTPILOT_PAGE_ESTIMATE
        )
        assert_can_create_analysis(
            current_user.organization_id,
            estimated_reviews=estimated_reviews,
        )
        run = create_analysis_run(payload, organization_id=current_user.organization_id)
        record_audit_event(
            organization_id=current_user.organization_id,
            actor_user=current_user,
            event_type="analysis.created",
            summary=f"Analyse Trustpilot creee pour {run['company_name']}.",
            entity_type="analysis_run",
            entity_id=run["run_id"],
            metadata={
                "source": run["source"],
                "pages_per_star": run["pages_per_star"],
            },
        )
    except ActiveAnalysisRunError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except UsageLimitError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return run


@router.post(
    "/preview-csv",
    response_model=CsvImportPreviewResponse,
    summary="Previsualiser un CSV d'avis",
    description=(
        "Analyse les colonnes d'un CSV et retourne un apercu avant de lancer "
        "le run d'analyse."
    ),
    responses={400: {"model": ErrorResponse}},
)
async def preview_csv_run(
    file: UploadFile = File(...),
    column_mapping: str | None = Form(default=None),
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    require_org_admin(current_user)
    require_source_available(current_user.organization_id, "csv")
    try:
        content = await file.read()
        if not content:
            raise ValueError("Le fichier CSV est vide.")
        return build_csv_import_preview(
            content,
            column_mapping=parse_csv_column_mapping(column_mapping),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
    column_mapping: str | None = Form(default=None),
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    require_org_admin(current_user)
    require_source_available(current_user.organization_id, "csv")
    try:
        content = await file.read()
        if not content:
            raise ValueError("Le fichier CSV est vide.")
        preview = build_csv_import_preview(
            content,
            column_mapping=parse_csv_column_mapping(column_mapping),
        )
        assert_can_import_csv(current_user.organization_id, preview["review_count"])
        run = create_csv_analysis_run(
            company_input=company,
            file_bytes=content,
            organization_id=current_user.organization_id,
            original_filename=file.filename,
            column_mapping=parse_csv_column_mapping(column_mapping),
        )
        record_audit_event(
            organization_id=current_user.organization_id,
            actor_user=current_user,
            event_type="analysis.csv_imported",
            summary=f"Import CSV lance pour {run['company_name']}.",
            entity_type="analysis_run",
            entity_id=run["run_id"],
            metadata={"source": run["source"], "filename": file.filename},
        )
    except ActiveAnalysisRunError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except UsageLimitError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
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
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    return list_analysis_runs(
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
    )


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
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    try:
        assert_feature_enabled(current_user.organization_id, "benchmark")
        parsed_run_ids = [
            int(run_id.strip())
            for run_id in run_ids.split(",")
            if run_id.strip()
        ]
        return get_runs_comparison(
            parsed_run_ids,
            organization_id=current_user.organization_id,
        )
    except FeatureNotAvailableError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/feedback/quality",
    response_model=FeedbackQualityResponse,
    summary="Consulter la qualité IA",
    description="Agrège les corrections humaines pour piloter le prochain réentraînement.",
)
def get_feedback_quality(
    recent_limit: int = Query(default=8, ge=1, le=50),
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    return get_feedback_quality_summary(
        recent_limit=recent_limit,
        organization_id=current_user.organization_id,
    )


@router.get(
    "/alerts",
    response_model=list[BusinessAlertResponse],
    summary="Lister les alertes metier",
    description="Retourne les alertes ouvertes ou historisees de l'organisation.",
    responses={400: {"model": ErrorResponse}},
)
def get_business_alerts(
    status: str | None = Query(default="open"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    if status == "all":
        status = None
    if status not in {None, "open", "acknowledged", "resolved"}:
        raise HTTPException(status_code=400, detail="Statut d'alerte invalide")
    return list_business_alerts(
        organization_id=current_user.organization_id,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/alerts/{alert_id}",
    response_model=BusinessAlertResponse,
    summary="Mettre a jour une alerte",
    description="Acquitte, rouvre ou resout une alerte metier.",
    responses={404: {"model": ErrorResponse}},
)
def patch_business_alert(
    alert_id: int,
    payload: BusinessAlertStatusUpdate,
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    require_org_admin(current_user)
    try:
        alert = update_business_alert_status(
            alert_id=alert_id,
            organization_id=current_user.organization_id,
            status=payload.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if alert is None:
        raise HTTPException(status_code=404, detail="Alerte introuvable")

    record_audit_event(
        organization_id=current_user.organization_id,
        actor_user=current_user,
        event_type="business_alert.status_updated",
        summary=f"Alerte #{alert_id} mise a jour: {payload.status}.",
        entity_type="business_alert",
        entity_id=alert_id,
        metadata={
            "status": payload.status,
            "alert_type": alert["alert_type"],
            "run_id": alert.get("run_id"),
        },
    )
    return alert


@router.get(
    "/{run_id}",
    response_model=AnalysisRunResponse,
    summary="Consulter une analyse",
    responses={404: {"model": ErrorResponse}},
)
def get_run(
    run_id: int,
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    run = get_analysis_run(run_id, organization_id=current_user.organization_id)
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
def execute_run(
    run_id: int,
    skip_scrape: bool = False,
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    require_org_admin(current_user)
    if get_analysis_run(run_id, organization_id=current_user.organization_id) is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")

    try:
        queue_analysis_run(run_id, skip_scrape=skip_scrape)
        record_audit_event(
            organization_id=current_user.organization_id,
            actor_user=current_user,
            event_type="analysis.requeued",
            summary=f"Analyse #{run_id} replacee dans la file.",
            entity_type="analysis_run",
            entity_id=run_id,
            metadata={"skip_scrape": skip_scrape},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return get_analysis_run(run_id, organization_id=current_user.organization_id)


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
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    if get_analysis_run(run_id, organization_id=current_user.organization_id) is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    return get_run_reviews(
        run_id=run_id,
        sentiment=sentiment,
        limit=limit,
        offset=offset,
        organization_id=current_user.organization_id,
    )


@router.post(
    "/{run_id}/reviews/{review_id}/feedback",
    response_model=ReviewFeedbackResponse,
    summary="Corriger le sentiment d'un avis",
    description="Enregistre ou remplace une correction humaine pour alimenter le futur dataset d'entrainement.",
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def save_feedback(
    run_id: int,
    review_id: int,
    payload: ReviewFeedbackCreate,
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    require_org_admin(current_user)
    if get_analysis_run(run_id, organization_id=current_user.organization_id) is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")

    try:
        feedback = save_review_feedback(
            run_id,
            review_id,
            payload,
            organization_id=current_user.organization_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if feedback is None:
        raise HTTPException(status_code=404, detail="Avis introuvable")
    record_audit_event(
        organization_id=current_user.organization_id,
        actor_user=current_user,
        event_type="feedback.saved",
        summary=f"Correction enregistree sur l'avis #{review_id}.",
        entity_type="review",
        entity_id=review_id,
        metadata={
            "run_id": run_id,
            "corrected_label": feedback["corrected_label"],
        },
    )
    return feedback


@router.delete(
    "/{run_id}/reviews/{review_id}/feedback",
    status_code=204,
    summary="Supprimer une correction",
    responses={404: {"model": ErrorResponse}},
)
def delete_feedback(
    run_id: int,
    review_id: int,
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    require_org_admin(current_user)
    if get_analysis_run(run_id, organization_id=current_user.organization_id) is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    if not delete_review_feedback(
        run_id,
        review_id,
        organization_id=current_user.organization_id,
    ):
        raise HTTPException(status_code=404, detail="Correction introuvable")
    record_audit_event(
        organization_id=current_user.organization_id,
        actor_user=current_user,
        event_type="feedback.deleted",
        summary=f"Correction supprimee sur l'avis #{review_id}.",
        entity_type="review",
        entity_id=review_id,
        metadata={"run_id": run_id},
    )
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
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    if get_analysis_run(run_id, organization_id=current_user.organization_id) is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    return get_run_events(run_id, limit=limit)


@router.get(
    "/{run_id}/summary",
    summary="Consulter le rapport synthétique",
    responses={404: {"model": ErrorResponse}},
)
def get_summary(
    run_id: int,
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    summary = get_run_summary(run_id, organization_id=current_user.organization_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    return summary


@router.get(
    "/{run_id}/trend",
    response_model=AnalysisRunTrendResponse,
    summary="Comparer avec l'analyse precedente",
    description=(
        "Compare une analyse terminee avec le run precedent termine de la meme "
        "entreprise et de la meme source."
    ),
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_trend(
    run_id: int,
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    try:
        trend = get_run_trend(run_id, organization_id=current_user.organization_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if trend is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    return trend


@router.post(
    "/{run_id}/alerts/refresh",
    response_model=list[BusinessAlertResponse],
    summary="Regenerer les alertes d'un run",
    description="Recalcule les alertes metier d'une analyse terminee.",
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def refresh_business_alerts_for_run(
    run_id: int,
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    require_org_admin(current_user)
    run = get_analysis_run(run_id, organization_id=current_user.organization_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    if run["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail="Les alertes sont disponibles uniquement pour une analyse terminee.",
        )

    alerts = upsert_business_alerts_for_run(
        run_id=run_id,
        organization_id=current_user.organization_id,
    )
    record_audit_event(
        organization_id=current_user.organization_id,
        actor_user=current_user,
        event_type="business_alert.generated",
        summary=f"Alertes metier regenerees pour le run #{run_id}.",
        entity_type="analysis_run",
        entity_id=run_id,
        metadata={"alert_count": len(alerts)},
    )
    return alerts


@router.get(
    "/{run_id}/feedback/export",
    summary="Exporter les corrections humaines en CSV",
    responses={404: {"model": ErrorResponse}},
)
def export_feedback(
    run_id: int,
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    require_org_admin(current_user)
    if get_analysis_run(run_id, organization_id=current_user.organization_id) is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")

    rows = get_feedback_export_rows(
        run_id,
        organization_id=current_user.organization_id,
    )
    record_audit_event(
        organization_id=current_user.organization_id,
        actor_user=current_user,
        event_type="feedback.exported",
        summary=f"Corrections exportees pour le run #{run_id}.",
        entity_type="analysis_run",
        entity_id=run_id,
        metadata={"row_count": len(rows)},
    )
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
def export_reviews(
    run_id: int,
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    if get_analysis_run(run_id, organization_id=current_user.organization_id) is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable")

    rows = get_export_rows(run_id, organization_id=current_user.organization_id)
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
