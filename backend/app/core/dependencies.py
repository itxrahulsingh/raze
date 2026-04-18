"""
RAZE Enterprise AI OS – FastAPI Dependencies

Provides:
  - Rate limiting dependency injection
  - User context extraction
  - Common request processing
"""

from __future__ import annotations

import structlog
from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis

from app.core.rate_limiter import get_rate_limit_config
from app.core.security import RateLimiter
from app.database import get_redis

logger = structlog.get_logger(__name__)


async def check_rate_limit(
    request: Request,
    operation: str = "default",
) -> None:
    """
    Check rate limit for a request.

    Raises HTTPException 429 if rate limit exceeded.

    Args:
        request: FastAPI request object
        operation: Rate limit operation key (e.g., "chat", "knowledge_search")
    """
    try:
        redis = get_redis()
        user_id = getattr(request.state, "user_id", "anonymous")
        identifier = f"{operation}:{user_id}"

        config = get_rate_limit_config(operation)
        limiter = RateLimiter(redis)

        await limiter.check(
            identifier=identifier,
            limit=config["requests"],
            window_seconds=config["window"],
            raise_on_exceeded=True,
        )

    except HTTPException:
        raise
    except Exception as e:
        # Log but allow request on Redis errors
        logger.error(
            "rate_limit_check_failed",
            operation=operation,
            error=str(e),
        )
