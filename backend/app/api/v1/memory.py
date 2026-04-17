"""Memory management API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.v1 import deps
from app.core.memory_engine import MemoryEngine
from app.database import get_db
from app.models.memory import Memory, MemoryRetentionPolicy
from app.schemas.memory import MemoryCreate, MemoryResponse, MemoryUpdate, MemorySearchRequest

router = APIRouter()

@router.get("/", response_model=list[MemoryResponse])
async def list_memories(
    memory_type: str | None = Query(None),
    skip: int = Query(0, ge=0, le=1000),
    limit: int = Query(50, ge=1, le=100),
    request: Request,
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List memories for current user."""
    await deps.apply_rate_limit(request, "memory_list", 30, 60, current_user)
    stmt = select(Memory).where(Memory.user_id == current_user.id)
    if memory_type:
        stmt = stmt.where(Memory.type == memory_type)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/", response_model=MemoryResponse)
async def create_memory(
    data: MemoryCreate,
    request: Request,
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create memory."""
    await deps.apply_rate_limit(request, "memory_create", 30, 60, current_user)
    import uuid as _uuid
    memory = Memory(
        id=str(_uuid.uuid4()),
        user_id=str(current_user.id),
        session_id=data.session_id,
        type=data.type,
        content=data.content,
        importance_score=data.importance_score if data.importance_score is not None else 0.5,
        is_active=True,
    )
    db.add(memory)
    await db.commit()
    await db.refresh(memory)
    return memory

@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: str,
    request: Request,
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get memory detail - only own memories."""
    await deps.apply_rate_limit(request, "memory_get", 30, 60, current_user)
    result = await db.execute(
        select(Memory).where(
            (Memory.id == memory_id) & (Memory.user_id == current_user.id)
        )
    )
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory

@router.put("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: str,
    data: MemoryUpdate,
    request: Request,
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update memory."""
    await deps.apply_rate_limit(request, "memory_update", 30, 60, current_user)
    result = await db.execute(select(Memory).where(Memory.id == memory_id))
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404)

    if data.importance_score is not None:
        memory.importance_score = data.importance_score
    if data.content is not None:
        memory.content = data.content

    await db.commit()
    return memory

@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    request: Request,
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete memory."""
    await deps.apply_rate_limit(request, "memory_delete", 30, 60, current_user)
    result = await db.execute(select(Memory).where(Memory.id == memory_id))
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404)

    memory.is_active = False
    await db.commit()
    return {"deleted": True}

@router.post("/search")
async def search_memories(
    data: MemorySearchRequest,
    request: Request,
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Semantic search memories for current user."""
    await deps.apply_rate_limit(request, "memory_search", 30, 60, current_user)
    stmt = select(Memory).where(
        Memory.user_id == current_user.id,
        Memory.is_active == True,
    )
    if data.query:
        stmt = stmt.where(Memory.content.ilike(f"%{data.query}%"))
    stmt = stmt.order_by(Memory.importance_score.desc()).limit(20)
    result = await db.execute(stmt)
    return {"results": result.scalars().all()}

@router.get("/sessions/{session_id}")
async def get_session_context(
    session_id: str,
    request: Request,
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get context memory for a session owned by current user."""
    await deps.apply_rate_limit(request, "memory_session_get", 30, 60, current_user)
    stmt = select(Memory).where(
        Memory.session_id == session_id,
        Memory.user_id == current_user.id,
        Memory.is_active == True,
    ).order_by(Memory.created_at.asc())
    result = await db.execute(stmt)
    return {"messages": result.scalars().all()}

@router.delete("/sessions/{session_id}")
async def clear_session_context(
    session_id: str,
    request: Request,
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Clear session context."""
    await deps.apply_rate_limit(request, "memory_session_clear", 30, 60, current_user)
    return {"cleared": True}
