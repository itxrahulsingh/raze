"""
RAZE Enterprise AI OS – Background Tasks & Scheduled Jobs

Handles:
  - Memory decay (reduce importance over time)
  - Memory pruning (remove expired/low-value memories)
  - Knowledge source cleanup
  - Audit log archival
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import delete, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.memory import Memory, MemoryRetentionPolicy

logger = structlog.get_logger(__name__)
settings = get_settings()


async def apply_memory_decay() -> None:
    """
    Apply importance decay to all active memories.

    Memories fade over time based on their decay_rate and last access.
    """
    async with AsyncSessionLocal() as db:
        try:
            logger.info("memory_decay.starting")

            # Get all active memories
            result = await db.execute(select(Memory).where(Memory.is_active.is_(True)))
            memories = result.scalars().all()

            decayed_count = 0
            now = datetime.now(UTC)

            for memory in memories:
                if not memory.decay_rate:
                    continue

                # Calculate days since last access
                last_access = memory.last_accessed or memory.created_at
                if not last_access:
                    continue

                days_inactive = (now - last_access).days
                if days_inactive == 0:
                    continue

                # Apply decay: importance *= (1 - decay_rate) ^ days_inactive
                decay_factor = (1.0 - memory.decay_rate) ** days_inactive
                new_score = memory.importance_score * decay_factor

                if new_score < 0.01:
                    new_score = 0.0

                memory.importance_score = max(0.0, min(1.0, new_score))
                decayed_count += 1

            await db.commit()
            logger.info("memory_decay.completed", decayed_count=decayed_count)

        except Exception as e:
            logger.error("memory_decay.failed", error=str(e))


async def prune_expired_memories() -> None:
    """Remove memories that have expired or fallen below importance threshold."""
    async with AsyncSessionLocal() as db:
        try:
            logger.info("memory_prune.starting")

            now = datetime.now(UTC)
            pruned_count = 0

            # Delete expired memories
            expired_result = await db.execute(
                delete(Memory).where(
                    Memory.is_active.is_(True),
                    Memory.expires_at.is_not(None),
                    Memory.expires_at <= now,
                )
            )
            pruned_count += expired_result.rowcount or 0

            # Get retention policies
            policy_result = await db.execute(
                select(MemoryRetentionPolicy).where(MemoryRetentionPolicy.is_active.is_(True))
            )
            policies = policy_result.scalars().all()

            # Apply per-type pruning
            for policy in policies:
                if not policy.max_count:
                    continue

                # Get memories of this type
                type_result = await db.execute(
                    select(Memory)
                    .where(Memory.type == policy.type, Memory.is_active.is_(True))
                    .order_by(desc(Memory.importance_score), desc(Memory.created_at))
                )
                type_memories = type_result.scalars().all()

                # If over limit, mark oldest/least important for deletion
                if len(type_memories) > policy.max_count:
                    to_delete = len(type_memories) - policy.max_count
                    for mem in type_memories[-to_delete:]:
                        mem.is_active = False
                        pruned_count += 1

                # Apply min_importance threshold
                if policy.min_importance and policy.min_importance > 0:
                    low_importance_result = await db.execute(
                        delete(Memory).where(
                            Memory.type == policy.type,
                            Memory.is_active.is_(True),
                            Memory.importance_score < policy.min_importance,
                        )
                    )
                    pruned_count += low_importance_result.rowcount or 0

            await db.commit()
            logger.info("memory_prune.completed", pruned_count=pruned_count)

        except Exception as e:
            logger.error("memory_prune.failed", error=str(e))


async def cleanup_old_audit_logs(days: int = 90) -> None:
    """Archive or delete old audit logs beyond retention period."""
    async with AsyncSessionLocal() as db:
        try:
            logger.info("audit_log_cleanup.starting", retention_days=days)

            from app.models.system import AuditLog

            cutoff_date = datetime.now(UTC) - timedelta(days=days)

            result = await db.execute(
                delete(AuditLog).where(AuditLog.created_at < cutoff_date)
            )
            deleted_count = result.rowcount or 0

            await db.commit()
            logger.info("audit_log_cleanup.completed", deleted_count=deleted_count)

        except Exception as e:
            logger.error("audit_log_cleanup.failed", error=str(e))


async def run_all_background_tasks() -> None:
    """Run all background maintenance tasks."""
    logger.info("background_tasks.starting")

    try:
        await apply_memory_decay()
        await prune_expired_memories()
        await cleanup_old_audit_logs()
        logger.info("background_tasks.all_completed")
    except Exception as e:
        logger.error("background_tasks.failed", error=str(e))
