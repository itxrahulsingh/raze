"""
RAZE Enterprise AI OS – Analytics & Observability Models

Three tables:
  ObservabilityLog  – per-message decision audit trail
  UsageMetrics      – daily rolled-up aggregate metrics
  UserSession       – visitor / session tracking
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ─── Observability Log ────────────────────────────────────────────────────────


class ObservabilityLog(Base):
    """
    Immutable audit record for every AI decision made while processing a
    message.  Captures the full reasoning chain so operators can replay and
    debug AI behaviour.

    ``intent_detected``   – NLU intent classification result.
    ``model_selected``    – the model that was ultimately used.
    ``model_reason``      – free-text explanation of the routing decision.
    ``tools_considered``  – list of tool names the planner evaluated.
    ``tool_selected``     – tool that was actually invoked (if any).
    ``confidence_score``  – planner's self-reported confidence (0.0–1.0).
    ``context_retrieved`` – knowledge chunks / memories injected into the prompt.
    ``decision_path``     – ordered list of reasoning steps (chain-of-thought).
    ``cost_usd``          – estimated cost of this message.
    """

    __tablename__ = "observability_logs"

    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="message_processed", index=True
    )
    # Intent & routing
    intent_detected: Mapped[str | None] = mapped_column(String(256), nullable=True)
    model_selected: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_selected: Mapped[str | None] = mapped_column(String(64), nullable=True)
    routing_strategy_used: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    # Tool selection
    tools_considered: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    tool_selected: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tool_selection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Confidence
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Context injection
    context_retrieved: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Knowledge chunks / memory items injected into the prompt",
    )
    knowledge_chunks_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    memory_items_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Reasoning chain
    decision_path: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    # Performance
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ttft_ms: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Time-to-first-token in ms"
    )
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    tokens_prompt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_completion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Misc
    log_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    conversation: Mapped[Any] = relationship(
        "Conversation", back_populates="observability_logs", lazy="select"
    )
    message: Mapped[Any] = relationship(
        "Message", back_populates="observability_logs", lazy="select"
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_obs_logs_event_created", "event_type", "created_at"),
        Index("ix_obs_logs_model_selected", "model_selected"),
        Index("ix_obs_logs_cost", "cost_usd"),
    )


# ─── Usage Metrics ────────────────────────────────────────────────────────────


class UsageMetrics(Base):
    """
    Daily aggregated metrics rolled up by a Celery beat task.

    One row per calendar date; the ``date`` column has a unique constraint
    so the upsert logic is safe.
    """

    __tablename__ = "usage_metrics"

    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    total_requests: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    total_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_prompt_tokens: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    total_completion_tokens: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    total_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p50_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p95_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p99_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tool_executions: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tool_failures: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    knowledge_queries: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    memory_reads: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    memory_writes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    unique_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unique_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_conversations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Per-provider breakdown stored as JSON  {"openai": {...}, "anthropic": {...}}
    provider_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    model_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    __table_args__ = (
        UniqueConstraint("date", name="uq_usage_metrics_date"),
    )


# ─── User Session ─────────────────────────────────────────────────────────────


class UserSession(Base):
    """
    Visitor / session tracking record.  Created when a new ``session_id``
    is first seen, updated on each subsequent message.

    Not to be confused with HTTP sessions – this tracks chat widget sessions.
    """

    __tablename__ = "user_sessions"

    session_id: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_type: Mapped[str | None] = mapped_column(
        String(32), nullable=True, index=True
    )
    os_info: Mapped[str | None] = mapped_column(String(128), nullable=True)
    browser_info: Mapped[str | None] = mapped_column(String(128), nullable=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    referrer: Mapped[str | None] = mapped_column(Text, nullable=True)
    utm_source: Mapped[str | None] = mapped_column(String(256), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(256), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(256), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    session_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_user_sessions_started_active", "started_at", "is_active"),
        Index("ix_user_sessions_country", "country"),
        Index("ix_user_sessions_device", "device_type"),
        Index("ix_user_sessions_last_seen", "last_seen"),
    )
