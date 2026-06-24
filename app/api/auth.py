import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.database import get_cursor


DEFAULT_JWT_SECRET = "dev-satisfaction-jwt-secret-change-me-32-bytes"
DEFAULT_JWT_ALGORITHM = "HS256"
DEFAULT_TOKEN_EXPIRE_MINUTES = 60 * 24
MAX_BCRYPT_PASSWORD_BYTES = 72

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: int
    email: str
    full_name: str | None
    role: str
    organization_id: int
    organization_name: str


def get_jwt_secret():
    return os.getenv("JWT_SECRET_KEY", DEFAULT_JWT_SECRET)


def get_token_expire_minutes():
    try:
        return max(
            5,
            int(os.getenv("JWT_EXPIRE_MINUTES", DEFAULT_TOKEN_EXPIRE_MINUTES)),
        )
    except ValueError:
        return DEFAULT_TOKEN_EXPIRE_MINUTES


def get_bcrypt_password_bytes(password: str):
    return password.encode("utf-8")[:MAX_BCRYPT_PASSWORD_BYTES]


def hash_password(password: str):
    password_bytes = get_bcrypt_password_bytes(password)
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str):
    try:
        return bcrypt.checkpw(
            get_bcrypt_password_bytes(password),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


def create_access_token(user_id: int):
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=get_token_expire_minutes()
    )
    payload = {
        "sub": str(user_id),
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=DEFAULT_JWT_ALGORITHM)


def get_user_by_email(email: str):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                u.user_id,
                u.organization_id,
                u.email,
                u.full_name,
                u.password_hash,
                u.role,
                u.is_active,
                o.name AS organization_name
            FROM users u
            JOIN organizations o ON o.organization_id = u.organization_id
            WHERE LOWER(u.email) = LOWER(%s);
            """,
            (email,),
        )
        return cursor.fetchone()


def get_user_by_id(user_id: int):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                u.user_id,
                u.organization_id,
                u.email,
                u.full_name,
                u.role,
                u.is_active,
                o.name AS organization_name
            FROM users u
            JOIN organizations o ON o.organization_id = u.organization_id
            WHERE u.user_id = %s;
            """,
            (user_id,),
        )
        return cursor.fetchone()


def serialize_authenticated_user(row):
    if row is None or not row.get("is_active", True):
        return None

    return AuthenticatedUser(
        user_id=int(row["user_id"]),
        email=row["email"],
        full_name=row.get("full_name"),
        role=row.get("role") or "member",
        organization_id=int(row["organization_id"]),
        organization_name=row.get("organization_name") or "Organisation",
    )


def authenticate_user(email: str, password: str):
    user = get_user_by_email(email)
    if not user or not user.get("is_active"):
        return None

    if not verify_password(password, user["password_hash"]):
        return None

    return serialize_authenticated_user(user)


def serialize_organization_user(row):
    return {
        "user_id": int(row["user_id"]),
        "email": row["email"],
        "full_name": row.get("full_name"),
        "role": row.get("role") or "member",
        "is_active": bool(row.get("is_active", True)),
        "created_at": row.get("created_at"),
    }


def list_organization_users(organization_id: int):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT user_id, email, full_name, role, is_active, created_at
            FROM users
            WHERE organization_id = %s
            ORDER BY
                CASE role WHEN 'admin' THEN 0 ELSE 1 END,
                LOWER(email);
            """,
            (organization_id,),
        )
        return [serialize_organization_user(row) for row in cursor.fetchall()]


def create_organization_user(organization_id: int, payload):
    normalized_email = payload.email.strip().lower()
    full_name = payload.full_name.strip() if payload.full_name else None

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            "SELECT user_id FROM users WHERE LOWER(email) = LOWER(%s);",
            (normalized_email,),
        )
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un utilisateur existe deja avec cet email.",
            )

        cursor.execute(
            """
            INSERT INTO users (
                organization_id,
                email,
                full_name,
                password_hash,
                role,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING user_id, email, full_name, role, is_active, created_at;
            """,
            (
                organization_id,
                normalized_email,
                full_name,
                hash_password(payload.password),
                payload.role,
            ),
        )
        return serialize_organization_user(cursor.fetchone())


def require_org_admin(user: AuthenticatedUser):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Action reservee aux administrateurs de l'organisation.",
        )
    return user


def decode_access_token(token: str):
    try:
        payload = jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=[DEFAULT_JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expiree. Reconnecte-toi.",
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token invalide.",
        ) from exc

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token invalide.",
        )

    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token invalide.",
        ) from exc


def require_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise.",
        )

    user_id = decode_access_token(credentials.credentials)
    user = serialize_authenticated_user(get_user_by_id(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable ou inactif.",
        )

    return user


def seed_demo_identity():
    org_name = os.getenv("DEMO_ORG_NAME", "Demo Satisfaction Client")
    org_slug = os.getenv("DEMO_ORG_SLUG", "demo")
    admin_email = os.getenv("DEMO_ADMIN_EMAIL", "demo@satisfaction.local")
    admin_password = os.getenv("DEMO_ADMIN_PASSWORD", "demo-password")
    admin_name = os.getenv("DEMO_ADMIN_NAME", "Admin Demo")

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO organizations (name, slug, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (slug) DO UPDATE
            SET name = EXCLUDED.name,
                updated_at = NOW()
            RETURNING organization_id;
            """,
            (org_name, org_slug),
        )
        organization_id = cursor.fetchone()["organization_id"]

        cursor.execute(
            """
            UPDATE companies
            SET organization_id = %s
            WHERE organization_id IS NULL;
            """,
            (organization_id,),
        )
        cursor.execute(
            """
            UPDATE analysis_runs
            SET organization_id = %s
            WHERE organization_id IS NULL;
            """,
            (organization_id,),
        )
        cursor.execute(
            """
            UPDATE model_training_runs
            SET organization_id = %s
            WHERE organization_id IS NULL;
            """,
            (organization_id,),
        )

        cursor.execute("SELECT COUNT(*) AS count FROM users;")
        if int(cursor.fetchone()["count"] or 0) == 0:
            cursor.execute(
                """
                INSERT INTO users (
                    organization_id,
                    email,
                    full_name,
                    password_hash,
                    role,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, 'admin', NOW());
                """,
                (
                    organization_id,
                    admin_email,
                    admin_name,
                    hash_password(admin_password),
                ),
            )
