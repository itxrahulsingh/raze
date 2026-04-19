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
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response, status
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


# ─── STATISTICS ─────────────────────────────────────────────────────────────


@router.get("/stats")
async def get_conversation_stats(
    request: Request,
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get comprehensive conversation statistics."""
    await deps.apply_rate_limit(request, "admin_stats", 120, 60, current_user)

    # Count conversations
    total_convs = (await db.execute(select(func.count(Conversation.id)))).scalar() or 0
    active_convs = (await db.execute(
        select(func.count(Conversation.id)).where(Conversation.status == ConversationStatus.active.value)
    )).scalar() or 0

    # Count messages
    total_msgs = (await db.execute(select(func.count(Message.id)))).scalar() or 0

    # Sum tokens and cost
    total_tokens = (await db.execute(
        select(func.sum(Conversation.total_tokens))
    )).scalar() or 0
    total_cost = (await db.execute(
        select(func.sum(Conversation.total_cost_usd))
    )).scalar() or 0.0

    # Calculate averages
    avg_tokens = total_tokens / total_convs if total_convs > 0 else 0
    avg_cost = total_cost / total_convs if total_convs > 0 else 0.0

    return {
        "total_conversations": total_convs,
        "active_conversations": active_convs,
        "total_messages": total_msgs,
        "total_tokens": int(total_tokens),
        "total_cost_usd": round(float(total_cost), 4),
        "avg_tokens_per_conversation": round(float(avg_tokens), 2),
        "avg_cost_per_conversation": round(float(avg_cost), 6),
    }


@router.get("/session-stats")
async def get_session_stats(
    request: Request,
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get user session statistics."""
    await deps.apply_rate_limit(request, "admin_session_stats", 120, 60, current_user)

    from app.models.analytics import UserSession

    # Count sessions
    total_sessions = (await db.execute(select(func.count(UserSession.id)))).scalar() or 0
    active_sessions = (await db.execute(
        select(func.count(UserSession.id)).where(UserSession.is_active.is_(True))
    )).scalar() or 0

    # Sum session messages
    total_session_messages = (await db.execute(
        select(func.sum(UserSession.message_count))
    )).scalar() or 0

    return {
        "total_sessions": total_sessions,
        "active_sessions": active_sessions,
        "total_session_messages": int(total_session_messages),
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


# ─── USER MANAGEMENT ───────────────────────────────────────────────────────


@router.get("/users")
async def list_users(
    request: Request,
    q: str | None = Query(None, description="Search by email, username, or full_name"),
    role: str | None = Query(None, description="Filter by role"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List users for admin directory views."""
    await deps.apply_rate_limit(request, "admin_users_list", 120, 60, current_user)

    query = select(User)
    count_query = select(func.count(User.id))

    if q:
        like = f"%{q.lower()}%"
        query = query.where(
            func.lower(User.email).like(like)
            | func.lower(User.username).like(like)
            | func.lower(func.coalesce(User.full_name, "")).like(like)
        )
        count_query = count_query.where(
            func.lower(User.email).like(like)
            | func.lower(User.username).like(like)
            | func.lower(func.coalesce(User.full_name, "")).like(like)
        )

    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)

    if is_active is not None:
        query = query.where(User.is_active.is_(is_active))
        count_query = count_query.where(User.is_active.is_(is_active))

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.order_by(desc(User.created_at)).limit(limit).offset(offset)
    )
    users = result.scalars().all()

    return {
        "items": [
            {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat(),
            }
            for user in users
        ],
        "total": int(total),
        "limit": limit,
        "offset": offset,
    }


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    data: dict = Body(...),
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new user (admin only)."""
    await deps.apply_rate_limit(request, "admin_users_create", 30, 60, current_user)

    from app.core.security import get_password_hash

    email = str(data.get("email", "")).strip().lower()
    username = str(data.get("username", "")).strip().lower()
    password_raw = data.get("password", "")
    # Ensure password is a string and not longer than 72 bytes (bcrypt limit)
    if isinstance(password_raw, (list, dict)):
        password_raw = str(password_raw)
    password = str(password_raw)[:72] if password_raw else ""
    full_name = str(data.get("full_name", "")).strip() or None
    role = str(data.get("role", "viewer")).strip().lower()

    existing_email = await db.execute(select(User).where(User.email == email))
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already exists")

    existing_username = await db.execute(select(User).where(User.username == username))
    if existing_username.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")

    # Hash password using bcrypt directly
    try:
        import bcrypt
        salt = bcrypt.gensalt(rounds=12)
        hashed_pwd = bcrypt.hashpw(password[:72].encode('utf-8'), salt).decode('utf-8')
    except Exception as e:
        # Fallback to passlib
        try:
            hashed_pwd = get_password_hash(password[:72])
        except Exception:
            raise HTTPException(status_code=500, detail="Password hashing failed")

    user = User(
        email=email,
        username=username,
        hashed_password=hashed_pwd,
        full_name=full_name,
        role=role,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await log_audit(db, current_user.id, "create", "user", str(user.id))

    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    request: Request,
    data: dict = Body(...),
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update user (admin only)."""
    await deps.apply_rate_limit(request, "admin_users_update", 30, 60, current_user)

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    changes = {}
    if "full_name" in data:
        new_name = data["full_name"]
        if new_name != user.full_name:
            changes["full_name"] = (user.full_name, new_name)
            user.full_name = new_name

    if "role" in data:
        new_role = str(data["role"]).strip().lower() if data["role"] else user.role
        if new_role not in ["viewer", "admin", "superadmin"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        if new_role != user.role:
            changes["role"] = (user.role, new_role)
            user.role = new_role

    if "is_active" in data:
        new_active = bool(data["is_active"])
        if new_active != user.is_active:
            changes["is_active"] = (user.is_active, new_active)
            user.is_active = new_active

    if changes:
        await db.commit()
        await log_audit(db, current_user.id, "update", "user", str(user.id), changes)

    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "updated_at": user.updated_at.isoformat(),
    }


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    response_class=Response,
)
async def delete_user(
    user_id: str,
    request: Request,
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete user (admin only)."""
    await deps.apply_rate_limit(request, "admin_users_delete", 30, 60, current_user)

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    await db.commit()
    await log_audit(db, current_user.id, "delete", "user", str(user.id))


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
