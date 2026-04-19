"""Tool management API routes."""
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.api.v1 import deps
from app.database import get_db
from app.models.tool import Tool, ToolExecution
from app.schemas.tool import ToolCreate, ToolUpdate, ToolResponse, ToolExecutionResponse

router = APIRouter()

@router.post("/", response_model=ToolResponse)
async def create_tool(
    data: ToolCreate,
    request: Request,
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create tool."""
    await deps.apply_rate_limit(request, "tools_create", 30, 60, current_user)
    tool = Tool(
        id=uuid.uuid4(),
        name=data.name,
        display_name=data.display_name,
        description=data.description,
        type=data.type,
        schema=data.tool_schema,
        endpoint_url=data.endpoint_url,
        method=data.method,
        timeout_seconds=data.timeout_seconds,
        max_retries=data.max_retries,
        auth_type=data.auth_type,
        auth_config=data.auth_config or {},
        default_headers=data.default_headers,
        is_active=True,
        requires_approval=data.requires_approval,
        tags=data.tags or [],
        tool_metadata=data.tool_metadata or {}
    )
    db.add(tool)
    await db.commit()
    await db.refresh(tool)
    return tool

@router.get("/", response_model=list[ToolResponse])
async def list_tools(
    request: Request,
    skip: int = Query(0, ge=0, le=1000),
    limit: int = Query(50, ge=1, le=100),
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List available tools - authenticated users only."""
    await deps.apply_rate_limit(request, "tools_list", 30, 60, current_user)
    result = await db.execute(
        select(Tool).where(Tool.is_active == True).offset(skip).limit(limit)
    )
    return result.scalars().all()

@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: str,
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get tool detail - authenticated users only."""
    result = await db.execute(
        select(Tool).where((Tool.id == tool_id) & (Tool.is_active == True))
    )
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool

@router.put("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: str,
    data: ToolUpdate,
    request: Request,
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update tool."""
    await deps.apply_rate_limit(request, "tools_update", 30, 60, current_user)
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    for field, value in data.model_dump(exclude_unset=True, by_alias=True).items():
        if field == "schema":
            setattr(tool, "schema", value)
        else:
            setattr(tool, field, value)

    await db.commit()
    await db.refresh(tool)
    return tool

@router.delete("/{tool_id}")
async def delete_tool(
    tool_id: str,
    request: Request,
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete tool."""
    await deps.apply_rate_limit(request, "tools_delete", 30, 60, current_user)
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    tool.is_active = False
    await db.commit()
    return {"deleted": True}

@router.post("/{tool_id}/test")
async def test_tool(
    tool_id: str,
    request: Request,
    input_data: dict = Body(...),
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Test tool execution - admin only."""
    await deps.apply_rate_limit(request, "tools_test", 10, 60, current_user)
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    try:
        from app.core.tool_engine import ToolEngine
        engine = ToolEngine(db)
        exec_result = await engine.execute_tool(
            tool_id=tool_id,
            input_data=input_data,
            conversation_id=None,
            user_id=current_user.id
        )
        return exec_result
    except Exception as e:
        return {
            "error": str(e),
            "tool_id": tool_id,
            "tool_name": tool.name,
            "success": False
        }

@router.get("/{tool_id}/executions")
async def get_tool_executions(
    tool_id: str,
    skip: int = Query(0, ge=0, le=10000),
    limit: int = Query(50, ge=1, le=100),
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get tool execution history - admin only."""
    result = await db.execute(
        select(ToolExecution)
        .where(ToolExecution.tool_id == tool_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

@router.get("/executions")
async def get_all_executions(
    skip: int = Query(0, ge=0, le=10000),
    limit: int = Query(50, ge=1, le=100),
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all recent tool executions - admin only."""
    result = await db.execute(
        select(ToolExecution)
        .order_by(ToolExecution.executed_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
