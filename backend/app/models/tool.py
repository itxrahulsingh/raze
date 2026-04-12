"""
RAZE Enterprise AI OS – Tool & Tool Execution Models

Tools are registered external capabilities the AI can invoke via the
OpenAI function-calling protocol.  ``auth_config`` is stored encrypted
(the service layer handles encryption/decryption via Fernet).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation


# ─── Enumerations ─────────────────────────────────────────────────────────────


class ToolType(str, Enum):
    http_api = "http_api"
    database = "database"
    function = "function"       # server-side Python function
    mcp = "mcp"                 # Model Context Protocol server


class ToolAuthType(str, Enum):
    none = "none"
    api_key = "api_key"
    bearer = "bearer"
    basic = "basic"
    oauth2 = "oauth2"
    custom_header = "custom_header"


class ToolExecutionStatus(str, Enum):
    success = "success"
    failed = "failed"
    timeout = "timeout"
    rate_limited = "rate_limited"
    auth_error = "auth_error"


# ─── Tool ─────────────────────────────────────────────────────────────────────


class Tool(Base):
    """
    A registered tool / capability the AI can invoke.

    ``schema``        – OpenAI function-calling JSON schema:
                       {"name": ..., "description": ..., "parameters": {...}}
    ``auth_config``   – encrypted JSON with credentials (API key value, etc.).
    ``success_rate``  – maintained by the execution tracker (0.0–1.0).
    ``tags``          – list[str] for grouping (e.g. ["crm", "sales"]).
    """

    __tablename__ = "tools"

    name: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    display_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ToolType.http_api.value, index=True
    )
    # OpenAI function-calling schema
    schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # HTTP-specific fields
    endpoint_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    method: Mapped[str] = mapped_column(
        String(16), nullable=False, default="POST"
    )
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    # Auth
    auth_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ToolAuthType.none.value
    )
    auth_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, comment="Encrypted credentials blob"
    )
    # Extra headers / query params passed with every request
    default_headers: Mapped[dict[str, str] | None] = mapped_column(
        JSONB, nullable=True
    )
    # State
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requires_approval: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    # Telemetry (updated by execution tracker)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_used: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tool_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    executions: Mapped[list["ToolExecution"]] = relationship(
        "ToolExecution",
        back_populates="tool",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_tools_type_active", "type", "is_active"),
        Index(
            "ix_tools_tags_gin",
            "tags",
            postgresql_using="gin",
        ),
    )


# ─── Tool Execution ───────────────────────────────────────────────────────────


class ToolExecution(Base):
    """
    Immutable audit log of every tool invocation.

    ``input_data``  – the arguments supplied by the LLM.
    ``output_data`` – the raw response returned by the tool.
    ``latency_ms``  – wall-clock time from call to response.
    """

    __tablename__ = "tool_executions"

    tool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
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
    )
    input_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ToolExecutionStatus.success.value,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    http_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exec_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    tool: Mapped["Tool"] = relationship("Tool", back_populates="executions")
    conversation: Mapped["Conversation | None"] = relationship(
        "Conversation", back_populates="tool_executions"
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_tool_executions_tool_status", "tool_id", "status"),
        Index("ix_tool_executions_executed_at", "executed_at"),
    )
