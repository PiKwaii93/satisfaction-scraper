import os
import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader


API_KEY_HEADER_NAME = "X-API-Key"
DEFAULT_DEV_API_KEY = "dev-satisfaction-key"

api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


def get_expected_api_key():
    return os.getenv("API_KEY", DEFAULT_DEV_API_KEY)


def require_api_key(api_key: str | None = Security(api_key_header)):
    expected_api_key = get_expected_api_key()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key manquante. Ajoute le header X-API-Key.",
        )

    if not secrets.compare_digest(api_key, expected_api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key invalide.",
        )

    return api_key
