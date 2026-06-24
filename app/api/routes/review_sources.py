from fastapi import APIRouter, Depends

from app.api.auth import AuthenticatedUser, require_current_user
from app.api.schemas import ErrorResponse, ReviewSourceResponse
from app.api.services.review_sources import list_review_sources


router = APIRouter(
    prefix="/review-sources",
    tags=["review-sources"],
    responses={
        401: {"model": ErrorResponse, "description": "Authentification requise"},
        403: {"model": ErrorResponse, "description": "Token invalide"},
    },
)


@router.get(
    "",
    response_model=list[ReviewSourceResponse],
    summary="Lister les sources d'avis disponibles",
)
def review_sources(current_user: AuthenticatedUser = Depends(require_current_user)):
    _ = current_user
    return list_review_sources()
