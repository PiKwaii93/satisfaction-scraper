from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import AuthenticatedUser, require_current_user, require_org_admin
from app.api.schemas import ErrorResponse, ReviewSourceResponse, ReviewSourceUpdate
from app.api.services.organization_service import record_audit_event
from app.api.services.review_sources import list_review_sources, update_review_source


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
    return list_review_sources(current_user.organization_id)


@router.patch(
    "/{source_id}",
    response_model=ReviewSourceResponse,
    summary="Configurer une source d'avis",
)
def configure_review_source(
    source_id: str,
    payload: ReviewSourceUpdate,
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    require_org_admin(current_user)
    try:
        source = update_review_source(
            current_user.organization_id,
            source_id,
            payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    record_audit_event(
        organization_id=current_user.organization_id,
        actor_user=current_user,
        event_type="review_source.updated",
        summary=f"Source d'avis {source['label']} mise a jour.",
        entity_type="review_source",
        metadata={
            "source_id": source["source_id"],
            "status": source["status"],
            "is_enabled": source["is_enabled"],
            "config_keys": sorted(source["config"].keys()),
        },
    )
    return source
