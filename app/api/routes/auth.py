from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.auth import (
    AuthenticatedUser,
    accept_organization_invitation,
    authenticate_user,
    create_access_token,
    create_organization_user,
    invite_organization_user,
    list_organization_users,
    require_org_admin,
    require_current_user,
    require_platform_admin,
)
from app.api.schemas import (
    ActionCenterResponse,
    OrganizationInvitationAccept,
    OrganizationInvitationCreate,
    OrganizationAuditEventResponse,
    OrganizationPlanUpdate,
    OrganizationSettingsResponse,
    OrganizationSettingsUpdate,
    OrganizationUsageResponse,
    UpgradeRequestCreate,
    UpgradeRequestResponse,
    UpgradeRequestStatusUpdate,
    AuthLoginRequest,
    AuthMeResponse,
    AuthTokenResponse,
    OrganizationUserCreate,
    OrganizationUserResponse,
)
from app.api.services.action_center_service import get_action_center
from app.api.services.organization_service import (
    get_organization_settings,
    list_audit_events,
    record_audit_event,
    update_organization_plan,
    update_organization_settings,
)
from app.api.services.upgrade_service import (
    create_upgrade_request,
    list_upgrade_requests,
    update_upgrade_request_status,
)
from app.api.services.usage_limits import (
    UsageLimitError,
    assert_can_add_member,
    get_organization_usage,
)


router = APIRouter(prefix="/auth", tags=["auth"])


def serialize_me(user: AuthenticatedUser):
    return {
        "user_id": user.user_id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "organization": {
            "organization_id": user.organization_id,
            "name": user.organization_name,
        },
    }


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    summary="Se connecter",
)
def login(payload: AuthLoginRequest):
    user = authenticate_user(payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe invalide.",
        )

    return {
        "access_token": create_access_token(user.user_id),
        "token_type": "bearer",
        "user": serialize_me(user),
    }


@router.post(
    "/invitations/accept",
    response_model=AuthTokenResponse,
    summary="Accepter une invitation",
)
def accept_invitation(payload: OrganizationInvitationAccept):
    user = accept_organization_invitation(payload)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation invalide.",
        )

    record_audit_event(
        organization_id=user.organization_id,
        actor_user=user,
        event_type="user.invitation_accepted",
        summary=f"{user.email} a active son compte.",
        entity_type="user",
        entity_id=user.user_id,
        metadata={"role": user.role},
    )

    return {
        "access_token": create_access_token(user.user_id),
        "token_type": "bearer",
        "user": serialize_me(user),
    }


@router.get(
    "/me",
    response_model=AuthMeResponse,
    summary="Consulter l'utilisateur connecte",
)
def me(user: AuthenticatedUser = Depends(require_current_user)):
    return serialize_me(user)


@router.get(
    "/organization/users",
    response_model=list[OrganizationUserResponse],
    summary="Lister les utilisateurs de l'organisation",
)
def organization_users(user: AuthenticatedUser = Depends(require_current_user)):
    return list_organization_users(
        user.organization_id,
        include_invitation_links=user.role in {"admin", "platform_admin"},
    )


@router.get(
    "/organization/settings",
    response_model=OrganizationSettingsResponse,
    summary="Consulter les parametres de l'organisation",
)
def organization_settings(user: AuthenticatedUser = Depends(require_current_user)):
    settings = get_organization_settings(user.organization_id)
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation introuvable.",
        )
    return settings


@router.get(
    "/organization/usage",
    response_model=OrganizationUsageResponse,
    summary="Consulter le plan et l'usage de l'organisation",
)
def organization_usage(user: AuthenticatedUser = Depends(require_current_user)):
    return get_organization_usage(user.organization_id)


@router.get(
    "/organization/action-center",
    response_model=ActionCenterResponse,
    summary="Consulter le centre d'action de l'organisation",
)
def organization_action_center(
    limit: int = Query(default=8, ge=1, le=20),
    user: AuthenticatedUser = Depends(require_current_user),
):
    return get_action_center(
        user.organization_id,
        role=user.role,
        limit=limit,
    )


@router.patch(
    "/organization/settings",
    response_model=OrganizationSettingsResponse,
    summary="Modifier les parametres de l'organisation",
)
def update_settings(
    payload: OrganizationSettingsUpdate,
    user: AuthenticatedUser = Depends(require_current_user),
):
    require_org_admin(user)
    previous_settings = get_organization_settings(user.organization_id)
    settings = update_organization_settings(user.organization_id, payload)
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation introuvable.",
        )

    changed_fields = [
        field
        for field in ("name", "default_source", "default_pages_per_star")
        if previous_settings and previous_settings.get(field) != settings.get(field)
    ]
    record_audit_event(
        organization_id=user.organization_id,
        actor_user=user,
        event_type="organization.settings_updated",
        summary="Parametres de l'organisation mis a jour.",
        entity_type="organization",
        entity_id=user.organization_id,
        metadata={"changed_fields": changed_fields},
    )
    return settings


@router.patch(
    "/organization/plan",
    response_model=OrganizationSettingsResponse,
    summary="Modifier le plan de l'organisation",
)
def update_plan(
    payload: OrganizationPlanUpdate,
    user: AuthenticatedUser = Depends(require_current_user),
):
    require_platform_admin(user)
    previous_settings = get_organization_settings(user.organization_id)
    settings = update_organization_plan(user.organization_id, payload.plan)
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation introuvable.",
        )

    previous_plan = (previous_settings or {}).get("plan")
    record_audit_event(
        organization_id=user.organization_id,
        actor_user=user,
        event_type="organization.plan_updated",
        summary=f"Plan de l'organisation mis a jour: {previous_plan} -> {settings['plan']}.",
        entity_type="organization",
        entity_id=user.organization_id,
        metadata={"previous_plan": previous_plan, "new_plan": settings["plan"]},
    )
    return settings


@router.post(
    "/organization/upgrade-requests",
    response_model=UpgradeRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Creer une demande d'upgrade",
)
def request_upgrade(
    payload: UpgradeRequestCreate,
    user: AuthenticatedUser = Depends(require_current_user),
):
    try:
        upgrade_request = create_upgrade_request(user.organization_id, user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    record_audit_event(
        organization_id=user.organization_id,
        actor_user=user,
        event_type="organization.upgrade_requested",
        summary=(
            "Demande d'upgrade creee vers le plan "
            f"{upgrade_request['requested_plan']}."
        ),
        entity_type="upgrade_request",
        entity_id=upgrade_request["upgrade_request_id"],
        metadata={
            "current_plan": upgrade_request["current_plan"],
            "requested_plan": upgrade_request["requested_plan"],
            "status": upgrade_request["status"],
            "source": upgrade_request.get("source"),
        },
    )
    return upgrade_request


@router.get(
    "/organization/upgrade-requests",
    response_model=list[UpgradeRequestResponse],
    summary="Lister les demandes d'upgrade de l'organisation",
)
def organization_upgrade_requests(
    request_status: str = Query(default="open", pattern="^(open|all|pending|approved|rejected|completed|cancelled)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(require_current_user),
):
    require_org_admin(user)
    return list_upgrade_requests(
        user.organization_id,
        status=request_status,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/organization/upgrade-requests/{upgrade_request_id}",
    response_model=UpgradeRequestResponse,
    summary="Mettre a jour une demande d'upgrade",
)
def update_upgrade_request(
    upgrade_request_id: int,
    payload: UpgradeRequestStatusUpdate,
    user: AuthenticatedUser = Depends(require_current_user),
):
    require_platform_admin(user)
    upgrade_request = update_upgrade_request_status(
        user.organization_id,
        upgrade_request_id,
        payload.status,
    )
    if upgrade_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demande d'upgrade introuvable.",
        )

    record_audit_event(
        organization_id=user.organization_id,
        actor_user=user,
        event_type="organization.upgrade_request_updated",
        summary=(
            "Demande d'upgrade mise a jour: "
            f"{upgrade_request['requested_plan']} -> {upgrade_request['status']}."
        ),
        entity_type="upgrade_request",
        entity_id=upgrade_request_id,
        metadata={
            "requested_plan": upgrade_request["requested_plan"],
            "status": upgrade_request["status"],
        },
    )
    return upgrade_request


@router.get(
    "/organization/audit-events",
    response_model=list[OrganizationAuditEventResponse],
    summary="Consulter le journal d'activite de l'organisation",
)
def organization_audit_events(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(require_current_user),
):
    require_org_admin(user)
    return list_audit_events(user.organization_id, limit=limit, offset=offset)


@router.post(
    "/organization/users",
    response_model=OrganizationUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter un utilisateur a l'organisation",
)
def add_organization_user(
    payload: OrganizationUserCreate,
    user: AuthenticatedUser = Depends(require_current_user),
):
    require_org_admin(user)
    try:
        assert_can_add_member(user.organization_id)
    except UsageLimitError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    created_user = create_organization_user(user.organization_id, payload)
    record_audit_event(
        organization_id=user.organization_id,
        actor_user=user,
        event_type="user.created",
        summary=f"Utilisateur actif cree pour {created_user['email']}.",
        entity_type="user",
        entity_id=created_user["user_id"],
        metadata={"role": created_user["role"]},
    )
    return created_user


@router.post(
    "/organization/invitations",
    response_model=OrganizationUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Inviter un utilisateur dans l'organisation",
)
def invite_user(
    payload: OrganizationInvitationCreate,
    user: AuthenticatedUser = Depends(require_current_user),
):
    require_org_admin(user)
    try:
        assert_can_add_member(user.organization_id)
    except UsageLimitError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    invited_user = invite_organization_user(user.organization_id, payload)
    record_audit_event(
        organization_id=user.organization_id,
        actor_user=user,
        event_type="user.invited",
        summary=f"Invitation creee pour {invited_user['email']}.",
        entity_type="user",
        entity_id=invited_user["user_id"],
        metadata={"role": invited_user["role"]},
    )
    return invited_user
