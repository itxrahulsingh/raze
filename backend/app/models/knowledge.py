"""
RAZE Enterprise AI OS – Knowledge Source & Chunk Models

Uses pgvector's Vector column type for storing dense embeddings directly
in PostgreSQL so we can run hybrid (BM25 + ANN) search without a separate
vector store for the common case.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pgvector.sqlalchemy import Vector
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

from app.config import settings
from app.database import Base


# ─── Enumerations ─────────────────────────────────────────────────────────────


class KnowledgeSourceType(str, Enum):
    pdf = "pdf"
    docx = "docx"
    txt = "txt"
    url = "url"
    manual = "manual"
    csv = "csv"
    html = "html"
    json = "json"
    xlsx = "xlsx"
    xls = "xls"


class KnowledgeSourceCategory(str, Enum):
    document = "document"
    article = "article"
    chat_session = "chat_session"
    client_document = "client_document"
    training_material = "training_material"
    reference = "reference"


class KnowledgeSourceStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    approved = "approved"
    rejected = "rejected"
    failed = "failed"


class KnowledgeSourceMode(str, Enum):
    linked = "linked"        # content fetched on-demand (URL sources)
    persistent = "persistent"  # content stored in DB / MinIO


# ─── Knowledge Source ─────────────────────────────────────────────────────────


class KnowledgeSource(Base):
    """
    A document or URL that has been ingested into the knowledge base.

    ``content_hash``   – SHA-256 of the raw file / content (deduplication).
    ``chunk_count``    – number of KnowledgeChunk rows created from this source.
    ``embedding_model`` – model used to produce the chunk embeddings.
    ``approved_by``    – user_id of the admin who approved the content.
    ``tags``           – list[str] JSON for faceted filtering.
    """

    __tablename__ = "knowledge_sources"

    name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=KnowledgeSourceType.txt.value,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=KnowledgeSourceStatus.pending.value,
        index=True,
    )
    mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=KnowledgeSourceMode.persistent.value,
    )
    # Storage
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    # Processing results
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Approval workflow
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Classification
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    src_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    category: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=KnowledgeSourceCategory.document.value,
        index=True,
    )
    source_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    client_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    # Usage control flags
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    can_use_in_knowledge: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    can_use_in_chat: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    can_use_in_search: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Edit tracking
    edited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    edit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Relationships ──────────────────────────────────────────────────────────
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk",
        back_populates="source",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_knowledge_sources_status_type", "status", "type"),
        Index("ix_knowledge_sources_active_status", "is_active", "status"),
        Index("ix_knowledge_sources_category", "category"),
        Index("ix_knowledge_sources_client_id", "client_id"),
        # GIN index for fast tag array containment queries
        Index(
            "ix_knowledge_sources_tags_gin",
            "tags",
            postgresql_using="gin",
        ),
    )


# ─── Knowledge Chunk ──────────────────────────────────────────────────────────


class KnowledgeChunk(Base):
    """
    A text chunk derived from a KnowledgeSource, with its dense embedding.

    ``embedding`` – pgvector VECTOR column; dimension set from config so that
                   Alembic migrations stay consistent if the model is swapped.
    ``chunk_index`` – positional order within the parent source.
    ``token_count`` – tiktoken count used for context-window budgeting.
    """

    __tablename__ = "knowledge_chunks"

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dimensions), nullable=True
    )
    # Optional structured fields extracted during ingestion
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    chunk_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    source: Mapped["KnowledgeSource"] = relationship(
        "KnowledgeSource", back_populates="chunks"
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index(
            "ix_knowledge_chunks_source_idx",
            "source_id",
            "chunk_index",
        ),
        # IVFFlat ANN index – created here so Alembic picks it up.
        # For production use HNSW (requires pgvector >= 0.5.0):
        #   postgresql_using="hnsw",
        #   postgresql_with={"m": 16, "ef_construction": 64},
        Index(
            "ix_knowledge_chunks_embedding_ivfflat",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
