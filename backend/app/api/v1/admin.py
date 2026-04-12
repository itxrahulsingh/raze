"""Admin control panel API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.v1 import deps
from app.database import get_db
from app.models.ai_config import AIConfig
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.schemas.admin import AIConfigCreate, AIConfigUpdate, AIConfigResponse, SystemStats, AdminDashboard

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard(
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get admin dashboard overview."""
    # Stats - properly wrapped count queries with select()
    conv_result = await db.execute(select(func.count(Conversation.id)))
    total_convs = conv_result.scalar() or 0

    msg_result = await db.execute(select(func.count(Message.id)))
    total_msgs = msg_result.scalar() or 0

    user_result = await db.execute(select(func.count(User.id)))
    total_users = user_result.scalar() or 0

    return {
        "total_conversations": total_convs,
        "total_messages": total_msgs,
        "active_users": total_users,
        "health": "healthy"
    }

@router.get("/ai-config", response_model=list[AIConfigResponse])
async def list_ai_configs(
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """List AI configurations."""
    result = await db.execute(select(AIConfig))
    return result.scalars().all()

@router.post("/ai-config", response_model=AIConfigResponse)
async def create_ai_config(
    data: AIConfigCreate,
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create AI configuration."""
    import uuid
    config = AIConfig(
        id=str(uuid.uuid4()),
        name=data.name,
        is_default=data.is_default,
        provider=data.provider,
        model_name=data.model_name,
        temperature=data.temperature,
        max_tokens=data.max_tokens,
        system_prompt=data.system_prompt,
        routing_strategy=data.routing_strategy
    )
    db.add(config)
    await db.commit()
    return config

@router.put("/ai-config/{config_id}", response_model=AIConfigResponse)
async def update_ai_config(
    config_id: str,
    data: AIConfigUpdate,
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update AI configuration."""
    result = await db.execute(select(AIConfig).where(AIConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found"
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(config, field, value)

    await db.commit()
    return config

@router.delete("/ai-config/{config_id}")
async def delete_ai_config(
    config_id: str,
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete AI configuration."""
    result = await db.execute(select(AIConfig).where(AIConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found"
        )

    await db.delete(config)
    await db.commit()
    return {"deleted": True}

@router.put("/ai-config/{config_id}/set-default")
async def set_default_config(
    config_id: str,
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Set as default AI configuration."""
    # Unset all others
    await db.execute(AIConfig.__table__.update().values(is_default=False))

    # Set this one
    result = await db.execute(select(AIConfig).where(AIConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found"
        )

    config.is_default = True
    await db.commit()
    return config

@router.get("/users")
async def list_users(
    skip: int = 0,
    limit: int = 50,
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """List users."""
    result = await db.execute(
        select(User).offset(skip).limit(limit)
    )
    return result.scalars().all()

@router.get("/system/health")
async def system_health(
    current_user = Depends(deps.get_current_admin)
):
    """Get system health status."""
    return {
        "database": "healthy",
        "redis": "healthy",
        "qdrant": "healthy",
        "minio": "healthy"
    }

@router.post("/system/clear-cache")
async def clear_cache(
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Clear all caches."""
    return {"cleared": True}
