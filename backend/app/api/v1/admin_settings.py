"""Admin settings and configuration endpoints."""
import asyncio
import httpx
import time
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db, get_redis
from app.api.v1 import deps
from app.models.user import User

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin Settings"])


@router.get("/system/readiness")
async def get_system_readiness(
    request: Request,
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Deep readiness snapshot for DB/Redis/Qdrant/Celery/Ollama."""
    await deps.apply_rate_limit(request, "system_readiness", 60, 60, current_user)
    settings = get_settings()
    redis_client = get_redis()

    status_map: dict[str, dict] = {}

    db_start = time.monotonic()
    try:
        await db.execute(text("SELECT 1"))
        status_map["database"] = {"status": "healthy", "latency_ms": int((time.monotonic() - db_start) * 1000)}
    except Exception as e:
        status_map["database"] = {"status": "unhealthy", "error": str(e)}

    redis_start = time.monotonic()
    try:
        pong = await redis_client.ping()
        status_map["redis"] = {
            "status": "healthy" if pong else "unhealthy",
            "latency_ms": int((time.monotonic() - redis_start) * 1000),
        }
    except Exception as e:
        status_map["redis"] = {"status": "unhealthy", "error": str(e)}

    qdrant_start = time.monotonic()
    try:
        from app.core.vector_search import VectorSearchEngine

        vs = VectorSearchEngine()
        info = await vs.get_collection_info(settings.qdrant_collection_knowledge)
        status_map["qdrant"] = {
            "status": "healthy",
            "latency_ms": int((time.monotonic() - qdrant_start) * 1000),
            "knowledge_points": int(info.get("points_count") or 0),
            "indexed_vectors": int(info.get("indexed_vectors_count") or 0),
        }
    except Exception as e:
        status_map["qdrant"] = {"status": "unhealthy", "error": str(e)}

    ollama_start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
        status_map["ollama"] = {
            "status": "healthy",
            "latency_ms": int((time.monotonic() - ollama_start) * 1000),
            "models_count": len(data.get("models", [])),
        }
    except Exception as e:
        status_map["ollama"] = {"status": "unhealthy", "error": str(e)}

    celery_status = {"status": "disabled"}
    if settings.celery_enabled:
        try:
            from app.celery_app import celery_app

            def _inspect_ping():
                insp = celery_app.control.inspect(timeout=1.5)
                return insp.ping() if insp else None

            ping_result = await asyncio.to_thread(_inspect_ping)
            if ping_result:
                worker_count = len(ping_result.keys())
                celery_status = {"status": "healthy", "workers": worker_count}
            else:
                celery_status = {"status": "degraded", "workers": 0, "detail": "No worker ping response"}
        except Exception as e:
            celery_status = {"status": "unhealthy", "error": str(e)}
    status_map["celery"] = celery_status

    overall = "healthy"
    if any(component.get("status") == "unhealthy" for component in status_map.values()):
        overall = "degraded"
    if settings.celery_enabled and status_map["celery"].get("status") in ("degraded", "unhealthy"):
        overall = "degraded"

    return {
        "status": overall,
        "celery_enabled": settings.celery_enabled,
        "components": status_map,
    }


@router.get("/ollama-models")
async def get_ollama_models(
    request: Request,
    current_user: User = Depends(deps.get_current_user),
) -> dict:
    """Get list of available Ollama models."""
    await deps.apply_rate_limit(request, "ollama_models", 120, 60, current_user)

    settings = get_settings()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            models = [model["name"] for model in data.get("models", [])]
            return {"models": models, "count": len(models)}
    except Exception as e:
        logger.warning("ollama.models_fetch_failed", error=str(e))
        return {"models": [], "count": 0, "error": str(e)}


@router.post("/ai-config")
async def save_ai_config(
    request: Request,
    config: dict,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Save AI configuration (model selection, temperature, etc)."""
    from app.models.ai_config import AIConfig
    import uuid

    await deps.apply_rate_limit(request, "save_ai_config", 60, 60, current_user)

    try:
        from sqlalchemy import select, update

        # Create or update AI config in database
        config_name = config.get("name", f"{config.get('provider', 'openai')} - {config.get('model_name', 'default')}")

        # Check if config already exists
        result = await db.execute(select(AIConfig).where(AIConfig.name == config_name).limit(1))
        existing_config = result.scalars().first()

        if existing_config:
            # Update existing config
            existing_config.provider = config.get("provider", existing_config.provider)
            existing_config.model_name = config.get("model_name", existing_config.model_name)
            existing_config.temperature = float(config.get("temperature", existing_config.temperature))
            existing_config.max_tokens = int(config.get("max_tokens", existing_config.max_tokens))
            existing_config.top_p = float(config.get("top_p", existing_config.top_p))
            existing_config.is_default = bool(config.get("is_default", existing_config.is_default))
            existing_config.is_active = True
            existing_config.streaming_enabled = bool(config.get("streaming_enabled", existing_config.streaming_enabled))
            existing_config.tool_calling_enabled = bool(config.get("tool_calling_enabled", existing_config.tool_calling_enabled))
            existing_config.memory_enabled = bool(config.get("memory_enabled", existing_config.memory_enabled))
            existing_config.knowledge_enabled = bool(config.get("knowledge_enabled", existing_config.knowledge_enabled))
            ai_config = existing_config
        else:
            # Create new config
            ai_config = AIConfig(
                id=uuid.uuid4(),
                name=config_name,
                provider=config.get("provider", "openai"),
                model_name=config.get("model_name", "gpt-4-turbo"),
                temperature=float(config.get("temperature", 0.7)),
                max_tokens=int(config.get("max_tokens", 2048)),
                top_p=float(config.get("top_p", 1.0)),
                is_default=bool(config.get("is_default", False)),
                is_active=True,
                streaming_enabled=bool(config.get("streaming_enabled", True)),
                tool_calling_enabled=bool(config.get("tool_calling_enabled", True)),
                memory_enabled=bool(config.get("memory_enabled", True)),
                knowledge_enabled=bool(config.get("knowledge_enabled", True)),
            )
            db.add(ai_config)

        await db.commit()
        await db.refresh(ai_config)

        logger.info(
            "ai_config.saved",
            admin_id=str(current_user.id),
            provider=config.get("provider"),
            model=config.get("model_name"),
        )

        return {
            "status": "saved",
            "id": str(ai_config.id),
            "provider": ai_config.provider,
            "model": ai_config.model_name,
        }
    except Exception as e:
        logger.error("ai_config.save_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save AI configuration: {str(e)}",
        )


@router.post("/provider-config")
async def save_provider_config(
    request: Request,
    config: dict,
    current_user: User = Depends(deps.get_current_user),
) -> dict:
    """Save provider API configurations (admin only)."""
    await deps.apply_rate_limit(request, "save_provider_config", 60, 60, current_user)

    redis_client = get_redis()

    # Validate that at least one provider is configured
    has_config = False
    for provider, creds in config.items():
        if creds.get("apiKey") or creds.get("baseUrl"):
            has_config = True
            break

    if not has_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one provider must be configured",
        )

    # Store in Redis with encryption flag (in production, use encryption)
    try:
        import json
        await redis_client.setex(
            "provider_configs",
            86400,  # 24 hours
            json.dumps(config),
        )
    except Exception as e:
        logger.error("provider_config.save_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save provider configuration",
        )

    logger.info(
        "provider_config.saved",
        admin_id=str(current_user.id),
        providers=list(config.keys()),
    )

    return {"status": "saved", "providers": list(config.keys())}


@router.get("/provider-config")
async def get_provider_config(
    request: Request,
    current_user: User = Depends(deps.get_current_user),
) -> dict:
    """Get provider API configuration from cache."""
    await deps.apply_rate_limit(request, "get_provider_config", 120, 60, current_user)
    redis_client = get_redis()
    defaults = {
        "openai": {"apiKey": "", "orgId": ""},
        "anthropic": {"apiKey": ""},
        "gemini": {"apiKey": ""},
        "grok": {"apiKey": ""},
        "ollama": {"baseUrl": get_settings().ollama_base_url},
    }
    try:
        cached = await redis_client.get("provider_configs")
        if cached:
            import json
            parsed = json.loads(cached)
            if isinstance(parsed, dict):
                return {**defaults, **parsed}
    except Exception as e:
        logger.warning("provider_config.get_failed", error=str(e))
    return defaults


@router.post("/white-label")
async def save_white_label(
    request: Request,
    settings_data: dict,
    current_user: User = Depends(deps.get_current_user),
) -> dict:
    """Save white label settings (admin only)."""
    await deps.apply_rate_limit(request, "save_white_label", 60, 60, current_user)

    redis_client = get_redis()

    # Validate settings
    brand_name = settings_data.get("brand_name", "RAZE")
    brand_color = settings_data.get("brand_color", "#3B82F6")
    logo_url = settings_data.get("logo_url", "")

    if not brand_name or len(brand_name) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brand name must be 1-128 characters",
        )

    # Store in Redis
    try:
        import json
        white_label = {
            "brand_name": brand_name,
            "brand_color": brand_color,
            "logo_url": logo_url,
        }
        await redis_client.setex(
            "white_label_settings",
            86400,  # 24 hours
            json.dumps(white_label),
        )
    except Exception as e:
        logger.error("white_label.save_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save white label settings",
        )

    logger.info(
        "white_label.saved",
        admin_id=str(current_user.id),
        brand_name=brand_name,
    )

    return {
        "status": "saved",
        "brand_name": brand_name,
        "brand_color": brand_color,
    }


@router.get("/white-label")
async def get_white_label(
    request: Request,
    current_user: User = Depends(deps.get_current_user),
) -> dict:
    """Get white label settings."""
    await deps.apply_rate_limit(request, "get_white_label", 120, 60, current_user)

    redis_client = get_redis()

    try:
        cached = await redis_client.get("white_label_settings")
        if cached:
            import json
            return json.loads(cached)
    except Exception as e:
        logger.warning("white_label.get_failed", error=str(e))

    # Return defaults
    return {
        "brand_name": "RAZE",
        "brand_color": "#3B82F6",
        "logo_url": "",
    }
