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
)
from app.api.schemas import (
    OrganizationInvitationAccept,
    OrganizationInvitationCreate,
    OrganizationAuditEventResponse,
    OrganizationSettingsResponse,
    OrganizationSettingsUpdate,
    AuthLoginRequest,
    AuthMeResponse,
    AuthTokenResponse,
    OrganizationUserCreate,
    OrganizationUserResponse,
)
from app.api.services.organization_service import (
    get_organization_settings,
    list_audit_events,
    record_audit_event,
    update_organization_settings,
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
        include_invitation_links=user.role == "admin",
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
