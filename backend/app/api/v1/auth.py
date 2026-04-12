"""
RAZE Enterprise AI OS – Authentication Routes

Covers:
  POST /auth/login            – email+password → JWT access+refresh tokens
  POST /auth/refresh          – exchange refresh token for new access token
  POST /auth/logout           – blacklist refresh token in Redis
  GET  /auth/me               – current user profile
  PUT  /auth/me               – update own profile
  POST /auth/change-password  – change own password
  POST /auth/api-keys         – create API key
  GET  /auth/api-keys         – list own API keys
  DELETE /auth/api-keys/{id}  – revoke API key
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db, get_redis
from app.models.user import APIKey, User, UserRole
from app.schemas.auth import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyListResponse,
    APIKeyResponse,
    LoginRequest,
    PasswordChangeRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
    UserUpdate,
)
from app.core.security import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def _verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


def _create_access_token(subject: str, settings=None) -> str:
    settings = settings or get_settings()
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "access"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def _create_refresh_token(subject: str, settings=None) -> str:
    settings = settings or get_settings()
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    jti = secrets.token_urlsafe(32)
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "refresh", "jti": jti},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def _hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _generate_raw_api_key(length: int = 64) -> str:
    return secrets.token_urlsafe(length)


# ─── Login ────────────────────────────────────────────────────────────────────


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate with email and password",
    status_code=status.HTTP_200_OK,
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Validate credentials and issue JWT access and refresh tokens.

    Account lockout is enforced after 5 consecutive failed attempts;
    the lock lasts 15 minutes.
    """
    settings = get_settings()

    result = await db.execute(
        select(User).where(User.email == body.email, User.is_active.is_(True))
    )
    user: User | None = result.scalar_one_or_none()

    if user is None:
        logger.warning("auth.login_failed", email=body.email, reason="user_not_found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Check account lock
    if user.locked_until and user.locked_until > datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked until {user.locked_until.isoformat()}",
        )

    if not _verify_password(body.password, user.hashed_password):
        new_attempts = user.failed_login_attempts + 1
        locked_until = None
        if new_attempts >= 5:
            locked_until = datetime.now(UTC) + timedelta(minutes=15)
            logger.warning(
                "auth.account_locked",
                user_id=str(user.id),
                until=locked_until.isoformat(),
            )
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(failed_login_attempts=new_attempts, locked_until=locked_until)
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Successful login – reset failure counters
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            failed_login_attempts=0,
            locked_until=None,
            last_login=func.now(),
        )
    )
    await db.commit()

    access_token = _create_access_token(str(user.id), settings)
    refresh_token = _create_refresh_token(str(user.id), settings)

    logger.info("auth.login_success", user_id=str(user.id), email=user.email)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


# ─── Refresh ──────────────────────────────────────────────────────────────────


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange a refresh token for a new access token",
)
async def refresh_token(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Validate the refresh token (checking the Redis blacklist) and issue
    a new access token.  The refresh token itself is NOT rotated here;
    call /logout to invalidate it explicitly.
    """
    settings = get_settings()
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )

    try:
        payload = jwt.decode(
            body.refresh_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        raise credentials_error

    if payload.get("type") != "refresh":
        raise credentials_error

    jti: str | None = payload.get("jti")
    user_id: str | None = payload.get("sub")
    if not jti or not user_id:
        raise credentials_error

    # Check Redis blacklist
    redis = get_redis()
    try:
        is_blacklisted = await redis.exists(f"blacklist:refresh:{jti}")
        if is_blacklisted:
            raise credentials_error
    finally:
        await redis.aclose()

    # Verify user still exists and is active
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id), User.is_active.is_(True))
    )
    user: User | None = result.scalar_one_or_none()
    if user is None:
        raise credentials_error

    new_access = _create_access_token(user_id, settings)
    logger.info("auth.token_refreshed", user_id=user_id)
    return TokenResponse(
        access_token=new_access,
        refresh_token=body.refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


# ─── Logout ───────────────────────────────────────────────────────────────────


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Invalidate refresh token",
)
async def logout(
    body: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Decode the refresh token and add its JTI to the Redis blacklist,
    effectively invalidating it for the remainder of its TTL.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            body.refresh_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        # Already invalid – nothing to do
        return

    jti: str | None = payload.get("jti")
    exp: int | None = payload.get("exp")
    if not jti or not exp:
        return

    ttl = max(0, exp - int(datetime.now(UTC).timestamp()))
    redis = get_redis()
    try:
        await redis.setex(f"blacklist:refresh:{jti}", ttl, "1")
    finally:
        await redis.aclose()

    logger.info("auth.logout", user_id=str(current_user.id), jti=jti)


# ─── Profile: GET ─────────────────────────────────────────────────────────────


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> User:
    """Return the authenticated user's profile."""
    return current_user


# ─── Profile: PUT ─────────────────────────────────────────────────────────────


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
async def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Update mutable profile fields.  Email and username uniqueness is
    enforced at the database level; conflicts are surfaced as 409.
    """
    update_data: dict = body.model_dump(exclude_none=True)

    # Non-admins cannot change their own role
    if "role" in update_data and current_user.role not in (
        UserRole.admin.value,
        UserRole.superadmin.value,
    ):
        update_data.pop("role")

    if not update_data:
        return current_user

    # Check uniqueness of email / username if changed
    if "email" in update_data:
        existing = await db.execute(
            select(User).where(
                User.email == update_data["email"], User.id != current_user.id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use",
            )

    if "username" in update_data:
        existing = await db.execute(
            select(User).where(
                User.username == update_data["username"], User.id != current_user.id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already in use",
            )

    await db.execute(
        update(User).where(User.id == current_user.id).values(**update_data)
    )
    await db.commit()

    result = await db.execute(select(User).where(User.id == current_user.id))
    updated = result.scalar_one()
    logger.info("auth.profile_updated", user_id=str(current_user.id))
    return updated


# ─── Change Password ──────────────────────────────────────────────────────────


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change own password",
)
async def change_password(
    body: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Verify current password, then replace it with the new one."""
    if not _verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    new_hash = _hash_password(body.new_password)
    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(hashed_password=new_hash)
    )
    await db.commit()
    logger.info("auth.password_changed", user_id=str(current_user.id))


# ─── API Keys: Create ─────────────────────────────────────────────────────────


@router.post(
    "/api-keys",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API key",
)
async def create_api_key(
    body: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIKeyCreateResponse:
    """
    Generate a cryptographically random API key, store its SHA-256 hash,
    and return the raw key exactly once.  The caller must store it safely.
    """
    settings = get_settings()
    raw_key = _generate_raw_api_key(settings.api_key_length)
    prefix = raw_key[:8]
    key_hash = _hash_api_key(raw_key)

    api_key = APIKey(
        user_id=current_user.id,
        name=body.name,
        description=body.description,
        key_hash=key_hash,
        key_prefix=prefix,
        permissions=body.permissions,
        rate_limit=body.rate_limit,
        expires_at=body.expires_at,
        is_active=True,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    logger.info(
        "auth.api_key_created",
        user_id=str(current_user.id),
        key_id=str(api_key.id),
        prefix=prefix,
    )
    return APIKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        raw_key=f"raze_{raw_key}",
        key_prefix=prefix,
        permissions=api_key.permissions,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


# ─── API Keys: List ───────────────────────────────────────────────────────────


@router.get(
    "/api-keys",
    response_model=APIKeyListResponse,
    summary="List own API keys",
)
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIKeyListResponse:
    """Return all API keys belonging to the authenticated user."""
    result = await db.execute(
        select(APIKey)
        .where(APIKey.user_id == current_user.id)
        .order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()
    return APIKeyListResponse(items=list(keys), total=len(keys))


# ─── API Keys: Revoke ─────────────────────────────────────────────────────────


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke API key",
)
async def revoke_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Deactivate an API key.  Only the owning user (or an admin) may revoke it.
    """
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    api_key: APIKey | None = result.scalar_one_or_none()

    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    is_owner = api_key.user_id == current_user.id
    is_admin = current_user.role in (UserRole.admin.value, UserRole.superadmin.value)
    if not (is_owner or is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised")

    await db.execute(
        update(APIKey).where(APIKey.id == key_id).values(is_active=False)
    )
    await db.commit()
    logger.info(
        "auth.api_key_revoked",
        key_id=str(key_id),
        revoked_by=str(current_user.id),
    )
