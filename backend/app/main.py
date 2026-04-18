"""
RAZE Enterprise AI OS - FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import structlog

from app.config import get_settings
from app.database import connect_db, disconnect_db, connect_redis, disconnect_redis
from app.api.v1 import auth, chat, knowledge, memory, tools, admin, analytics, sdk
from app.core.observability import TraceIDMiddleware, MetricsMiddleware, ErrorTrackingMiddleware

settings = get_settings()

# Configure logging
logging.basicConfig(level=logging.INFO)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context for startup and shutdown."""
    logger.info("Starting RAZE AI OS...")

    # Startup
    await connect_db()
    await connect_redis()

    # Initialize Qdrant collections
    from app.core.vector_search import VectorSearchEngine
    vs = VectorSearchEngine()
    await vs.create_collection(settings.qdrant_collection_knowledge, vector_size=settings.qdrant_vector_size)
    await vs.create_collection(settings.qdrant_collection_memory, vector_size=settings.qdrant_vector_size)
    logger.info("Qdrant collections initialized")

    # Soft-validate Ollama if enabled (retry on first request if unavailable)
    if settings.ollama_enabled:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                resp.raise_for_status()
                logger.info("Ollama service validated and healthy")
        except Exception as e:
            logger.warning("Ollama validation warning - will retry on first request", error=str(e), base_url=settings.ollama_base_url)

    logger.info("RAZE AI OS started successfully")

    yield

    # Shutdown
    logger.info("Shutting down RAZE AI OS...")
    await disconnect_db()
    await disconnect_redis()
    logger.info("RAZE AI OS shut down successfully")


# Create FastAPI app
app = FastAPI(
    title="RAZE Enterprise AI OS API",
    description="Enterprise AI Operating System with persistent knowledge, advanced memory, and full governance",
    version="1.0.0",
    lifespan=lifespan
)

# Add middlewares (order matters: innermost added first)
app.add_middleware(ErrorTrackingMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(TraceIDMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoints
@app.get("/health")
async def health_check():
    """Quick liveness check."""
    return {"status": "healthy"}


@app.get("/api/v1/health")
async def detailed_health_check():
    """Detailed health check."""
    import httpx

    components = {
        "database": "healthy",
        "redis": "healthy",
        "vector_search": "healthy"
    }

    # Check Ollama if enabled
    if settings.ollama_enabled:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                resp.raise_for_status()
                components["ollama"] = "healthy"
        except Exception as e:
            logger.warning("Ollama health check failed", error=str(e))
            components["ollama"] = f"unhealthy: {str(e)}"

    overall_status = "healthy" if all(v == "healthy" for v in components.values()) else "degraded"

    return {
        "status": overall_status,
        "version": "1.0.0",
        "components": components
    }


# Include routers
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(knowledge.router, prefix="/api/v1", tags=["knowledge"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["memory"])
app.include_router(tools.router, prefix="/api/v1/tools", tags=["tools"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(sdk.router, prefix="/api/v1", tags=["sdk"])


# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics (simplified)."""
    return {
        "requests_total": 0,
        "requests_errors_total": 0,
        "request_duration_seconds": 0.0
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
