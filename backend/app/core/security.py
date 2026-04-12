"""
RAZE Enterprise AI OS – Security & Authentication Engine

Covers:
  - JWT access / refresh token creation and verification
  - bcrypt password hashing
  - FastAPI dependency injection helpers (get_current_user, get_current_admin)
  - API-key generation, hashing, and DB lookup
  - Redis-backed rate limiting
"""

from __future__ import annotations

import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import APIKey, User, UserRole

settings = get_settings()
logger = structlog.get_logger(__name__)

# ─── Crypto primitives ────────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# ─── Token helpers ────────────────────────────────────────────────────────────

def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed HS256 JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "access"})
    token = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    logger.debug("access_token_created", subject=data.get("sub"), expires=expire.isoformat())
    return token


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a signed HS256 JWT refresh token with a longer TTL."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    token = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    logger.debug("refresh_token_created", subject=data.get("sub"), expires=expire.isoformat())
    return token


def verify_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    """
    Decode and verify a JWT.  Raises HTTPException 401 on any failure.
    Returns the decoded payload on success.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        logger.warning("jwt_verify_failed", error=str(exc))
        raise credentials_exception from exc

    token_type: str | None = payload.get("type")
    if token_type != expected_type:
        logger.warning(
            "jwt_type_mismatch", expected=expected_type, got=token_type
        )
        raise credentials_exception

    return payload


# ─── Password helpers ─────────────────────────────────────────────────────────

def get_password_hash(password: str) -> str:
    """Return the bcrypt hash of *password*."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if *plain_password* matches *hashed_password*."""
    return pwd_context.verify(plain_password, hashed_password)


# ─── API Key helpers ──────────────────────────────────────────────────────────

def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key.

    Returns
    -------
    raw_key   : str  – the secret value shown once to the user
    key_hash  : str  – SHA-256 hex digest stored in the DB
    key_prefix: str  – first 8 chars of raw_key used for UI identification
    """
    raw_key = "raze_" + secrets.token_urlsafe(settings.api_key_length)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:8]
    return raw_key, key_hash, key_prefix


def _hash_api_key(raw_key: str) -> str:
    """SHA-256 hash of a raw API key string."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


# ─── FastAPI dependencies ─────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency: extract and validate the Bearer JWT, then load the
    corresponding User from the database.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(credentials.credentials, expected_type="access")
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user: User | None = result.scalar_one_or_none()

    if user is None:
        logger.warning("user_not_found_in_db", user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    # Check account lockout
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account temporarily locked",
        )

    return user


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    FastAPI dependency: ensure the authenticated user holds an admin or
    superadmin role.
    """
    if current_user.role not in (UserRole.admin.value, UserRole.superadmin.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return current_user


async def verify_api_key(
    api_key: str | None = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency: look up a hashed API key in the database, validate it,
    and return the owning User.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )

    key_hash = _hash_api_key(api_key)
    key_prefix = api_key[:8]

    result = await db.execute(
        select(APIKey)
        .where(APIKey.key_hash == key_hash, APIKey.is_active == True)  # noqa: E712
    )
    api_key_record: APIKey | None = result.scalar_one_or_none()

    if api_key_record is None:
        logger.warning("api_key_not_found", prefix=key_prefix)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
        )

    # Check expiry
    if (
        api_key_record.expires_at is not None
        and api_key_record.expires_at < datetime.now(timezone.utc)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )

    # Load owner
    user_result = await db.execute(
        select(User).where(User.id == api_key_record.user_id, User.is_active == True)  # noqa: E712
    )
    user: User | None = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key owner not found or inactive",
        )

    # Update usage stats (fire-and-forget; don't block the request)
    try:
        api_key_record.last_used = datetime.now(timezone.utc)
        api_key_record.total_requests = (api_key_record.total_requests or 0) + 1
        await db.commit()
    except Exception:  # pragma: no cover
        await db.rollback()

    logger.info("api_key_authenticated", prefix=key_prefix, user_id=str(user.id))
    return user


# ─── Rate limiting ────────────────────────────────────────────────────────────

class RateLimiter:
    """
    Sliding-window rate limiter backed by Redis.

    Uses a sorted set per (identifier, window) where member = request timestamp
    and score = timestamp.  Entries older than the window are pruned on each
    check, giving an accurate sliding window count.
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def check(
        self,
        identifier: str,
        limit: int,
        window_seconds: int = 60,
        raise_on_exceeded: bool = True,
    ) -> tuple[bool, int]:
        """
        Check whether *identifier* is within the rate limit.

        Parameters
        ----------
        identifier      : unique key, e.g. ``f"rl:{user_id}:chat"``
        limit           : maximum requests allowed in *window_seconds*
        window_seconds  : size of the sliding window
        raise_on_exceeded: if True, raise HTTPException 429 when exceeded

        Returns
        -------
        (allowed, current_count)
        """
        now = time.time()
        window_start = now - window_seconds
        key = f"raze:rl:{identifier}"

        pipe = self._redis.pipeline()
        # Remove expired entries
        pipe.zremrangebyscore(key, "-inf", window_start)
        # Add current request
        pipe.zadd(key, {str(now): now})
        # Count entries in window
        pipe.zcard(key)
        # Set TTL so the key auto-expires
        pipe.expire(key, window_seconds + 1)
        results = await pipe.execute()

        current_count: int = results[2]
        allowed = current_count <= limit

        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                identifier=identifier,
                count=current_count,
                limit=limit,
            )
            if raise_on_exceeded:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {limit} requests per {window_seconds}s",
                    headers={"Retry-After": str(window_seconds)},
                )

        return allowed, current_count

    async def reset(self, identifier: str) -> None:
        """Clear all rate-limit entries for *identifier* (e.g. after account unlock)."""
        await self._redis.delete(f"raze:rl:{identifier}")


async def check_rate_limit(
    redis: Redis,
    identifier: str,
    limit: int | None = None,
    window_seconds: int = 60,
) -> tuple[bool, int]:
    """
    Convenience function for one-shot rate limit checks without instantiating
    a RateLimiter.  Used in route handlers that already hold a Redis client.
    """
    effective_limit = limit if limit is not None else settings.rate_limit_default_per_minute
    limiter = RateLimiter(redis)
    return await limiter.check(identifier, effective_limit, window_seconds)
