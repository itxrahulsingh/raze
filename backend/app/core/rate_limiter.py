"""
RAZE Enterprise AI OS – Rate Limiting Configuration

Provides centralized rate limit policies for all operations.
Actual enforcement uses RateLimiter from app.core.security.
"""

from __future__ import annotations


# Rate limit configurations: requests per window_seconds
RATE_LIMITS = {
    # Public endpoints
    "chat": {"requests": 30, "window": 60},  # 30/min
    "knowledge_search": {"requests": 120, "window": 60},  # 120/min
    "memory_search": {"requests": 60, "window": 60},  # 60/min

    # Admin endpoints
    "admin_ai_config": {"requests": 10, "window": 60},  # 10/min
    "admin_memories": {"requests": 20, "window": 60},  # 20/min
    "admin_conversations": {"requests": 20, "window": 60},  # 20/min
    "admin_analytics": {"requests": 30, "window": 60},  # 30/min

    # Tool execution
    "tools_execute": {"requests": 50, "window": 60},  # 50/min
    "tools_test": {"requests": 10, "window": 60},  # 10/min

    # File operations
    "file_upload": {"requests": 10, "window": 60},  # 10/min
    "file_download": {"requests": 100, "window": 60},  # 100/min

    # Knowledge operations
    "knowledge_ingest": {"requests": 5, "window": 60},  # 5/min
    "knowledge_delete": {"requests": 5, "window": 60},  # 5/min

    # Default
    "default": {"requests": 60, "window": 60},  # 60/min
}


def get_rate_limit_config(operation: str) -> dict[str, int]:
    """Get rate limit config for operation."""
    return RATE_LIMITS.get(operation, RATE_LIMITS["default"])
