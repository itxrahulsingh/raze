"""
RAZE Enterprise AI OS – Analytics Schemas

Covers observability log retrieval, daily usage metrics, and date-range
query helpers.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


# ─── Date Range ───────────────────────────────────────────────────────────────


class DateRangeRequest(BaseModel):
    """
    Shared query body for any endpoint that returns time-series data.

    ``start_date`` and ``end_date`` are inclusive; ``end_date`` defaults
    to today when omitted.
    """

    start_date: date = Field(..., description="Inclusive start date (YYYY-MM-DD)")
    end_date: date | None = Field(
        default=None, description="Inclusive end date; defaults to today"
    )
    granularity: str = Field(
        default="day",
        pattern="^(hour|day|week|month)$",
        description="Aggregation granularity",
    )
    timezone: str = Field(
        default="UTC",
        max_length=64,
        description="IANA timezone name for bucketing (e.g. 'America/New_York')",
    )

    @model_validator(mode="after")
    def validate_date_range(self) -> "DateRangeRequest":
        end = self.end_date or date.today()
        if self.start_date > end:
            raise ValueError("start_date must be before or equal to end_date")
        if (end - self.start_date).days > 366:
            raise ValueError("Date range cannot exceed 366 days")
        self.end_date = end
        return self


# ─── Observability Log ────────────────────────────────────────────────────────


class ObservabilityLogResponse(BaseModel):
    """
    Single observability log record.  Returned by GET /analytics/logs
    and GET /analytics/logs/{id}.
    """

    id: uuid.UUID
    conversation_id: uuid.UUID | None
    message_id: uuid.UUID | None
    event_type: str
    intent_detected: str | None
    model_selected: str | None
    model_reason: str | None
    provider_selected: str | None
    routing_strategy_used: str | None
    tools_considered: list[str]
    tool_selected: str | None
    tool_selection_reason: str | None
    confidence_score: float | None
    context_retrieved: list[dict[str, Any]]
    knowledge_chunks_used: int
    memory_items_used: int
    decision_path: list[dict[str, Any]]
    latency_ms: int | None
    ttft_ms: int | None
    cost_usd: float | None
    tokens_prompt: int | None
    tokens_completion: int | None
    log_metadata: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class ObservabilityLogListResponse(BaseModel):
    items: list[ObservabilityLogResponse]
    total: int
    page: int
    page_size: int


class ObservabilityLogFilterRequest(BaseModel):
    """Query filters for GET /analytics/logs."""

    conversation_id: uuid.UUID | None = None
    message_id: uuid.UUID | None = None
    event_type: str | None = None
    model_selected: str | None = None
    provider_selected: str | None = None
    tool_selected: str | None = None
    min_cost_usd: float | None = Field(default=None, ge=0.0)
    max_cost_usd: float | None = Field(default=None, ge=0.0)
    min_latency_ms: int | None = Field(default=None, ge=0)
    max_latency_ms: int | None = Field(default=None, ge=0)
    start_date: datetime | None = None
    end_date: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)

    model_config = {"protected_namespaces": ()}


# ─── Usage Metrics ────────────────────────────────────────────────────────────


class UsageMetricsResponse(BaseModel):
    """Daily aggregate metrics row."""

    id: uuid.UUID
    date: date
    total_requests: int
    total_tokens: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost_usd: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    tool_executions: int
    tool_failures: int
    knowledge_queries: int
    memory_reads: int
    memory_writes: int
    unique_users: int
    unique_sessions: int
    new_conversations: int
    error_count: int
    provider_breakdown: dict[str, Any]
    model_breakdown: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class UsageMetricsListResponse(BaseModel):
    items: list[UsageMetricsResponse]
    total: int
    # Aggregate totals across the returned range
    totals: "UsageMetricsTotals"


class UsageMetricsTotals(BaseModel):
    total_requests: int
    total_tokens: int
    total_cost_usd: float
    avg_latency_ms: float
    tool_executions: int
    knowledge_queries: int
    unique_users: int
    error_count: int


# ─── User Session ────────────────────────────────────────────────────────────


class UserSessionResponse(BaseModel):
    id: uuid.UUID
    session_id: str
    user_id: uuid.UUID | None
    ip_address: str | None
    device_type: str | None
    os_info: str | None
    browser_info: str | None
    country: str | None
    city: str | None
    referrer: str | None
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    started_at: datetime
    last_seen: datetime
    message_count: int
    is_active: bool
    session_metadata: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserSessionListResponse(BaseModel):
    items: list[UserSessionResponse]
    total: int
    page: int
    page_size: int


# ─── Aggregated Charts ────────────────────────────────────────────────────────


class TimeSeriesPoint(BaseModel):
    timestamp: str  # ISO-8601 bucket label
    value: float


class MetricSeries(BaseModel):
    """A named metric time series."""

    metric: str
    unit: str
    data: list[TimeSeriesPoint]
    total: float
    avg: float
    min: float
    max: float


class AnalyticsSummaryResponse(BaseModel):
    """
    Returned by GET /analytics/summary for the dashboard overview.
    """

    period: DateRangeRequest
    series: list[MetricSeries]
    top_models: list[dict[str, Any]]
    top_tools: list[dict[str, Any]]
    geo_distribution: list[dict[str, Any]]
    device_distribution: list[dict[str, Any]]
    generated_at: datetime
