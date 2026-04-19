"""
Centralized configuration caching system.
Stores settings in database with Redis caching layer.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.settings import AppConfig
from app.config import get_settings

logger = logging.getLogger(__name__)

# Cache TTL - 1 hour
CACHE_TTL = 3600


class ConfigCache:
    """Centralized configuration management with caching."""

    def __init__(self, redis_client: Redis, db: AsyncSession):
        self.redis = redis_client
        self.db = db
        self.settings = get_settings()

    async def get_config(self, key: str, default: Any = None) -> Any:
        """Get config value with caching."""
        try:
            # Try cache first
            cached = await self.redis.get(f"config:{key}")
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"config.cache_get_failed: {key}", error=str(e))

        # Get from database
        try:
            stmt = select(AppConfig).where(AppConfig.key == key)
            result = await self.db.execute(stmt)
            config = result.scalars().first()

            if config:
                value = json.loads(config.value)
                # Cache it
                try:
                    await self.redis.setex(
                        f"config:{key}",
                        CACHE_TTL,
                        json.dumps(value)
                    )
                except Exception as e:
                    logger.warning(f"config.cache_set_failed: {key}", error=str(e))
                return value
        except Exception as e:
            logger.error(f"config.db_get_failed: {key}", error=str(e))

        return default

    async def set_config(self, key: str, value: Any) -> None:
        """Set config value and invalidate cache."""
        try:
            stmt = select(AppConfig).where(AppConfig.key == key)
            result = await self.db.execute(stmt)
            config = result.scalars().first()

            value_json = json.dumps(value) if not isinstance(value, str) else value

            if config:
                config.value = value_json
                config.updated_at = datetime.utcnow()
            else:
                config = AppConfig(
                    key=key,
                    value=value_json,
                    category="system"
                )
                self.db.add(config)

            await self.db.commit()

            # Invalidate cache
            await self.redis.delete(f"config:{key}")
            logger.info("config.updated", key=key)
        except Exception as e:
            logger.error("config.set_failed", key=key, error=str(e))
            raise

    async def get_white_label(self) -> Dict[str, Any]:
        """Get white label settings with caching."""
        default_wl = {
            "brand_name": "RAZE",
            "brand_color": "#3B82F6",
            "logo_url": "",
            "favicon_url": "",
            "page_title": "RAZE AI",
            "copyright": "© 2026 RAZE. All rights reserved.",
        }
        return await self.get_config("white_label", default_wl)

    async def set_white_label(self, settings: Dict[str, Any]) -> None:
        """Set white label settings."""
        await self.set_config("white_label", settings)

    async def get_app_settings(self) -> Dict[str, Any]:
        """Get app-wide settings."""
        default_settings = {
            "enable_knowledge_base": True,
            "enable_web_search": False,
            "enable_memory": True,
            "require_source_approval": False,
            "auto_approve_sources": True,
            "max_file_size_mb": 50,
        }
        return await self.get_config("app_settings", default_settings)

    async def set_app_settings(self, settings: Dict[str, Any]) -> None:
        """Set app-wide settings."""
        await self.set_config("app_settings", settings)

    async def invalidate_all(self) -> None:
        """Invalidate all configuration caches."""
        try:
            await self.redis.delete(*[
                "config:white_label",
                "config:app_settings",
            ])
            logger.info("config.cache_invalidated")
        except Exception as e:
            logger.error("config.invalidate_failed", error=str(e))
