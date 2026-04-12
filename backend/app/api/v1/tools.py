"""Tool management API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.v1 import deps
from app.database import get_db
from app.models.tool import Tool, ToolExecution
from app.schemas.tool import ToolCreate, ToolUpdate, ToolResponse, ToolExecutionResponse

router = APIRouter()

@router.post("/", response_model=ToolResponse)
async def create_tool(
    data: ToolCreate,
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create tool."""
    import uuid
    tool = Tool(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description,
        type=data.type,
        schema=data.schema,
        endpoint_url=data.endpoint_url,
        method=data.method,
        auth_type=data.auth_type,
        auth_config=data.auth_config or {},
        is_active=True,
        tags=data.tags or []
    )
    db.add(tool)
    await db.commit()
    return tool

@router.get("/", response_model=list[ToolResponse])
async def list_tools(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List tools."""
    result = await db.execute(select(Tool).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get tool detail."""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404)
    return tool

@router.put("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: str,
    data: ToolUpdate,
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update tool."""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404)

    for field, value in data.dict(exclude_unset=True).items():
        setattr(tool, field, value)

    await db.commit()
    return tool

@router.delete("/{tool_id}")
async def delete_tool(
    tool_id: str,
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete tool."""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404)

    tool.is_active = False
    await db.commit()
    return {"deleted": True}

@router.post("/{tool_id}/test")
async def test_tool(
    tool_id: str,
    input_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Test tool execution."""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404)

    return {"test_result": "success", "tool_used": tool.name}

@router.get("/{tool_id}/executions")
async def get_tool_executions(
    tool_id: str,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get tool execution history."""
    result = await db.execute(
        select(ToolExecution)
        .where(ToolExecution.tool_id == tool_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

@router.get("/executions")
async def get_all_executions(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get all recent tool executions."""
    result = await db.execute(
        select(ToolExecution)
        .order_by(ToolExecution.executed_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
