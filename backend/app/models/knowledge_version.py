"""
RAZE Enterprise AI OS – Knowledge Versioning & Change History

Enables:
  - Full version history for knowledge chunks
  - Rollback to previous versions
  - Change tracking for compliance
  - Content audit trail
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class KnowledgeChunkVersion(Base):
    """
    Immutable version history for knowledge chunks.

    Every edit creates a new version record. Enables:
    - Full audit trail
    - Rollback capability
    - Change attribution
    - Compliance requirements
    """

    __tablename__ = "knowledge_chunk_versions"

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    old_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_content: Mapped[str] = mapped_column(Text, nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    change_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_knowledge_chunk_versions_chunk_version", "chunk_id", "version"),
        Index("ix_knowledge_chunk_versions_changed_by", "changed_by"),
        Index("ix_knowledge_chunk_versions_created", "created_at"),
    )
