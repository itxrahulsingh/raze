"""
RAZE Enterprise AI OS – Chat Schemas

Covers request/response shapes for the chat endpoint, streaming chunks,
conversation management, and message history.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.models.conversation import ConversationStatus, MessageRole


# ─── Enumerations ─────────────────────────────────────────────────────────────


class StreamEventType(str, Enum):
    start = "start"
    delta = "delta"
    tool_call = "tool_call"
    tool_result = "tool_result"
    done = "done"
    error = "error"


# ─── Request ──────────────────────────────────────────────────────────────────


class MessageInput(BaseModel):
    """A single message in the conversation history."""

    role: MessageRole
    content: str = Field(..., min_length=1, max_length=65536)


class ChatRequest(BaseModel):
    """
    Body for POST /chat.

    ``session_id``  – client-generated stable identifier for the session.
                     If omitted, the backend generates one.
    ``message``     – the new user turn.
    ``history``     – optional prior turns to prepend (useful for stateless SDK).
    ``stream``      – if True, response is Server-Sent Events.
    ``ai_config_id`` – override the default AI configuration for this request.
    ``context``     – arbitrary key/value bag forwarded to tool executors.
    """

    session_id: str | None = Field(
        default=None,
        max_length=128,
        description="Stable session identifier; auto-generated if absent",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=65536,
        description="The user's new message",
    )
    history: list[MessageInput] = Field(
        default_factory=list,
        max_length=100,
        description="Prior conversation turns for stateless mode",
    )
    stream: bool = Field(default=False, description="Enable SSE streaming")
    ai_config_id: uuid.UUID | None = Field(
        default=None, description="Override AI configuration"
    )
    # Knowledge / Memory controls
    use_knowledge: bool = Field(default=True)
    use_memory: bool = Field(default=True)
    memory_session_scope: bool = Field(
        default=True, description="Restrict memory retrieval to the current session"
    )
    # Tool controls
    tools_enabled: bool = Field(default=True)
    allowed_tools: list[str] = Field(
        default_factory=list,
        description="Explicit allow-list of tool names; empty = all active tools",
    )
    # Arbitrary context forwarded to tools
    context: dict[str, Any] = Field(default_factory=dict)
    # Optional metadata stored on the conversation
    chat_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("session_id", mode="before")
    @classmethod
    def strip_session_id(cls, v: str | None) -> str | None:
        return v.strip() if v else v

    model_config = {"str_strip_whitespace": True}


# ─── Streaming ────────────────────────────────────────────────────────────────


class ToolCallChunk(BaseModel):
    """Partial / complete tool call emitted during streaming."""

    id: str
    name: str
    arguments: str  # JSON string (may be partial during streaming)


class StreamChunk(BaseModel):
    """
    A single Server-Sent Event (SSE) data payload.

    Clients should buffer ``delta`` events and concatenate the ``text``
    fields to reconstruct the full assistant message.
    """

    event: StreamEventType
    # delta / start / done
    text: str | None = None
    # tool events
    tool_call: ToolCallChunk | None = None
    tool_result: dict[str, Any] | None = None
    # done event
    message_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    tokens_used: int | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None
    # error event
    error: str | None = None
    error_code: str | None = None


# ─── Non-streaming Response ───────────────────────────────────────────────────


class ChatResponse(BaseModel):
    """
    Returned by POST /chat when ``stream=False``.
    """

    message_id: uuid.UUID
    conversation_id: uuid.UUID
    session_id: str
    content: str
    role: Literal[MessageRole.assistant] = MessageRole.assistant
    tool_calls: list[dict[str, Any]] | None = None
    tool_results: list[dict[str, Any]] | None = None
    model_used: str
    provider_used: str
    tokens_used: int
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    latency_ms: int
    knowledge_chunks_used: int = 0
    memory_items_used: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Conversation ─────────────────────────────────────────────────────────────


class ConversationResponse(BaseModel):
    id: uuid.UUID
    session_id: str
    user_id: uuid.UUID | None
    title: str | None
    status: ConversationStatus
    message_count: int
    total_tokens: int
    total_cost_usd: float
    started_at: datetime | None
    ended_at: datetime | None
    ai_config_id: uuid.UUID | None
    conv_metadata: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=512)
    status: ConversationStatus | None = None
    conv_metadata: dict[str, Any] | None = None


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int
    page: int
    page_size: int


# ─── Message ──────────────────────────────────────────────────────────────────


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    content: str | None
    tool_calls: list[dict[str, Any]] | None
    tool_results: list[dict[str, Any]] | None
    tokens_used: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    model_used: str | None
    provider_used: str | None
    latency_ms: int | None
    cost_usd: float | None
    is_error: bool
    error_code: str | None
    msg_metadata: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    total: int
    conversation_id: uuid.UUID
