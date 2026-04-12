"""
RAZE Enterprise AI OS – Admin Schemas

Covers AI configuration management, system health stats, and the
top-level admin dashboard payload.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.ai_config import LLMProvider, RoutingStrategy


# ─── AI Config ────────────────────────────────────────────────────────────────


class AIConfigCreate(BaseModel):
    """Body for POST /admin/ai-configs."""

    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2048)
    is_default: bool = Field(default=False)
    provider: LLMProvider
    model_name: str = Field(..., min_length=1, max_length=128)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=200000)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    system_prompt: str | None = Field(default=None, max_length=65536)
    # Fallback
    fallback_provider: LLMProvider | None = None
    fallback_model: str | None = Field(default=None, max_length=128)
    fallback_on_errors: list[str] = Field(
        default_factory=lambda: ["429", "503", "rate_limit_error"],
        description="Error codes / HTTP statuses that trigger the fallback",
    )
    # Budget
    cost_limit_daily: float | None = Field(
        default=None, ge=0.0, description="Max daily spend in USD"
    )
    cost_per_1k_input_tokens: float | None = Field(default=None, ge=0.0)
    cost_per_1k_output_tokens: float | None = Field(default=None, ge=0.0)
    # Routing
    routing_strategy: RoutingStrategy = Field(default=RoutingStrategy.balanced)
    # Feature toggles
    streaming_enabled: bool = True
    tool_calling_enabled: bool = True
    memory_enabled: bool = True
    knowledge_enabled: bool = True
    # Extra provider-specific params
    extra_params: dict[str, Any] = Field(default_factory=dict)

    model_config = {"str_strip_whitespace": True}


class AIConfigUpdate(BaseModel):
    """Body for PATCH /admin/ai-configs/{id} – all fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    provider: LLMProvider | None = None
    model_name: str | None = Field(default=None, min_length=1, max_length=128)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=200000)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    presence_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    frequency_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    system_prompt: str | None = None
    fallback_provider: LLMProvider | None = None
    fallback_model: str | None = None
    fallback_on_errors: list[str] | None = None
    cost_limit_daily: float | None = None
    cost_per_1k_input_tokens: float | None = None
    cost_per_1k_output_tokens: float | None = None
    routing_strategy: RoutingStrategy | None = None
    streaming_enabled: bool | None = None
    tool_calling_enabled: bool | None = None
    memory_enabled: bool | None = None
    knowledge_enabled: bool | None = None
    extra_params: dict[str, Any] | None = None

    model_config = {"str_strip_whitespace": True}


class AIConfigResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_default: bool
    is_active: bool
    provider: LLMProvider
    model_name: str
    temperature: float
    max_tokens: int
    top_p: float
    presence_penalty: float
    frequency_penalty: float
    system_prompt: str | None
    fallback_provider: LLMProvider | None
    fallback_model: str | None
    fallback_on_errors: list[str]
    cost_limit_daily: float | None
    cost_per_1k_input_tokens: float | None
    cost_per_1k_output_tokens: float | None
    routing_strategy: RoutingStrategy
    streaming_enabled: bool
    tool_calling_enabled: bool
    memory_enabled: bool
    knowledge_enabled: bool
    extra_params: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AIConfigListResponse(BaseModel):
    items: list[AIConfigResponse]
    total: int


# ─── System Stats ─────────────────────────────────────────────────────────────


class ProviderHealth(BaseModel):
    provider: str
    reachable: bool
    latency_ms: float | None
    last_checked: datetime


class SystemStats(BaseModel):
    """Live system health snapshot, served by GET /admin/stats."""

    # Counts
    total_users: int
    active_users_today: int
    total_conversations: int
    active_conversations: int
    total_knowledge_sources: int
    approved_knowledge_sources: int
    total_tools: int
    active_tools: int
    # Today's usage
    requests_today: int
    tokens_today: int
    cost_today_usd: float
    errors_today: int
    avg_latency_ms_today: float
    # Infrastructure
    db_pool_size: int
    db_checked_out_connections: int
    redis_connected: bool
    redis_memory_used_mb: float | None
    # Provider health
    provider_health: list[ProviderHealth]
    # Timestamps
    collected_at: datetime


# ─── Admin Dashboard ─────────────────────────────────────────────────────────


class TrendPoint(BaseModel):
    """A single data point in a time-series trend."""

    label: str          # e.g. "2025-04-11"
    value: float


class DashboardChart(BaseModel):
    title: str
    unit: str           # e.g. "requests", "USD", "ms"
    trend: list[TrendPoint]
    current: float
    change_pct: float | None = None  # % change vs previous period


class TopTool(BaseModel):
    tool_id: uuid.UUID
    tool_name: str
    usage_count: int
    success_rate: float
    avg_latency_ms: float


class TopModel(BaseModel):
    provider: str
    model_name: str
    request_count: int
    total_tokens: int
    total_cost_usd: float
    avg_latency_ms: float


class AdminDashboard(BaseModel):
    """
    Full admin dashboard payload returned by GET /admin/dashboard.
    Aggregated over the trailing ``period_days`` days.
    """

    period_days: int = 7
    stats: SystemStats
    # Charts
    requests_chart: DashboardChart
    tokens_chart: DashboardChart
    cost_chart: DashboardChart
    latency_chart: DashboardChart
    error_rate_chart: DashboardChart
    # Leaderboards
    top_tools: list[TopTool]
    top_models: list[TopModel]
    # AI configs
    ai_configs: list[AIConfigResponse]
    generated_at: datetime
