"""Common API dependencies."""
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt

from app.database import get_db
from app.models.user import User
from app.config import get_settings

settings = get_settings()

async def get_current_user(
    token: str = None,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401)

    return user

async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current admin user."""
    if current_user.role not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return current_user
