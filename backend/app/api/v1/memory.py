"""Memory management API routes."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.api.v1 import deps
from app.core.memory_engine import MemoryEngine
from app.core.vector_search import VectorSearchEngine
from app.core.llm_router import LLMRouter
from app.database import get_db, get_redis
from app.models.memory import Memory, MemoryRetentionPolicy
from app.schemas.memory import MemoryCreate, MemoryResponse, MemoryUpdate, MemorySearchRequest

router = APIRouter()

@router.get("/", response_model=list[MemoryResponse])
async def list_memories(
    request: Request,
    memory_type: str | None = Query(None),
    skip: int = Query(0, ge=0, le=1000),
    limit: int = Query(50, ge=1, le=100),
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
    """Create memory with embeddings and vector storage."""
    await deps.apply_rate_limit(request, "memory_create", 30, 60, current_user)
    redis = get_redis()
    engine = MemoryEngine(db, redis, VectorSearchEngine(), LLMRouter())
    memory = await engine.store_memory(
        user_id=str(current_user.id),
        session_id=data.session_id,
        memory_type=data.type.value if hasattr(data.type, 'value') else data.type,
        content=data.content,
        importance_score=data.importance_score if data.importance_score is not None else 0.5,
        metadata=data.mem_metadata,
    )
    await db.commit()
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
            (Memory.id == memory_id) & (Memory.user_id == str(current_user.id))
        )
    )
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    # Update access tracking
    memory.access_count = (memory.access_count or 0) + 1
    memory.last_accessed = datetime.utcnow()
    await db.commit()

    return memory

@router.put("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: str,
    data: MemoryUpdate,
    request: Request,
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update memory - user can update their own memories."""
    await deps.apply_rate_limit(request, "memory_update", 30, 60, current_user)
    result = await db.execute(
        select(Memory).where(
            (Memory.id == memory_id) & (Memory.user_id == str(current_user.id))
        )
    )
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

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
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete memory - user can delete their own memories."""
    await deps.apply_rate_limit(request, "memory_delete", 30, 60, current_user)
    result = await db.execute(
        select(Memory).where(
            (Memory.id == memory_id) & (Memory.user_id == str(current_user.id))
        )
    )
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

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
    redis = get_redis()
    engine = MemoryEngine(db, redis, VectorSearchEngine(), LLMRouter())

    results = await engine.search_memories(
        user_id=str(current_user.id),
        query=data.query,
        memory_types=[t.value if hasattr(t, 'value') else t for t in data.types] if data.types else None,
        top_k=data.limit or 20,
        min_importance=data.min_importance or 0.0,
    )

    # Update access tracking for returned items
    now = datetime.utcnow()
    for mem in results:
        mem.access_count = (mem.access_count or 0) + 1
        mem.last_accessed = now
    await db.commit()

    return {"results": results, "total_found": len(results)}

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
        Memory.user_id == str(current_user.id),
        Memory.is_active == True,
    ).order_by(Memory.created_at.asc())
    result = await db.execute(stmt)
    return {"messages": result.scalars().all()}


@router.get("/retention-policies")
async def get_retention_policies(
    request: Request,
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all active retention policies."""
    await deps.apply_rate_limit(request, "memory_policies", 30, 60, current_user)
    stmt = select(MemoryRetentionPolicy).where(MemoryRetentionPolicy.is_active == True)
    result = await db.execute(stmt)
    policies = result.scalars().all()
    return {"policies": policies}

@router.delete("/sessions/{session_id}")
async def clear_session_context(
    session_id: str,
    request: Request,
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Clear session context - user can clear their own sessions."""
    await deps.apply_rate_limit(request, "memory_session_clear", 30, 60, current_user)
    redis = get_redis()
    engine = MemoryEngine(db, redis, VectorSearchEngine(), LLMRouter())
    await engine.clear_context(session_id)

    # Also soft-delete session memories in DB
    stmt = update(Memory).where(
        (Memory.session_id == session_id) & (Memory.user_id == str(current_user.id))
    ).values(is_active=False)
    await db.execute(stmt)
    await db.commit()

    return {"cleared": True}
