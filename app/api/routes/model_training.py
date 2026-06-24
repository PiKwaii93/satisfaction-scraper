from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import AuthenticatedUser, require_current_user, require_org_admin
from app.api.schemas import (
    ErrorResponse,
    ModelTrainingOverviewResponse,
    ModelTrainingRunCreate,
    ModelTrainingRunResponse,
)
from app.api.services.training_service import (
    ActiveModelTrainingRunError,
    create_model_training_run,
    get_model_training_overview,
    get_model_training_run,
    list_model_training_runs,
)
from app.api.services.organization_service import record_audit_event


router = APIRouter(
    prefix="/model-training",
    tags=["model-training"],
    responses={
        401: {"model": ErrorResponse, "description": "Authentification requise"},
        403: {"model": ErrorResponse, "description": "Acces refuse"},
    },
)


@router.get(
    "/overview",
    response_model=ModelTrainingOverviewResponse,
    summary="Consulter l'etat d'entrainement IA",
    description="Retourne le modele en production et les derniers reentrainements.",
)
def get_training_overview(
    limit: int = Query(default=6, ge=1, le=20),
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    return get_model_training_overview(
        organization_id=current_user.organization_id,
        limit=limit,
    )


@router.get(
    "/runs",
    response_model=list[ModelTrainingRunResponse],
    summary="Lister les entrainements du modele",
)
def list_training_runs(
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    return list_model_training_runs(
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/runs",
    response_model=ModelTrainingRunResponse,
    status_code=201,
    summary="Lancer un reentrainement du modele",
    responses={409: {"model": ErrorResponse}},
)
def create_training_run(
    payload: ModelTrainingRunCreate,
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    require_org_admin(current_user)
    try:
        run = create_model_training_run(
            payload,
            organization_id=current_user.organization_id,
        )
        record_audit_event(
            organization_id=current_user.organization_id,
            actor_user=current_user,
            event_type="model_training.created",
            summary=f"Reentrainement IA #{run['training_run_id']} lance.",
            entity_type="model_training_run",
            entity_id=run["training_run_id"],
            metadata={
                "feedback_sample_weight": run.get("feedback_sample_weight"),
                "execute_immediately": payload.execute_immediately,
            },
        )
        return run
    except ActiveModelTrainingRunError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/runs/{training_run_id}",
    response_model=ModelTrainingRunResponse,
    summary="Consulter un entrainement du modele",
    responses={404: {"model": ErrorResponse}},
)
def get_training_run(
    training_run_id: int,
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    run = get_model_training_run(
        training_run_id,
        organization_id=current_user.organization_id,
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Entrainement introuvable")
    return run
