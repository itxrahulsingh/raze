"""
RAZE Enterprise AI OS – Metrics & Observability

Provides:
  - Structured metrics collection
  - Prometheus-compatible metrics
  - Performance tracking
  - Business metrics
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator

import structlog

logger = structlog.get_logger(__name__)


class Metrics:
    """Application metrics collection."""

    def __init__(self):
        self.api_requests_total = {}
        self.api_latency_seconds = {}
        self.llm_tokens_total = {}
        self.vector_search_count = {}
        self.knowledge_chunks_total = 0
        self.memories_total = 0
        self.errors_total = {}

    def record_api_request(self, endpoint: str, method: str, status_code: int) -> None:
        """Record API request."""
        key = f"{method}_{endpoint}_{status_code}"
        self.api_requests_total[key] = self.api_requests_total.get(key, 0) + 1

    def record_api_latency(self, endpoint: str, latency_ms: float) -> None:
        """Record API latency."""
        if endpoint not in self.api_latency_seconds:
            self.api_latency_seconds[endpoint] = []
        self.api_latency_seconds[endpoint].append(latency_ms / 1000.0)

    def record_llm_tokens(self, provider: str, model: str, tokens: int) -> None:
        """Record LLM token usage."""
        key = f"{provider}_{model}"
        self.llm_tokens_total[key] = self.llm_tokens_total.get(key, 0) + tokens

    def record_vector_search(self, collection: str, latency_ms: float) -> None:
        """Record vector search."""
        key = collection
        if key not in self.vector_search_count:
            self.vector_search_count[key] = {
                "count": 0,
                "total_latency_ms": 0,
            }
        self.vector_search_count[key]["count"] += 1
        self.vector_search_count[key]["total_latency_ms"] += latency_ms

    def record_error(self, error_type: str, endpoint: str) -> None:
        """Record error."""
        key = f"{error_type}_{endpoint}"
        self.errors_total[key] = self.errors_total.get(key, 0) + 1

    def get_api_stats(self, endpoint: str | None = None) -> dict[str, Any]:
        """Get API statistics."""
        if endpoint:
            latencies = self.api_latency_seconds.get(endpoint, [])
            if not latencies:
                return {"endpoint": endpoint, "requests": 0, "avg_latency_ms": 0}

            return {
                "endpoint": endpoint,
                "requests": len(latencies),
                "avg_latency_ms": sum(latencies) / len(latencies) * 1000,
                "min_latency_ms": min(latencies) * 1000,
                "max_latency_ms": max(latencies) * 1000,
            }

        return {
            "total_requests": sum(self.api_requests_total.values()),
            "total_errors": sum(self.errors_total.values()),
            "endpoints": len(self.api_latency_seconds),
        }

    def get_llm_stats(self) -> dict[str, Any]:
        """Get LLM statistics."""
        return {
            "total_tokens": sum(self.llm_tokens_total.values()),
            "by_provider": self.llm_tokens_total,
        }

    def get_vector_stats(self) -> dict[str, Any]:
        """Get vector search statistics."""
        return {
            "total_searches": sum(s["count"] for s in self.vector_search_count.values()),
            "by_collection": self.vector_search_count,
        }


# Global metrics instance
_metrics = Metrics()


def get_metrics() -> Metrics:
    """Get the global metrics instance."""
    return _metrics


@asynccontextmanager
async def track_latency(operation_name: str) -> AsyncGenerator[None, None]:
    """
    Context manager to track operation latency.

    Usage:
        async with track_latency("knowledge_search"):
            # do operation
    """
    start_time = time.time()
    try:
        yield
    finally:
        latency_ms = (time.time() - start_time) * 1000
        logger.info(
            "operation_latency",
            operation=operation_name,
            latency_ms=round(latency_ms, 2),
        )


def log_api_call(
    endpoint: str,
    method: str,
    status_code: int,
    latency_ms: float,
    user_id: str | None = None,
) -> None:
    """Log API call with metrics."""
    _metrics.record_api_request(endpoint, method, status_code)
    _metrics.record_api_latency(endpoint, latency_ms)

    logger.info(
        "api_call",
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        latency_ms=round(latency_ms, 2),
        user_id=user_id,
    )


def log_llm_call(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
) -> None:
    """Log LLM call with metrics."""
    total_tokens = prompt_tokens + completion_tokens
    _metrics.record_llm_tokens(provider, model, total_tokens)

    logger.info(
        "llm_call",
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        latency_ms=round(latency_ms, 2),
    )


def log_vector_search(collection: str, latency_ms: float, results_count: int) -> None:
    """Log vector search with metrics."""
    _metrics.record_vector_search(collection, latency_ms)

    logger.info(
        "vector_search",
        collection=collection,
        latency_ms=round(latency_ms, 2),
        results_count=results_count,
    )


def export_prometheus_metrics() -> str:
    """Export metrics in Prometheus format."""
    lines = []
    lines.append("# HELP raze_api_requests_total Total API requests")
    lines.append("# TYPE raze_api_requests_total counter")

    for key, value in _metrics.api_requests_total.items():
        lines.append(f'raze_api_requests_total{{endpoint="{key}"}} {value}')

    lines.append("# HELP raze_llm_tokens_total Total LLM tokens")
    lines.append("# TYPE raze_llm_tokens_total counter")

    for key, value in _metrics.llm_tokens_total.items():
        lines.append(f'raze_llm_tokens_total{{model="{key}"}} {value}')

    lines.append("# HELP raze_errors_total Total errors")
    lines.append("# TYPE raze_errors_total counter")

    for key, value in _metrics.errors_total.items():
        lines.append(f'raze_errors_total{{error="{key}"}} {value}')

    return "\n".join(lines)
