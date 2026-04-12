"""Memory management API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
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
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List memories for current user."""
    stmt = select(Memory).where(Memory.user_id == current_user.id)
    if memory_type:
        stmt = stmt.where(Memory.type == memory_type)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/", response_model=MemoryResponse)
async def create_memory(
    data: MemoryCreate,
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create memory."""
    from app.core.memory_engine import MemoryEngine
    from app.core.llm_router import LLMRouter
    from app.core.vector_search import VectorSearchEngine

    memory_engine = MemoryEngine(db, None, None, None)
    memory = await memory_engine.store_memory(
        current_user.id, data.session_id, data.type,
        data.content, data.importance_score
    )
    return memory

@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: str,
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get memory detail - only own memories."""
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
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update memory."""
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
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete memory."""
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
    db: AsyncSession = Depends(get_db)
):
    """Semantic search memories."""
    return {"results": []}

@router.get("/sessions/{session_id}")
async def get_session_context(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get context memory for session."""
    return {"messages": []}

@router.delete("/sessions/{session_id}")
async def clear_session_context(
    session_id: str,
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Clear session context."""
    return {"cleared": True}
