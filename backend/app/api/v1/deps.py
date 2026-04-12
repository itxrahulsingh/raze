"""Common API dependencies."""
from fastapi import Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
import structlog

from app.database import get_db, get_redis
from app.models.user import User
from app.config import get_settings
from app.core.security import check_rate_limit

settings = get_settings()
logger = structlog.get_logger(__name__)

async def get_current_user(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )

    token = authorization.replace("Bearer ", "")

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return user

async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current admin user."""
    if current_user.role not in ["superadmin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return current_user


# ─── Rate limiting helper ─────────────────────────────────────────────────────

async def apply_rate_limit(
    request: Request,
    endpoint_name: str,
    limit: int,
    window_seconds: int = 60,
    current_user: User | None = None,
) -> None:
    """
    Apply rate limiting to an endpoint.

    Call this at the beginning of a route handler after getting current_user.

    Usage::

        @router.post("/chat/message")
        async def send_message(
            req: ChatRequest,
            current_user: User = Depends(get_current_user),
            request: Request,
            db: AsyncSession = Depends(get_db),
        ):
            await apply_rate_limit(request, "chat_message", 30, 60, current_user)
            ...
    """
    redis = get_redis()
    try:
        if current_user:
            identifier = f"user:{current_user.id}:{endpoint_name}"
        else:
            # Fallback to IP-based for unauthenticated endpoints
            client_host = request.client.host if hasattr(request, "client") and request.client else "unknown"
            identifier = f"ip:{client_host}:{endpoint_name}"

        await check_rate_limit(redis, identifier, limit, window_seconds)
    finally:
        await redis.aclose()

