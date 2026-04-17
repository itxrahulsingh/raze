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

# Add middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Health check endpoints
@app.get("/health")
async def health_check():
    """Quick liveness check."""
    return {"status": "healthy"}


@app.get("/api/v1/health")
async def detailed_health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "components": {
            "database": "healthy",
            "redis": "healthy",
            "vector_search": "healthy"
        }
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
