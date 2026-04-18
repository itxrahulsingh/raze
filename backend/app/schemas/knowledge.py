"""
RAZE Enterprise AI OS – Knowledge Schemas

Covers knowledge source ingestion, chunk retrieval, semantic search,
and approval workflow shapes.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.models.knowledge import (
    KnowledgeSourceMode,
    KnowledgeSourceStatus,
    KnowledgeSourceType,
)


# ─── Knowledge Source ────────────────────────────────────────────────────────


class KnowledgeSourceCreate(BaseModel):
    """
    Body for POST /knowledge/sources.

    Either ``url`` (for URL sources) or a file upload (multipart) is expected;
    the router validates this before calling the service layer.
    """

    name: str = Field(..., min_length=1, max_length=512)
    description: str | None = Field(default=None, max_length=4096)
    type: KnowledgeSourceType = Field(default=KnowledgeSourceType.txt)
    mode: KnowledgeSourceMode = Field(default=KnowledgeSourceMode.persistent)
    url: HttpUrl | None = Field(
        default=None, description="Required when type=url"
    )
    tags: list[str] = Field(default_factory=list, max_length=20)
    src_metadata: dict[str, Any] = Field(default_factory=dict)
    # Processing hints
    embedding_model: str | None = Field(
        default=None,
        description="Override embedding model for this source (uses system default if None)",
    )
    auto_approve: bool = Field(
        default=False,
        description="Skip the approval queue (requires admin role)",
    )

    @field_validator("tags", mode="before")
    @classmethod
    def normalise_tags(cls, v: list[str]) -> list[str]:
        return [t.strip().lower() for t in v if t.strip()]

    model_config = {"str_strip_whitespace": True}


class KnowledgeSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    tags: list[str] | None = None
    src_metadata: dict[str, Any] | None = None
    is_active: bool | None = None

    @field_validator("tags", mode="before")
    @classmethod
    def normalise_tags(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        return [t.strip().lower() for t in v if t.strip()]


class KnowledgeSourceResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    type: KnowledgeSourceType
    status: KnowledgeSourceStatus
    mode: KnowledgeSourceMode
    file_path: str | None
    url: str | None
    file_size: int | None
    mime_type: str | None
    content_hash: str | None
    chunk_count: int
    embedding_model: str | None
    processing_error: str | None
    processed_at: datetime | None
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    rejection_reason: str | None
    tags: list[str]
    src_metadata: dict[str, Any] | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeSourceListResponse(BaseModel):
    items: list[KnowledgeSourceResponse]
    total: int
    page: int
    page_size: int


# ─── Approval ────────────────────────────────────────────────────────────────


class KnowledgeApprovalRequest(BaseModel):
    """Body for POST /knowledge/sources/{id}/approve or /reject."""

    approved: bool
    reason: str | None = Field(
        default=None, max_length=2048, description="Required when rejecting"
    )

    @field_validator("reason")
    @classmethod
    def reason_required_on_reject(
        cls, v: str | None, info: Any
    ) -> str | None:
        # Pydantic v2 validation_info approach
        values = info.data if hasattr(info, "data") else {}
        if values.get("approved") is False and not v:
            raise ValueError("A reason must be provided when rejecting a source")
        return v


# ─── Knowledge Chunk ─────────────────────────────────────────────────────────


class KnowledgeChunkResponse(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    content: str
    chunk_index: int
    token_count: int
    page_number: int | None
    section_title: str | None
    chunk_metadata: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeChunkListResponse(BaseModel):
    items: list[KnowledgeChunkResponse]
    total: int
    source_id: uuid.UUID


# ─── Search ──────────────────────────────────────────────────────────────────


class KnowledgeSearchRequest(BaseModel):
    """
    Body for POST /knowledge/search.

    Supports semantic (ANN), keyword (full-text), and hybrid modes.
    """

    query: str = Field(..., min_length=1, max_length=4096)
    mode: str = Field(
        default="hybrid",
        pattern="^(semantic|keyword|hybrid)$",
        description="Search mode: semantic (ANN), keyword (FTS), or hybrid",
    )
    limit: int = Field(default=5, ge=1, le=50)
    score_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score (semantic mode only)",
    )
    # Filters
    source_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="Restrict results to these source IDs (empty = all)",
    )
    tags: list[str] = Field(
        default_factory=list, description="Restrict results to sources with these tags"
    )
    source_types: list[KnowledgeSourceType] = Field(default_factory=list)
    # Hybrid weights
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0)

    model_config = {"str_strip_whitespace": True}


class KnowledgeSearchResult(BaseModel):
    chunk: KnowledgeChunkResponse
    source: KnowledgeSourceResponse
    score: float = Field(..., ge=0.0, le=1.0)
    highlights: list[str] = Field(
        default_factory=list, description="Matched text snippets (keyword mode)"
    )


class KnowledgeSearchResponse(BaseModel):
    query: str
    mode: str
    results: list[KnowledgeSearchResult]
    total_found: int
    search_latency_ms: int


# ─── Versioning ──────────────────────────────────────────────────────────────


class KnowledgeChunkVersionResponse(BaseModel):
    id: uuid.UUID
    chunk_id: uuid.UUID
    version: int
    old_content: str | None
    new_content: str
    changed_by: uuid.UUID | None
    change_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeChunkVersionListResponse(BaseModel):
    chunk_id: uuid.UUID
    versions: list[KnowledgeChunkVersionResponse]
    current_version: int
