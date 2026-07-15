from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import AuthenticatedUser, require_current_user, require_org_admin
from app.api.schemas import (
    CustomerActionCreate,
    CustomerActionResponse,
    CustomerActionUpdate,
    ErrorResponse,
)
from app.api.services.customer_action_service import (
    ACTION_STATUSES,
    create_customer_action,
    list_customer_actions,
    update_customer_action,
)
from app.api.services.organization_service import record_audit_event


router = APIRouter(
    prefix="/customer-actions",
    tags=["customer-actions"],
    responses={
        401: {"model": ErrorResponse, "description": "Authentification requise"},
        403: {"model": ErrorResponse, "description": "Acces refuse"},
    },
)


@router.get(
    "",
    response_model=list[CustomerActionResponse],
    summary="Lister les actions client",
)
def list_actions(
    status: str = Query(default="open"),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    if status != "all" and status not in ACTION_STATUSES:
        raise HTTPException(status_code=400, detail="Statut d'action invalide.")
    try:
        return list_customer_actions(
            current_user.organization_id,
            status=status,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "",
    response_model=CustomerActionResponse,
    status_code=201,
    summary="Creer une action client",
)
def create_action(
    payload: CustomerActionCreate,
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    require_org_admin(current_user)
    try:
        action = create_customer_action(
            current_user.organization_id,
            current_user.user_id,
            payload,
        )
        record_audit_event(
            organization_id=current_user.organization_id,
            actor_user=current_user,
            event_type="customer_action.created",
            summary=f"Action client creee: {action['title']}.",
            entity_type="customer_action",
            entity_id=action["action_id"],
            metadata={
                "alert_id": action.get("alert_id"),
                "run_id": action.get("run_id"),
                "priority": action.get("priority"),
                "status": action.get("status"),
            },
        )
        return action
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch(
    "/{action_id}",
    response_model=CustomerActionResponse,
    summary="Mettre a jour une action client",
)
def update_action(
    action_id: int,
    payload: CustomerActionUpdate,
    current_user: AuthenticatedUser = Depends(require_current_user),
):
    require_org_admin(current_user)
    try:
        action = update_customer_action(
            action_id,
            current_user.organization_id,
            current_user.user_id,
            payload,
        )
        record_audit_event(
            organization_id=current_user.organization_id,
            actor_user=current_user,
            event_type="customer_action.updated",
            summary=f"Action client mise a jour: {action['title']}.",
            entity_type="customer_action",
            entity_id=action["action_id"],
            metadata={
                "status": action.get("status"),
                "priority": action.get("priority"),
            },
        )
        return action
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
