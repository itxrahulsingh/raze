"""Knowledge management settings and configuration routes."""
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_redis
from app.models.user import User
from app.api.v1 import deps

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/knowledge", tags=["Knowledge Settings"])


class KnowledgeSettings:
    """Knowledge system settings with Redis caching."""

    CACHE_KEY = "knowledge:settings"
    CACHE_TTL = 3600

    @staticmethod
    def get_defaults() -> dict[str, Any]:
        return {
            "enable_knowledge_base": True,
            "enable_web_search": True,
            "enable_articles": True,
            "enable_documents": True,
            "enable_client_documents": True,
            "enable_chat_sessions": True,
            "enable_training_materials": True,
            "enable_references": True,
            "knowledge_in_chat": True,
            "knowledge_in_search": True,
            "max_knowledge_sources": 1000,
            "auto_approve_sources": False,
            "require_source_approval": True,
            "chat_session_knowledge_enabled": True,
            "web_search_timeout_seconds": 30,
            "knowledge_search_limit": 10,
        }


@router.get("/settings")
async def get_knowledge_settings(
    request: Request,
    current_user: User = Depends(deps.get_current_user),
) -> dict[str, Any]:
    """Get knowledge system settings."""
    await deps.apply_rate_limit(request, "knowledge_settings_read", 120, 60, current_user)

    # Try to get from cache
    redis_client = get_redis()
    try:
        cached = await redis_client.get(KnowledgeSettings.CACHE_KEY)
        if cached:
            import json
            return json.loads(cached)
    except Exception:
        pass

    # Return defaults
    settings = KnowledgeSettings.get_defaults()

    # Try to cache it
    try:
        import json
        await redis_client.setex(
            KnowledgeSettings.CACHE_KEY,
            KnowledgeSettings.CACHE_TTL,
            json.dumps(settings)
        )
    except Exception:
        pass

    return settings


@router.put("/settings")
async def update_knowledge_settings(
    request: Request,
    settings_update: dict[str, Any],
    current_user: User = Depends(deps.get_current_user),
) -> dict[str, Any]:
    """Update knowledge system settings (admin only)."""
    await deps.apply_rate_limit(request, "knowledge_settings_write", 60, 60, current_user)

    # Validate settings
    defaults = KnowledgeSettings.get_defaults()
    validated_settings = {**defaults}

    for key, value in settings_update.items():
        if key in defaults:
            validated_settings[key] = value

    # Store in cache
    redis_client = get_redis()
    try:
        import json
        await redis_client.setex(
            KnowledgeSettings.CACHE_KEY,
            KnowledgeSettings.CACHE_TTL,
            json.dumps(validated_settings)
        )
    except Exception as e:
        logger.warning("knowledge.cache_update_failed", error=str(e))

    logger.info(
        "knowledge.settings_updated",
        admin_id=str(current_user.id),
        settings_keys=list(settings_update.keys()),
    )

    return validated_settings


@router.post("/clear-settings-cache")
async def clear_settings_cache(
    request: Request,
    current_user: User = Depends(deps.get_current_user),
):
    """Clear cached knowledge settings (admin only)."""
    await deps.apply_rate_limit(request, "knowledge_settings_clear_cache", 120, 60, current_user)

    redis_client = get_redis()
    try:
        await redis_client.delete(KnowledgeSettings.CACHE_KEY)
    except Exception as e:
        logger.warning("knowledge.cache_clear_failed", error=str(e))

    logger.info("knowledge.settings_cache_cleared", admin_id=str(current_user.id))

    return {"status": "cache cleared"}
