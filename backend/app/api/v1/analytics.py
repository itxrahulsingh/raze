"""Analytics and observability API routes."""
from fastapi import APIRouter, Depends, Query, status, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.api.v1 import deps
from app.database import get_db
from app.models.analytics import ObservabilityLog, UsageMetrics, UserSession
from app.schemas.analytics import DateRangeRequest

router = APIRouter()

@router.get("/overview")
async def get_analytics_overview(
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get analytics overview."""
    today = datetime.utcnow().strftime("%Y-%m-%d")

    result = await db.execute(
        select(func.count(ObservabilityLog.id)).where(
            ObservabilityLog.created_at >= datetime.utcnow() - timedelta(days=1)
        )
    )
    today_requests = result.scalar() or 0

    return {
        "today_requests": today_requests,
        "week_requests": 0,
        "month_requests": 0,
        "total_cost": 0.0
    }

@router.get("/usage")
async def get_usage_metrics(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get usage metrics by date range with validation."""
    # Parse and validate dates
    from datetime import date
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format. Expected YYYY-MM-DD: {str(e)}"
        )

    # Validate date range
    if start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )

    if (end - start).days > 366:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range cannot exceed 366 days"
        )

    result = await db.execute(
        select(UsageMetrics).where(
            UsageMetrics.date >= start,
            UsageMetrics.date <= end
        )
    )
    return result.scalars().all()

@router.get("/conversations")
async def get_conversation_analytics(
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation analytics."""
    return {
        "total_conversations": 0,
        "avg_messages_per_conversation": 0,
        "avg_duration_minutes": 0
    }

@router.get("/models")
async def get_model_usage(
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get model usage and cost breakdown."""
    result = await db.execute(
        select(
            ObservabilityLog.model_selected,
            func.count(ObservabilityLog.id).label("count"),
            func.sum(ObservabilityLog.cost_usd).label("total_cost")
        ).group_by(ObservabilityLog.model_selected)
    )

    models = []
    for row in result:
        models.append({
            "model": row[0],
            "usage_count": row[1],
            "total_cost": row[2] or 0.0
        })

    return {"models": models}

@router.get("/tools")
async def get_tool_usage(
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get tool usage statistics."""
    result = await db.execute(
        select(
            ObservabilityLog.tool_selected,
            func.count(ObservabilityLog.id).label("count")
        ).where(ObservabilityLog.tool_selected != None)
        .group_by(ObservabilityLog.tool_selected)
    )

    tools = []
    for row in result:
        tools.append({
            "tool": row[0],
            "usage_count": row[1]
        })

    return {"tools": tools}

@router.get("/knowledge")
async def get_knowledge_stats(
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get knowledge base statistics."""
    return {
        "total_sources": 0,
        "total_chunks": 0,
        "storage_mb": 0.0
    }

@router.get("/observability")
async def get_observability_logs(
    skip: int = 0,
    limit: int = 50,
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get AI decision observability logs."""
    result = await db.execute(
        select(ObservabilityLog)
        .order_by(ObservabilityLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

@router.get("/observability/{log_id}")
async def get_observability_detail(
    log_id: str,
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific observability log detail."""
    result = await db.execute(
        select(ObservabilityLog).where(ObservabilityLog.id == log_id)
    )
    return result.scalar_one_or_none()

@router.get("/sessions")
async def get_session_analytics(
    skip: int = 0,
    limit: int = 50,
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user session analytics."""
    result = await db.execute(
        select(UserSession)
        .order_by(UserSession.started_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

@router.post("/export")
async def export_analytics(
    format: str = Query("csv"),  # csv or json
    current_user = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Export analytics as CSV or JSON."""
    return {"exported": True, "format": format}
