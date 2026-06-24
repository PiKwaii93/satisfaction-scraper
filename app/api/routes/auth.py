from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import (
    AuthenticatedUser,
    authenticate_user,
    create_access_token,
    create_organization_user,
    list_organization_users,
    require_org_admin,
    require_current_user,
)
from app.api.schemas import (
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
    return list_organization_users(user.organization_id)


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
