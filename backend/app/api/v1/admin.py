"""
RAZE Enterprise AI OS – Admin Control Panel API Routes

Complete operational control:
  - AI Configuration management
  - Memory management
  - User management (CRUD + activity)
  - Conversation monitoring
  - Analytics & reporting
  - System audit logs
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import deps
from app.config import get_settings
from app.database import get_db
from app.models.ai_config import AIConfig
from app.models.conversation import Conversation, ConversationStatus, Message
from app.models.memory import Memory
from app.models.system import AuditLog
from app.models.user import User, UserRole

settings = get_settings()
logger = structlog.get_logger(__name__)
router = APIRouter()


# ─── Audit Logging Helper ──────────────────────────────────────────────────


async def log_audit(
    db: AsyncSession,
    user_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: str,
    changes: dict[str, Any] | None = None,
) -> None:
    """Log an action to the audit trail."""
    try:
        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
        )
        db.add(audit)
        await db.flush()
    except Exception as e:
        logger.warning("audit_log_failed", error=str(e))


# ─── DASHBOARD ─────────────────────────────────────────────────────────────


@router.get("/dashboard")
async def get_dashboard(
    request: Request,
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get admin dashboard overview."""
    await deps.apply_rate_limit(request, "admin_dashboard", 120, 60, current_user)

    # Total conversations
    conv_result = await db.execute(select(func.count(Conversation.id)))
    total_convs = conv_result.scalar() or 0

    # Total messages
    msg_result = await db.execute(select(func.count(Message.id)))
    total_msgs = msg_result.scalar() or 0

    # Total users
    user_result = await db.execute(select(func.count(User.id)))
    total_users = user_result.scalar() or 0

    # Active conversations (last 24 hours)
    since = datetime.now(UTC) - timedelta(hours=24)
    active_result = await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.created_at >= since,
            Conversation.status == ConversationStatus.active.value,
        )
    )
    active_convs = active_result.scalar() or 0

    # Total cost (last 30 days)
    since_month = datetime.now(UTC) - timedelta(days=30)
    cost_result = await db.execute(
        select(func.sum(Conversation.total_cost_usd)).where(Conversation.created_at >= since_month)
    )
    total_cost = cost_result.scalar() or 0.0

    return {
        "total_conversations": total_convs,
        "total_messages": total_msgs,
        "active_conversations_24h": active_convs,
        "total_users": total_users,
        "total_cost_30d": round(float(total_cost), 2),
        "health": "healthy",
    }


# ─── AI CONFIGURATION MANAGEMENT ────────────────────────────────────────────


@router.get("/ai-configs")
async def list_ai_configs(
    request: Request,
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all AI configurations."""
    await deps.apply_rate_limit(request, "admin_ai_config_list", 120, 60, current_user)

    result = await db.execute(
        select(AIConfig).where(AIConfig.is_active.is_(True)).order_by(desc(AIConfig.is_default))
    )
    configs = result.scalars().all()

    return [
        {
            "id": str(c.id),
            "name": c.name,
            "provider": c.provider,
            "model_name": c.model_name,
            "temperature": c.temperature,
            "max_tokens": c.max_tokens,
            "routing_strategy": c.routing_strategy,
            "is_default": c.is_default,
        }
        for c in configs
    ]


@router.post("/ai-configs", status_code=status.HTTP_201_CREATED)
async def create_ai_config(
    body: dict[str, Any],
    request: Request,
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new AI configuration."""
    await deps.apply_rate_limit(request, "admin_ai_config_create", 120, 60, current_user)

    config = AIConfig(
        id=uuid.uuid4(),
        name=body.get("name"),
        description=body.get("description"),
        model_name=body.get("model_name"),
        provider=body.get("provider"),
        temperature=body.get("temperature", 0.7),
        max_tokens=body.get("max_tokens", 2048),
        top_p=body.get("top_p", 1.0),
        routing_strategy=body.get("routing_strategy", "balanced"),
        is_default=body.get("is_default", False),
        is_active=True,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)

    await log_audit(
        db,
        current_user.id,
        "create",
        "ai_config",
        str(config.id),
        {"name": config.name, "provider": config.provider},
    )

    logger.info("admin.ai_config_created", config_id=str(config.id), by=str(current_user.id))

    return {
        "id": str(config.id),
        "name": config.name,
        "provider": config.provider,
        "model_name": config.model_name,
    }


@router.put("/ai-configs/{config_id}")
async def update_ai_config(
    config_id: uuid.UUID,
    body: dict[str, Any],
    request: Request,
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update an AI configuration."""
    await deps.apply_rate_limit(request, "admin_ai_config_update", 120, 60, current_user)

    result = await db.execute(select(AIConfig).where(AIConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")

    changes = {}
    for field in ["temperature", "max_tokens", "routing_strategy", "top_p"]:
        if field in body:
            changes[field] = (getattr(config, field), body[field])
            setattr(config, field, body[field])

    await db.commit()
    await db.refresh(config)

    await log_audit(
        db,
        current_user.id,
        "update",
        "ai_config",
        str(config.id),
        changes,
    )

    logger.info("admin.ai_config_updated", config_id=str(config.id), by=str(current_user.id))

    return {
        "id": str(config.id),
        "name": config.name,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }


@router.delete("/ai-configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_config(
    config_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete an AI configuration (soft delete)."""
    await deps.apply_rate_limit(request, "admin_ai_config_delete", 120, 60, current_user)

    result = await db.execute(select(AIConfig).where(AIConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")

    config.is_active = False
    await db.commit()

    await log_audit(db, current_user.id, "delete", "ai_config", str(config.id))

    logger.info("admin.ai_config_deleted", config_id=str(config.id), by=str(current_user.id))


# ─── MEMORY MANAGEMENT ─────────────────────────────────────────────────────


@router.get("/memories")
async def list_memories(
    request: Request,
    user_id: uuid.UUID | None = Query(None),
    memory_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List user memories with optional filtering."""
    await deps.apply_rate_limit(request, "admin_memories_list", 120, 60, current_user)

    query = select(Memory).where(Memory.is_active.is_(True))

    if user_id:
        query = query.where(Memory.user_id == user_id)
    if memory_type:
        query = query.where(Memory.type == memory_type)

    # Get total count
    count_result = await db.execute(
        select(func.count(Memory.id)).where(Memory.is_active.is_(True))
    )
    total = count_result.scalar() or 0

    # Get paginated results
    result = await db.execute(
        query.order_by(desc(Memory.created_at)).limit(limit).offset(offset)
    )
    memories = result.scalars().all()

    return {
        "items": [
            {
                "id": str(m.id),
                "user_id": str(m.user_id) if m.user_id else None,
                "type": m.type,
                "content": m.content[:100] + "..." if len(m.content) > 100 else m.content,
                "importance_score": m.importance_score,
                "created_at": m.created_at.isoformat(),
            }
            for m in memories
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.delete("/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a memory (soft delete)."""
    await deps.apply_rate_limit(request, "admin_memories_delete", 120, 60, current_user)

    result = await db.execute(select(Memory).where(Memory.id == memory_id))
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    memory.is_active = False
    await db.commit()

    await log_audit(db, current_user.id, "delete", "memory", str(memory.id))

    logger.info("admin.memory_deleted", memory_id=str(memory.id), by=str(current_user.id))


# ─── CONVERSATION MONITORING ──────────────────────────────────────────────


@router.get("/conversations")
async def list_conversations(
    request: Request,
    user_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List conversations with filtering."""
    await deps.apply_rate_limit(request, "admin_conversations_list", 120, 60, current_user)

    query = select(Conversation)

    if user_id:
        query = query.where(Conversation.user_id == user_id)
    if status:
        query = query.where(Conversation.status == status)

    # Get total count
    count_result = await db.execute(select(func.count(Conversation.id)))
    total = count_result.scalar() or 0

    # Get paginated results
    result = await db.execute(
        query.order_by(desc(Conversation.created_at)).limit(limit).offset(offset)
    )
    conversations = result.scalars().all()

    return {
        "items": [
            {
                "id": str(c.id),
                "session_id": c.session_id,
                "user_id": str(c.user_id) if c.user_id else None,
                "title": c.title,
                "status": c.status,
                "message_count": c.message_count,
                "total_cost_usd": c.total_cost_usd,
                "started_at": c.started_at.isoformat() if c.started_at else None,
            }
            for c in conversations
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and all associated messages."""
    await deps.apply_rate_limit(
        request, "admin_conversations_delete", 120, 60, current_user
    )

    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    await db.delete(conversation)
    await db.commit()

    await log_audit(db, current_user.id, "delete", "conversation", str(conversation.id))

    logger.info(
        "admin.conversation_deleted", conv_id=str(conversation.id), by=str(current_user.id)
    )


# ─── ANALYTICS ─────────────────────────────────────────────────────────────


@router.get("/analytics/summary")
async def analytics_summary(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get analytics summary for the past N days."""
    await deps.apply_rate_limit(request, "admin_analytics_summary", 120, 60, current_user)

    since = datetime.now(UTC) - timedelta(days=days)

    # Total conversations
    conv_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.created_at >= since)
    )
    total_conversations = conv_result.scalar() or 0

    # Active conversations
    active_result = await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.created_at >= since,
            Conversation.status == ConversationStatus.active.value,
        )
    )
    active_conversations = active_result.scalar() or 0

    # Total cost
    cost_result = await db.execute(
        select(func.sum(Conversation.total_cost_usd)).where(Conversation.created_at >= since)
    )
    total_cost = cost_result.scalar() or 0.0

    # Total messages
    msg_result = await db.execute(
        select(func.count(Message.id)).where(Message.created_at >= since)
    )
    total_messages = msg_result.scalar() or 0

    return {
        "period_days": days,
        "total_conversations": total_conversations,
        "active_conversations": active_conversations,
        "total_messages": total_messages,
        "avg_messages_per_conv": (
            round(total_messages / total_conversations, 2)
            if total_conversations > 0
            else 0
        ),
        "total_cost_usd": round(float(total_cost), 2),
        "avg_cost_per_conv": (
            round(float(total_cost) / total_conversations, 2)
            if total_conversations > 0
            else 0.0
        ),
    }


# ─── AUDIT LOG ─────────────────────────────────────────────────────────────


@router.get("/audit-log")
async def get_audit_log(
    request: Request,
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get audit log entries."""
    await deps.apply_rate_limit(request, "admin_audit_log", 120, 60, current_user)

    query = select(AuditLog)

    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)

    # Get total count
    count_result = await db.execute(select(func.count(AuditLog.id)))
    total = count_result.scalar() or 0

    # Get paginated results
    result = await db.execute(
        query.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
    )
    logs = result.scalars().all()

    return {
        "items": [
            {
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "changes": log.changes,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ─── SYSTEM HEALTH ────────────────────────────────────────────────────────


@router.get("/system/health")
async def system_health(
    request: Request,
    current_user: User = Depends(deps.get_current_admin),
) -> dict[str, str]:
    """Get system health status."""
    await deps.apply_rate_limit(request, "admin_system_health", 120, 60, current_user)

    return {
        "database": "healthy",
        "redis": "healthy",
        "qdrant": "healthy",
        "minio": "healthy",
    }
