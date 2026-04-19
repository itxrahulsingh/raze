"""Settings and configuration management API."""
import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.settings import AppSettings
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get(
    "/",
    response_model=Dict[str, Any],
    summary="Get all application settings",
)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get all application settings (cached)."""
    from app.database import get_redis

    redis = get_redis()
    service = SettingsService(db, redis)
    return await service.get_all_settings()


@router.put(
    "/",
    response_model=Dict[str, Any],
    summary="Update application settings",
)
async def update_settings(
    updates: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update application settings (admin only)."""
    # Check admin permission
    if current_user.role not in ("admin", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update settings",
        )

    from app.database import get_redis

    redis = get_redis()
    service = SettingsService(db, redis)
    await service.update_settings(updates)
    return await service.get_all_settings()


@router.get(
    "/{key}",
    summary="Get single setting value",
)
async def get_setting(
    key: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get a single setting value."""
    from app.database import get_redis

    redis = get_redis()
    service = SettingsService(db, redis)
    value = await service.get_setting(key)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found",
        )
    return value


@router.post(
    "/reset",
    response_model=Dict[str, Any],
    summary="Reset settings to defaults",
)
async def reset_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Reset all settings to defaults (admin only)."""
    # Check admin permission
    if current_user.role not in ("admin", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can reset settings",
        )

    from app.database import get_redis

    redis = get_redis()
    service = SettingsService(db, redis)
    await service.reset_to_defaults()
    return await service.get_all_settings()
