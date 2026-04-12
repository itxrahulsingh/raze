"""
RAZE Enterprise AI OS – AI Configuration Model

Each AIConfig defines a named LLM configuration that can be selected
per conversation (or set as the global default).  The routing strategy
determines how the system picks between primary and fallback providers.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from sqlalchemy import (
    Boolean,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# ─── Enumerations ─────────────────────────────────────────────────────────────


class LLMProvider(str, Enum):
    openai = "openai"
    anthropic = "anthropic"
    gemini = "gemini"
    grok = "grok"
    ollama = "ollama"


class RoutingStrategy(str, Enum):
    cost = "cost"              # always prefer cheapest model
    performance = "performance"  # always prefer highest-quality model
    balanced = "balanced"      # cost-performance trade-off
    round_robin = "round_robin"  # spread load across providers
    latency = "latency"        # prefer lowest p50 latency


# ─── AI Config ────────────────────────────────────────────────────────────────


class AIConfig(Base):
    """
    Named LLM configuration.

    One row may be marked ``is_default=True``; a partial unique index
    enforces that only one default exists at a time.

    ``system_prompt``     – injected as the system message in every conversation
                           that uses this config.
    ``fallback_provider`` – provider to switch to on rate-limit / error.
    ``cost_limit_daily``  – maximum spend (USD) per day for this config;
                           enforced by the billing guard middleware.
    ``extra_params``      – arbitrary JSON passed to the provider SDK
                           (e.g. {"top_p": 0.9, "frequency_penalty": 0.1}).
    """

    __tablename__ = "ai_configs"

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Primary provider
    provider: Mapped[str] = mapped_column(
        String(32), nullable=False, default=LLMProvider.openai.value, index=True
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=4096)
    top_p: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    presence_penalty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    frequency_penalty: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Fallback provider
    fallback_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fallback_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fallback_on_errors: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="HTTP status codes / error classes that trigger fallback",
    )

    # Budget
    cost_limit_daily: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_per_1k_input_tokens: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    cost_per_1k_output_tokens: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    # Routing
    routing_strategy: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RoutingStrategy.balanced.value,
    )

    # Feature toggles per config
    streaming_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    tool_calling_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    memory_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    knowledge_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Extra provider-specific params
    extra_params: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # ── Indexes / Constraints ─────────────────────────────────────────────────
    __table_args__ = (
        # Only one default config allowed at a time
        Index(
            "uix_ai_configs_single_default",
            "is_default",
            unique=True,
            postgresql_where="is_default = TRUE",
        ),
        Index("ix_ai_configs_provider_active", "provider", "is_active"),
        UniqueConstraint("name", name="uq_ai_configs_name"),
    )
