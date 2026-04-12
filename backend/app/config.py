"""
RAZE Enterprise AI OS – Application Configuration
All settings are loaded from environment variables (or a .env file).
"""

from __future__ import annotations

import secrets
from enum import Enum
from functools import lru_cache
from typing import Any

from pydantic import AnyHttpUrl, Field, PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ─── Enumerations ─────────────────────────────────────────────────────────────


class Environment(str, Enum):
    development = "development"
    staging = "staging"
    production = "production"


class LogLevel(str, Enum):
    debug = "DEBUG"
    info = "INFO"
    warning = "WARNING"
    error = "ERROR"
    critical = "CRITICAL"


# ─── Settings ─────────────────────────────────────────────────────────────────


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    app_name: str = "RAZE Enterprise AI OS"
    app_version: str = "1.0.0"
    environment: Environment = Environment.development
    debug: bool = False
    log_level: LogLevel = LogLevel.info
    api_v1_prefix: str = "/api/v1"
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="CORS allowed origins",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://raze:raze@localhost:5432/raze",
        description="Async PostgreSQL DSN (asyncpg driver)",
    )
    database_pool_size: int = 20
    database_max_overflow: int = 40
    database_pool_timeout: int = 30
    database_pool_recycle: int = 1800
    database_echo: bool = False

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    redis_max_connections: int = 100
    redis_decode_responses: bool = True
    redis_socket_timeout: float = 5.0
    redis_socket_connect_timeout: float = 5.0

    # ── JWT / Auth ────────────────────────────────────────────────────────────
    jwt_secret_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(64),
        description="Secret key for JWT signing",
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    api_key_length: int = 64

    # ── OpenAI ───────────────────────────────────────────────────────────────
    openai_api_key: str | None = None
    openai_org_id: str | None = None
    openai_default_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-large"
    openai_embedding_dimensions: int = 3072

    # ── Anthropic ────────────────────────────────────────────────────────────
    anthropic_api_key: str | None = None
    anthropic_default_model: str = "claude-opus-4-5"

    # ── Google Gemini ─────────────────────────────────────────────────────────
    google_api_key: str | None = None
    gemini_default_model: str = "gemini-2.0-flash"

    # ── Grok (xAI) ───────────────────────────────────────────────────────────
    grok_api_key: str | None = None
    grok_base_url: str = "https://api.x.ai/v1"
    grok_default_model: str = "grok-3"

    # ── Ollama ────────────────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3.2"
    ollama_enabled: bool = False

    # ── Qdrant ───────────────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection_knowledge: str = "raze_knowledge"
    qdrant_collection_memory: str = "raze_memory"
    qdrant_vector_size: int = 3072

    # ── MinIO / S3 ───────────────────────────────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket_documents: str = "raze-documents"
    minio_bucket_exports: str = "raze-exports"

    # ── Celery ───────────────────────────────────────────────────────────────
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        description="Celery broker URL",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        description="Celery result backend URL",
    )
    celery_task_serializer: str = "json"
    celery_result_expires: int = 86400  # 1 day in seconds

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    rate_limit_enabled: bool = True
    rate_limit_default_per_minute: int = 60
    rate_limit_chat_per_minute: int = 30
    rate_limit_upload_per_minute: int = 10
    rate_limit_search_per_minute: int = 120
    rate_limit_admin_per_minute: int = 120

    # ── Embedding ────────────────────────────────────────────────────────────
    local_embedding_model: str = "BAAI/bge-large-en-v1.5"
    local_embedding_enabled: bool = False
    local_embedding_dimensions: int = 1024

    # ── Knowledge Processing ──────────────────────────────────────────────────
    chunk_size: int = 512
    chunk_overlap: int = 64
    max_file_size_mb: int = 50
    supported_file_types: list[str] = Field(
        default=["pdf", "docx", "txt", "md", "html", "csv", "json"],
    )

    # ── Memory ───────────────────────────────────────────────────────────────
    memory_default_ttl_days: int = 30
    memory_max_context_items: int = 10
    memory_importance_threshold: float = 0.5
    memory_decay_rate: float = 0.01

    # ── Cost / Budget ─────────────────────────────────────────────────────────
    daily_cost_limit_usd: float = 100.0
    alert_cost_threshold_pct: float = 0.80

    # ── Feature Flags ─────────────────────────────────────────────────────────
    feature_streaming: bool = True
    feature_voice: bool = False
    feature_image_understanding: bool = True
    feature_tool_calling: bool = True
    feature_memory: bool = True
    feature_knowledge_base: bool = True
    feature_analytics: bool = True
    feature_multi_model_routing: bool = True
    feature_sdk_mode: bool = True

    # ── Observability ─────────────────────────────────────────────────────────
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    trace_sample_rate: float = 1.0  # 0.0–1.0

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("supported_file_types", mode="before")
    @classmethod
    def parse_file_types(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [ft.strip().lstrip(".") for ft in v.split(",") if ft.strip()]
        return v

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.environment == Environment.production:
            if "localhost" in self.jwt_secret_key or len(self.jwt_secret_key) < 32:
                raise ValueError(
                    "jwt_secret_key must be a strong random secret in production"
                )
        return self

    # ── Derived helpers ───────────────────────────────────────────────────────

    @property
    def is_development(self) -> bool:
        return self.environment == Environment.development

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.production

    @property
    def embedding_dimensions(self) -> int:
        if self.local_embedding_enabled:
            return self.local_embedding_dimensions
        return self.openai_embedding_dimensions

    @property
    def sync_database_url(self) -> str:
        """Synchronous DSN used by Alembic migrations (psycopg2)."""
        return self.database_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://"
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()


# Convenience export so callers can do: `from app.config import settings`
settings: Settings = get_settings()
