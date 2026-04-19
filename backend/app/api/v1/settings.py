"""Settings and configuration management API."""
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.settings import AppSettings
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


async def get_current_user_optional() -> Optional[User]:
    """Get current user if authenticated, otherwise return None."""
    try:
        from fastapi import Request
        from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
        # This is a simplified optional auth - in practice, you'd need the request context
        # For now, we'll make the GET endpoint public without this dependency
        return None
    except Exception:
        return None


@router.get(
    "/",
    response_model=Dict[str, Any],
    summary="Get all application settings",
)
async def get_settings(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get all application settings (cached) - public read, no auth required."""
    from app.database import get_redis

    redis = get_redis()
    service = SettingsService(db, redis)
    settings = await service.get_all_settings()

    # Return public-safe fields for unauthenticated requests
    return {
        "brand_name": settings.get("brand_name", "RAZE"),
        "brand_color": settings.get("brand_color", "#3B82F6"),
        "logo_url": settings.get("logo_url"),
        "favicon_url": settings.get("favicon_url"),
        "page_title": settings.get("page_title", "RAZE AI - Enterprise Chat"),
        "page_description": settings.get("page_description", "Enterprise AI Assistant"),
        "theme_mode": settings.get("theme_mode", "dark"),
        "accent_color": settings.get("accent_color", "#3B82F6"),
        "chat_welcome_message": settings.get("chat_welcome_message"),
        "chat_placeholder": settings.get("chat_placeholder"),
        "enable_suggestions": settings.get("enable_suggestions", True),
        "chat_suggestions": settings.get("chat_suggestions", []),
        "enable_knowledge_base": settings.get("enable_knowledge_base", True),
        "enable_web_search": settings.get("enable_web_search", True),
        "enable_memory": settings.get("enable_memory", True),
        "web_search_engine": settings.get("web_search_engine", "duckduckgo"),
        "web_search_max_results": settings.get("web_search_max_results", 5),
        "include_web_search_in_chat": settings.get("include_web_search_in_chat", True),
    }


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
