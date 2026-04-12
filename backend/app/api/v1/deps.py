"""Common API dependencies."""
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt

from app.database import get_db
from app.models.user import User
from app.config import get_settings

settings = get_settings()

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
