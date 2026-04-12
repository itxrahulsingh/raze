"""
RAZE Enterprise AI OS – Memory Schemas

Covers memory CRUD and semantic memory search.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.memory import MemoryType


# ─── Memory ───────────────────────────────────────────────────────────────────


class MemoryCreate(BaseModel):
    """
    Body for POST /memory.

    ``importance_score`` can be supplied by the caller (e.g. when the LLM
    extracts a user preference and knows it is important) or computed later
    by the importance scorer service.
    """

    type: MemoryType = Field(default=MemoryType.context)
    content: str = Field(..., min_length=1, max_length=65536)
    summary: str | None = Field(
        default=None,
        max_length=1024,
        description="Short summary for display / de-duplication",
    )
    importance_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Initial importance (0–1)"
    )
    decay_rate: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="Daily exponential decay factor",
    )
    session_id: str | None = Field(default=None, max_length=128)
    expires_at: datetime | None = None
    mem_metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"str_strip_whitespace": True}


class MemoryUpdate(BaseModel):
    """Body for PATCH /memory/{id} – all fields optional."""

    content: str | None = Field(default=None, min_length=1, max_length=65536)
    summary: str | None = Field(default=None, max_length=1024)
    importance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    decay_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    expires_at: datetime | None = None
    is_active: bool | None = None
    mem_metadata: dict[str, Any] | None = None

    model_config = {"str_strip_whitespace": True}


class MemoryResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    session_id: str | None
    type: MemoryType
    content: str
    summary: str | None
    importance_score: float
    decay_rate: float
    access_count: int
    last_accessed: datetime | None
    expires_at: datetime | None
    is_active: bool
    source_conversation_id: uuid.UUID | None
    mem_metadata: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemoryListResponse(BaseModel):
    items: list[MemoryResponse]
    total: int
    page: int
    page_size: int


# ─── Memory Search ────────────────────────────────────────────────────────────


class MemorySearchRequest(BaseModel):
    """
    Body for POST /memory/search.

    The service layer embeds ``query`` and performs an ANN search against
    the ``memories.embedding`` column.
    """

    query: str = Field(..., min_length=1, max_length=4096)
    user_id: uuid.UUID | None = Field(
        default=None, description="Restrict to a specific user's memories"
    )
    session_id: str | None = Field(
        default=None, description="Restrict to a specific session"
    )
    types: list[MemoryType] = Field(
        default_factory=list,
        description="Filter by memory type (empty = all types)",
    )
    limit: int = Field(default=10, ge=1, le=100)
    score_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    min_importance: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Only return memories with importance >= this value",
    )
    include_expired: bool = Field(
        default=False, description="Include memories past their expires_at"
    )

    model_config = {"str_strip_whitespace": True}


class MemorySearchResult(BaseModel):
    memory: MemoryResponse
    score: float = Field(..., ge=0.0, le=1.0)


class MemorySearchResponse(BaseModel):
    query: str
    results: list[MemorySearchResult]
    total_found: int
    search_latency_ms: int


# ─── Retention Policy ────────────────────────────────────────────────────────


class RetentionPolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    type: MemoryType
    max_count: int | None = Field(default=None, ge=1, le=10000)
    ttl_days: int | None = Field(default=None, ge=1, le=3650)
    min_importance: float = Field(default=0.1, ge=0.0, le=1.0)
    auto_decay: bool = True
    decay_formula: str = Field(
        default="exponential", pattern="^(exponential|linear|step)$"
    )
    description: str | None = None

    model_config = {"str_strip_whitespace": True}


class RetentionPolicyResponse(BaseModel):
    id: uuid.UUID
    name: str
    type: MemoryType
    max_count: int | None
    ttl_days: int | None
    min_importance: float
    auto_decay: bool
    decay_formula: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
