"""Settings and configuration service with caching."""
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.settings import AppSettings
from app.config import get_settings

logger = logging.getLogger(__name__)

# Cache forever - only invalidate on explicit update
SETTINGS_CACHE_KEY = "app:settings:singleton"


class SettingsService:
    """Manages application settings with Redis caching."""

    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.settings = get_settings()

    async def get_all_settings(self) -> AppSettings:
        """Get all settings with caching."""
        # Try cache first
        try:
            cached = await self.redis.get(SETTINGS_CACHE_KEY)
            if cached:
                data = json.loads(cached)
                logger.info("settings.cache_hit")
                # Return as dict, convert to AppSettings in caller
                return data
        except Exception as e:
            logger.warning("settings.cache_get_failed", error=str(e))

        # Get from database
        try:
            result = await self.db.execute(
                select(AppSettings).where(AppSettings.id == "singleton")
            )
            settings = result.scalars().first()

            if not settings:
                # Create default settings
                settings = AppSettings(id="singleton")
                self.db.add(settings)
                await self.db.commit()
                await self.db.refresh(settings)
                logger.info("settings.created_defaults")

            # Cache it indefinitely
            settings_dict = {
                "brand_name": settings.brand_name,
                "brand_color": settings.brand_color,
                "logo_url": settings.logo_url,
                "favicon_url": settings.favicon_url,
                "page_title": settings.page_title,
                "page_description": settings.page_description,
                "copyright_text": settings.copyright_text,
                "chat_welcome_message": settings.chat_welcome_message,
                "chat_placeholder": settings.chat_placeholder,
                "enable_suggestions": settings.enable_suggestions,
                "chat_suggestions": json.loads(settings.chat_suggestions) if isinstance(settings.chat_suggestions, str) else settings.chat_suggestions,
                "theme_mode": settings.theme_mode,
                "accent_color": settings.accent_color,
                "sdk_api_endpoint": settings.sdk_api_endpoint,
                "sdk_websocket_endpoint": settings.sdk_websocket_endpoint,
                "sdk_auth_type": settings.sdk_auth_type,
                "enable_knowledge_base": settings.enable_knowledge_base,
                "enable_web_search": settings.enable_web_search,
                "enable_memory": settings.enable_memory,
                "enable_voice": settings.enable_voice,
                "require_source_approval": settings.require_source_approval,
                "auto_approve_sources": settings.auto_approve_sources,
                "max_file_size_mb": settings.max_file_size_mb,
                "web_search_engine": settings.web_search_engine,
                "web_search_max_results": settings.web_search_max_results,
                "include_web_search_in_chat": settings.include_web_search_in_chat,
            }

            try:
                await self.redis.set(SETTINGS_CACHE_KEY, json.dumps(settings_dict))
                logger.info("settings.cached")
            except Exception as e:
                logger.warning("settings.cache_set_failed", error=str(e))

            return settings_dict
        except Exception as e:
            logger.error("settings.get_failed", error=str(e))
            raise

    async def update_settings(self, updates: Dict[str, Any]) -> AppSettings:
        """Update settings and invalidate cache."""
        try:
            result = await self.db.execute(
                select(AppSettings).where(AppSettings.id == "singleton")
            )
            settings = result.scalars().first()

            if not settings:
                settings = AppSettings(id="singleton")
                self.db.add(settings)

            # Update fields
            for key, value in updates.items():
                if hasattr(settings, key):
                    if key == "chat_suggestions" and isinstance(value, list):
                        setattr(settings, key, json.dumps(value))
                    else:
                        setattr(settings, key, value)

            settings.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(settings)

            # Invalidate cache
            try:
                await self.redis.delete(SETTINGS_CACHE_KEY)
                logger.info("settings.cache_invalidated")
            except Exception as e:
                logger.warning("settings.cache_delete_failed", error=str(e))

            logger.info("settings.updated", keys=list(updates.keys()))
            return settings
        except Exception as e:
            logger.error("settings.update_failed", error=str(e))
            raise

    async def get_setting(self, key: str) -> Any:
        """Get single setting value."""
        settings = await self.get_all_settings()
        return settings.get(key)

    async def set_setting(self, key: str, value: Any) -> None:
        """Set single setting value."""
        await self.update_settings({key: value})

    async def reset_to_defaults(self) -> AppSettings:
        """Reset all settings to defaults."""
        defaults = {
            "brand_name": "RAZE",
            "brand_color": "#3B82F6",
            "page_title": "RAZE AI - Enterprise Chat",
            "copyright_text": "© 2026 RAZE. All rights reserved.",
            "chat_welcome_message": "Hello! I'm RAZE, your AI assistant. How can I help?",
            "chat_placeholder": "Ask me anything...",
            "theme_mode": "dark",
            "enable_knowledge_base": True,
            "enable_web_search": True,
            "enable_memory": True,
            "web_search_engine": "duckduckgo",
            "web_search_max_results": 5,
            "include_web_search_in_chat": True,
        }
        return await self.update_settings(defaults)
