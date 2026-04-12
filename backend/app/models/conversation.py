"""
RAZE Enterprise AI OS – Conversation & Message Models
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
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
    from app.models.analytics import ObservabilityLog
    from app.models.tool import ToolExecution
    from app.models.user import User


# ─── Enumerations ─────────────────────────────────────────────────────────────


class ConversationStatus(str, Enum):
    active = "active"
    idle = "idle"
    ended = "ended"
    archived = "archived"
    error = "error"


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"
    tool = "tool"


# ─── Conversation ─────────────────────────────────────────────────────────────


class Conversation(Base):
    """
    A single chat session.

    ``session_id``     – externally supplied identifier (e.g. from the SDK widget).
    ``user_id``        – NULL for anonymous / SDK users identified only by session.
    ``metadata``       – arbitrary JSON bag: widget config, language, referrer, etc.
    ``total_tokens``   – running total of tokens consumed across all messages.
    ``message_count``  – denormalised for quick stats (updated by the service layer).
    """

    __tablename__ = "conversations"

    session_id: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ConversationStatus.active.value,
        index=True,
    )
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ai_config_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_configs.id", ondelete="SET NULL"),
        nullable=True,
    )
    conv_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped["User | None"] = relationship("User", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        lazy="select",
    )
    tool_executions: Mapped[list["ToolExecution"]] = relationship(
        "ToolExecution", back_populates="conversation", lazy="select"
    )
    observability_logs: Mapped[list["ObservabilityLog"]] = relationship(
        "ObservabilityLog", back_populates="conversation", lazy="select"
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_conversations_status_created", "status", "created_at"),
        Index("ix_conversations_user_status", "user_id", "status"),
        Index("ix_conversations_started_at", "started_at"),
    )


# ─── Message ──────────────────────────────────────────────────────────────────


class Message(Base):
    """
    A single turn within a conversation.

    ``tool_calls``   – list of OpenAI-format tool-call objects requested by the model.
    ``tool_results`` – corresponding tool result payloads (role=tool messages).
    ``latency_ms``   – end-to-end latency for this message (LLM + tool calls).
    """

    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(32), nullable=False, default=MessageRole.user.value, index=True
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_calls: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )
    tool_results: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_error: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    msg_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )
    observability_logs: Mapped[list["ObservabilityLog"]] = relationship(
        "ObservabilityLog", back_populates="message", lazy="select"
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
        Index("ix_messages_role", "role"),
        Index("ix_messages_model_used", "model_used"),
    )
