from fastapi import APIRouter, Depends, HTTPException, status

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
    AuthLoginRequest,
    AuthMeResponse,
    AuthTokenResponse,
    OrganizationUserCreate,
    OrganizationUserResponse,
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
    return create_organization_user(user.organization_id, payload)


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
    return invite_organization_user(user.organization_id, payload)
