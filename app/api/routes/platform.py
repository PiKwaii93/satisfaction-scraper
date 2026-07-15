from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.auth import (
    AuthenticatedUser,
    require_current_user,
    require_platform_admin,
)
from app.api.schemas import (
    OrganizationPlanUpdate,
    OrganizationSettingsResponse,
    PlatformOrganizationResponse,
    UpgradeRequestResponse,
    UpgradeRequestStatusUpdate,
)
from app.api.services.organization_service import (
    get_organization_settings,
    record_audit_event,
    update_organization_plan,
)
from app.api.services.platform_service import list_platform_organizations
from app.api.services.upgrade_service import (
    list_platform_upgrade_requests,
    update_platform_upgrade_request_status,
)


router = APIRouter(prefix="/platform", tags=["platform"])


@router.get(
    "/organizations",
    response_model=list[PlatformOrganizationResponse],
    summary="Lister les organisations clientes",
)
def platform_organizations(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(require_current_user),
):
    require_platform_admin(user)
    return list_platform_organizations(limit=limit, offset=offset)


@router.patch(
    "/organizations/{organization_id}/plan",
    response_model=OrganizationSettingsResponse,
    summary="Modifier le plan d'une organisation cliente",
)
def platform_update_organization_plan(
    organization_id: int,
    payload: OrganizationPlanUpdate,
    user: AuthenticatedUser = Depends(require_current_user),
):
    require_platform_admin(user)
    previous_settings = get_organization_settings(organization_id)
    settings = update_organization_plan(organization_id, payload.plan)
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation introuvable.",
        )

    previous_plan = (previous_settings or {}).get("plan")
    record_audit_event(
        organization_id=organization_id,
        actor_user=user,
        event_type="platform.organization_plan_updated",
        summary=(
            "Plan de l'organisation mis a jour par la plateforme: "
            f"{previous_plan} -> {settings['plan']}."
        ),
        entity_type="organization",
        entity_id=organization_id,
        metadata={"previous_plan": previous_plan, "new_plan": settings["plan"]},
    )
    return settings


@router.get(
    "/upgrade-requests",
    response_model=list[UpgradeRequestResponse],
    summary="Lister les demandes d'upgrade de toutes les organisations",
)
def platform_upgrade_requests(
    request_status: str = Query(
        default="open",
        pattern="^(open|all|pending|approved|rejected|completed|cancelled)$",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(require_current_user),
):
    require_platform_admin(user)
    return list_platform_upgrade_requests(
        status=request_status,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/upgrade-requests/{upgrade_request_id}",
    response_model=UpgradeRequestResponse,
    summary="Traiter une demande d'upgrade",
)
def platform_update_upgrade_request(
    upgrade_request_id: int,
    payload: UpgradeRequestStatusUpdate,
    user: AuthenticatedUser = Depends(require_current_user),
):
    require_platform_admin(user)
    upgrade_request = update_platform_upgrade_request_status(
        upgrade_request_id,
        payload.status,
    )
    if upgrade_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demande d'upgrade introuvable.",
        )

    record_audit_event(
        organization_id=upgrade_request["organization_id"],
        actor_user=user,
        event_type="platform.upgrade_request_updated",
        summary=(
            "Demande d'upgrade traitee par la plateforme: "
            f"{upgrade_request['requested_plan']} -> {upgrade_request['status']}."
        ),
        entity_type="upgrade_request",
        entity_id=upgrade_request_id,
        metadata={
            "requested_plan": upgrade_request["requested_plan"],
            "status": upgrade_request["status"],
            "organization_id": upgrade_request["organization_id"],
        },
    )
    return upgrade_request
