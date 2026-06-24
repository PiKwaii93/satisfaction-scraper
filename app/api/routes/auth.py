from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import (
    AuthenticatedUser,
    authenticate_user,
    create_access_token,
    require_current_user,
)
from app.api.schemas import AuthLoginRequest, AuthMeResponse, AuthTokenResponse


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
