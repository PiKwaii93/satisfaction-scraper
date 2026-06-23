from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas import (
    ErrorResponse,
    ModelTrainingOverviewResponse,
    ModelTrainingRunCreate,
    ModelTrainingRunResponse,
)
from app.api.security import require_api_key
from app.api.services.training_service import (
    ActiveModelTrainingRunError,
    create_model_training_run,
    get_model_training_overview,
    get_model_training_run,
    list_model_training_runs,
)


router = APIRouter(
    prefix="/model-training",
    tags=["model-training"],
    dependencies=[Depends(require_api_key)],
    responses={
        401: {"model": ErrorResponse, "description": "API key manquante"},
        403: {"model": ErrorResponse, "description": "API key invalide"},
    },
)


@router.get(
    "/overview",
    response_model=ModelTrainingOverviewResponse,
    summary="Consulter l'etat d'entrainement IA",
    description="Retourne le modele en production et les derniers reentrainements.",
)
def get_training_overview(limit: int = Query(default=6, ge=1, le=20)):
    return get_model_training_overview(limit=limit)


@router.get(
    "/runs",
    response_model=list[ModelTrainingRunResponse],
    summary="Lister les entrainements du modele",
)
def list_training_runs(
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    return list_model_training_runs(limit=limit, offset=offset)


@router.post(
    "/runs",
    response_model=ModelTrainingRunResponse,
    status_code=201,
    summary="Lancer un reentrainement du modele",
    responses={409: {"model": ErrorResponse}},
)
def create_training_run(payload: ModelTrainingRunCreate):
    try:
        return create_model_training_run(payload)
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
def get_training_run(training_run_id: int):
    run = get_model_training_run(training_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Entrainement introuvable")
    return run
