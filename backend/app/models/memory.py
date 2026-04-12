"""
RAZE Enterprise AI OS – Memory & Retention Policy Models

The memory system stores semantic memories about users and sessions.
Each memory has an embedding for similarity search, an importance score,
and a decay rate so old / irrelevant memories fade over time.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
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

from app.config import settings
from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


# ─── Enumerations ─────────────────────────────────────────────────────────────


class MemoryType(str, Enum):
    context = "context"          # short-term conversation context
    user = "user"                # persistent user facts / preferences
    operational = "operational"  # task / workflow state
    knowledge = "knowledge"      # derived from the knowledge base


# ─── Memory ───────────────────────────────────────────────────────────────────


class Memory(Base):
    """
    A single memory item.

    ``importance_score`` – 0.0–1.0 relevance score; computed at creation time
                          by the memory manager (e.g. LLM-based scoring).
    ``decay_rate``       – daily exponential decay factor (0.0 = immortal,
                          1.0 = gone tomorrow).
    ``access_count``     – incremented each time the memory is retrieved; used
                          to boost importance for frequently-accessed items.
    ``expires_at``       – hard TTL; NULL = rely on decay only.
    ``embedding``        – dense vector for semantic similarity search.
    """

    __tablename__ = "memories"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=MemoryType.context.value,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    importance_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5
    )
    decay_rate: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.01
    )
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_accessed: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dimensions), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    mem_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped["User | None"] = relationship("User", back_populates="memories")

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_memories_user_type_active", "user_id", "type", "is_active"),
        Index("ix_memories_session_active", "session_id", "is_active"),
        Index(
            "ix_memories_importance",
            "importance_score",
            "is_active",
        ),
        # ANN index for semantic memory retrieval
        Index(
            "ix_memories_embedding_ivfflat",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 50},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


# ─── Memory Retention Policy ──────────────────────────────────────────────────


class MemoryRetentionPolicy(Base):
    """
    Named retention policy that governs how memories of a given type age out.

    ``max_count``      – cap on the number of active memories of this type per
                        user; oldest / least important are pruned first.
    ``ttl_days``       – hard maximum age in days (NULL = unlimited).
    ``min_importance`` – memories below this score are eligible for early
                        eviction by the background sweeper.
    ``auto_decay``     – if True, the sweeper applies the decay formula nightly.
    """

    __tablename__ = "memory_retention_policies"

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    type: Mapped[str] = mapped_column(
        String(32), nullable=False, default=MemoryType.context.value, index=True
    )
    max_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ttl_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_importance: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.1
    )
    auto_decay: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    decay_formula: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        default="exponential",
        comment="exponential | linear | step",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_memory_retention_type_active", "type", "is_active"),
    )
