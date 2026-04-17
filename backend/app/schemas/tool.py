"""
RAZE Enterprise AI OS – Tool Schemas

Covers tool registration, updates, execution history, and test invocations.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.models.tool import ToolAuthType, ToolExecutionStatus, ToolType


# ─── Tool ────────────────────────────────────────────────────────────────────


class ToolCreate(BaseModel):
    """
    Body for POST /tools.

    ``schema`` must be a valid OpenAI function-calling schema object:
    {
        "name": "get_weather",
        "description": "...",
        "parameters": {
            "type": "object",
            "properties": {...},
            "required": [...]
        }
    }
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=r"^[a-zA-Z0-9_\-]+$",
        description="Unique snake_case tool name (used in function-calling)",
    )
    display_name: str | None = Field(default=None, max_length=256)
    description: str = Field(..., min_length=1, max_length=4096)
    type: ToolType = Field(default=ToolType.http_api)
    tool_schema: dict[str, Any] = Field(
        ...,
        alias="schema",
        validation_alias="schema",
        serialization_alias="schema",
        description="OpenAI function-calling JSON schema",
    )
    endpoint_url: str | None = Field(
        default=None, description="Required when type=http_api"
    )
    method: str = Field(
        default="POST", pattern="^(GET|POST|PUT|PATCH|DELETE)$"
    )
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    max_retries: int = Field(default=3, ge=0, le=10)
    auth_type: ToolAuthType = Field(default=ToolAuthType.none)
    auth_config: dict[str, Any] | None = Field(
        default=None,
        description="Credentials: {'api_key': '...', 'header_name': 'X-API-Key'}",
    )
    default_headers: dict[str, str] | None = None
    requires_approval: bool = Field(
        default=False, description="Require human approval before each execution"
    )
    tags: list[str] = Field(default_factory=list, max_length=20)
    tool_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tool_schema")
    @classmethod
    def validate_schema(cls, v: dict[str, Any]) -> dict[str, Any]:
        if "name" not in v:
            raise ValueError("Tool schema must contain a 'name' field")
        if "parameters" not in v:
            raise ValueError("Tool schema must contain a 'parameters' field")
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def normalise_tags(cls, v: list[str]) -> list[str]:
        return [t.strip().lower() for t in v if t.strip()]

    model_config = {"str_strip_whitespace": True, "populate_by_name": True}


class ToolUpdate(BaseModel):
    """Body for PATCH /tools/{id} – all fields optional."""

    display_name: str | None = Field(default=None, max_length=256)
    description: str | None = Field(default=None, min_length=1, max_length=4096)
    tool_schema: dict[str, Any] | None = Field(
        default=None,
        alias="schema",
        validation_alias="schema",
        serialization_alias="schema",
    )
    endpoint_url: str | None = None
    method: str | None = Field(
        default=None, pattern="^(GET|POST|PUT|PATCH|DELETE)$"
    )
    timeout_seconds: int | None = Field(default=None, ge=1, le=300)
    max_retries: int | None = Field(default=None, ge=0, le=10)
    auth_type: ToolAuthType | None = None
    auth_config: dict[str, Any] | None = None
    default_headers: dict[str, str] | None = None
    is_active: bool | None = None
    requires_approval: bool | None = None
    tags: list[str] | None = None
    tool_metadata: dict[str, Any] | None = None

    @field_validator("tags", mode="before")
    @classmethod
    def normalise_tags(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        return [t.strip().lower() for t in v if t.strip()]

    model_config = {"str_strip_whitespace": True, "populate_by_name": True}


class ToolResponse(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str | None
    description: str
    type: ToolType
    tool_schema: dict[str, Any] = Field(
        alias="schema",
        validation_alias="schema",
        serialization_alias="schema",
    )
    endpoint_url: str | None
    method: str
    timeout_seconds: int
    max_retries: int
    auth_type: ToolAuthType
    # auth_config intentionally omitted (sensitive)
    default_headers: dict[str, str] | None
    is_active: bool
    requires_approval: bool
    tags: list[str]
    usage_count: int
    success_rate: float
    avg_latency_ms: float
    last_used: datetime | None
    tool_metadata: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class ToolListResponse(BaseModel):
    items: list[ToolResponse]
    total: int
    page: int
    page_size: int


# ─── Tool Test ────────────────────────────────────────────────────────────────


class ToolTestRequest(BaseModel):
    """
    Body for POST /tools/{id}/test.

    Executes the tool immediately with the supplied ``arguments`` and returns
    the raw response – useful for validating connectivity during onboarding.
    """

    arguments: dict[str, Any] = Field(
        ..., description="Arguments matching the tool's JSON schema"
    )
    timeout_override: int | None = Field(
        default=None,
        ge=1,
        le=120,
        description="Override timeout for this test run only (seconds)",
    )


class ToolTestResponse(BaseModel):
    tool_id: uuid.UUID
    tool_name: str
    success: bool
    output: Any | None
    error: str | None
    latency_ms: int
    http_status_code: int | None


# ─── Tool Execution ──────────────────────────────────────────────────────────


class ToolExecutionResponse(BaseModel):
    id: uuid.UUID
    tool_id: uuid.UUID
    conversation_id: uuid.UUID | None
    message_id: uuid.UUID | None
    input_data: dict[str, Any]
    output_data: dict[str, Any] | None
    status: ToolExecutionStatus
    error_message: str | None
    error_code: str | None
    latency_ms: int | None
    executed_at: datetime | None
    http_status_code: int | None
    retry_count: int
    exec_metadata: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ToolExecutionListResponse(BaseModel):
    items: list[ToolExecutionResponse]
    total: int
    page: int
    page_size: int
