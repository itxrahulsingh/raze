"""
AI Observability and decision tracking for RAZE AI OS.
Tracks all AI decisions, model selections, and performance metrics.
"""

import logging
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, timedelta
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from redis.asyncio import Redis

from app.models.analytics import ObservabilityLog, UsageMetrics, UserSession
from app.config import get_settings

logger = logging.getLogger(__name__)


class ObservabilityEngine:
    """AI decision observability and tracking."""

    def __init__(self, db_session: AsyncSession, redis: Redis):
        self.db = db_session
        self.redis = redis
        self.settings = get_settings()

        # Cost per 1M tokens for major models
        self.token_costs = {
            "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
            "claude-3-opus": {"prompt": 0.015, "completion": 0.075},
            "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
            "gemini-pro": {"prompt": 0.0005, "completion": 0.00015},
            "grok": {"prompt": 0.005, "completion": 0.015},
        }

    async def log_decision(
        self,
        conversation_id: str,
        message_id: str,
        intent: str,
        model: str,
        tools_considered: List[str],
        tool_selected: Optional[str],
        confidence: float,
        context_retrieved: Optional[Dict] = None,
        decision_path: Optional[Dict] = None,
        latency_ms: Optional[int] = None,
        cost_usd: Optional[float] = None,
        metadata: Optional[Dict] = None
    ) -> ObservabilityLog:
        """Log an AI decision for observability."""
        try:
            log_entry = ObservabilityLog(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                message_id=message_id,
                event_type="ai_decision",
                intent_detected=intent,
                model_selected=model,
                model_reason="selected based on routing strategy",
                tools_considered=tools_considered,
                tool_selected=tool_selected,
                confidence_score=confidence,
                context_retrieved=context_retrieved or {},
                decision_path=decision_path or {},
                latency_ms=latency_ms or 0,
                cost_usd=cost_usd or 0.0,
                metadata=metadata or {}
            )

            self.db.add(log_entry)
            await self.db.flush()

            # Also cache in Redis for fast access
            cache_key = f"raze:observability:{message_id}"
            await self.redis.setex(
                cache_key,
                86400,  # 24h TTL
                log_entry.id
            )

            logger.info(f"Logged decision {log_entry.id} - intent: {intent}, model: {model}")
            return log_entry

        except Exception as e:
            logger.error(f"Error logging decision: {e}")
            raise

    async def get_decision_trace(self, message_id: str) -> Optional[ObservabilityLog]:
        """Get full decision trace for a message."""
        try:
            stmt = select(ObservabilityLog).where(ObservabilityLog.message_id == message_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting decision trace: {e}")
            return None

    async def replay_decision(self, message_id: str) -> Optional[Dict]:
        """Replay decision logs for debugging."""
        try:
            log = await self.get_decision_trace(message_id)
            if not log:
                return None

            return {
                "id": log.id,
                "timestamp": log.created_at.isoformat(),
                "intent": log.intent_detected,
                "model": log.model_selected,
                "confidence": log.confidence_score,
                "latency_ms": log.latency_ms,
                "cost_usd": log.cost_usd,
                "tools_considered": log.tools_considered,
                "tool_selected": log.tool_selected,
                "context_retrieved": log.context_retrieved,
                "decision_path": log.decision_path,
                "metadata": log.metadata
            }
        except Exception as e:
            logger.error(f"Error replaying decision: {e}")
            return None

    def calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """Calculate cost in USD for token usage."""
        try:
            costs = self.token_costs.get(model, {"prompt": 0.001, "completion": 0.001})

            prompt_cost = (prompt_tokens / 1_000_000) * costs["prompt"]
            completion_cost = (completion_tokens / 1_000_000) * costs["completion"]

            return prompt_cost + completion_cost
        except Exception as e:
            logger.error(f"Error calculating cost: {e}")
            return 0.0

    async def track_token_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        conversation_id: str
    ) -> float:
        """Track token usage and calculate cost."""
        try:
            cost = self.calculate_cost(model, prompt_tokens, completion_tokens)

            # Update daily metrics in Redis
            today = datetime.utcnow().strftime("%Y-%m-%d")
            metrics_key = f"raze:metrics:{today}"

            await self.redis.hincrby(metrics_key, "total_requests", 1)
            await self.redis.hincrbyfloat(metrics_key, "total_tokens", prompt_tokens + completion_tokens)
            await self.redis.hincrbyfloat(metrics_key, "total_cost_usd", cost)
            await self.redis.expire(metrics_key, 90 * 86400)  # Keep for 90 days

            return cost
        except Exception as e:
            logger.error(f"Error tracking token usage: {e}")
            return 0.0

    async def get_daily_metrics(self, date: Optional[str] = None) -> Dict:
        """Get aggregated daily metrics."""
        try:
            if not date:
                date = datetime.utcnow().strftime("%Y-%m-%d")

            metrics_key = f"raze:metrics:{date}"
            metrics = await self.redis.hgetall(metrics_key)

            return {
                "date": date,
                "total_requests": int(metrics.get(b"total_requests", 0) or 0),
                "total_tokens": float(metrics.get(b"total_tokens", 0) or 0),
                "total_cost_usd": float(metrics.get(b"total_cost_usd", 0) or 0),
                "avg_latency_ms": float(metrics.get(b"avg_latency_ms", 0) or 0)
            }
        except Exception as e:
            logger.error(f"Error getting daily metrics: {e}")
            return {}

    async def get_metrics_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Get metrics for date range."""
        try:
            stmt = select(UsageMetrics).where(
                UsageMetrics.date >= start_date,
                UsageMetrics.date <= end_date
            ).order_by(UsageMetrics.date)

            result = await self.db.execute(stmt)
            metrics = result.scalars().all()

            return [
                {
                    "date": m.date.isoformat() if hasattr(m.date, 'isoformat') else str(m.date),
                    "total_requests": m.total_requests,
                    "total_tokens": m.total_tokens,
                    "total_cost_usd": m.total_cost_usd,
                    "avg_latency_ms": m.avg_latency_ms,
                    "tool_executions": m.tool_executions,
                    "knowledge_queries": m.knowledge_queries,
                    "unique_users": m.unique_users,
                    "error_count": m.error_count
                }
                for m in metrics
            ]
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return []

    async def get_model_usage_stats(self) -> Dict[str, Any]:
        """Get model usage statistics."""
        try:
            stmt = select(
                ObservabilityLog.model_selected,
                func.count(ObservabilityLog.id).label("usage_count"),
                func.avg(ObservabilityLog.latency_ms).label("avg_latency"),
                func.avg(ObservabilityLog.cost_usd).label("avg_cost"),
                func.avg(ObservabilityLog.confidence_score).label("avg_confidence")
            ).group_by(ObservabilityLog.model_selected)

            result = await self.db.execute(stmt)
            rows = result.all()

            return {
                row[0]: {
                    "usage_count": row[1],
                    "avg_latency_ms": float(row[2] or 0),
                    "avg_cost_usd": float(row[3] or 0),
                    "avg_confidence": float(row[4] or 0)
                }
                for row in rows
            }
        except Exception as e:
            logger.error(f"Error getting model stats: {e}")
            return {}

    async def get_intent_distribution(self) -> Dict[str, int]:
        """Get distribution of detected intents."""
        try:
            stmt = select(
                ObservabilityLog.intent_detected,
                func.count(ObservabilityLog.id).label("count")
            ).group_by(ObservabilityLog.intent_detected)

            result = await self.db.execute(stmt)
            rows = result.all()

            return {row[0]: row[1] for row in rows}
        except Exception as e:
            logger.error(f"Error getting intent distribution: {e}")
            return {}

    async def get_tool_usage_stats(self) -> Dict[str, Any]:
        """Get tool usage statistics."""
        try:
            stmt = select(
                ObservabilityLog.tool_selected,
                func.count(ObservabilityLog.id).label("usage_count")
            ).where(ObservabilityLog.tool_selected != None).group_by(ObservabilityLog.tool_selected)

            result = await self.db.execute(stmt)
            rows = result.all()

            return {row[0]: {"usage_count": row[1]} for row in rows}
        except Exception as e:
            logger.error(f"Error getting tool stats: {e}")
            return {}

    async def rollup_metrics_to_db(self) -> None:
        """Background task: Rollup daily metrics from Redis to DB."""
        try:
            yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
            metrics_key = f"raze:metrics:{yesterday}"

            metrics = await self.redis.hgetall(metrics_key)
            if not metrics:
                return

            # Create or update daily aggregate
            existing = await self.db.execute(
                select(UsageMetrics).where(UsageMetrics.date == yesterday)
            )
            daily_metrics = existing.scalar_one_or_none()

            if not daily_metrics:
                daily_metrics = UsageMetrics(
                    id=str(uuid.uuid4()),
                    date=yesterday,
                    total_requests=int(metrics.get(b"total_requests", 0) or 0),
                    total_tokens=float(metrics.get(b"total_tokens", 0) or 0),
                    total_cost_usd=float(metrics.get(b"total_cost_usd", 0) or 0),
                    avg_latency_ms=float(metrics.get(b"avg_latency_ms", 0) or 0)
                )
                self.db.add(daily_metrics)
            else:
                daily_metrics.total_requests = int(metrics.get(b"total_requests", 0) or 0)
                daily_metrics.total_tokens = float(metrics.get(b"total_tokens", 0) or 0)
                daily_metrics.total_cost_usd = float(metrics.get(b"total_cost_usd", 0) or 0)

            await self.db.commit()
            logger.info(f"Rolled up metrics for {yesterday}")
        except Exception as e:
            logger.error(f"Error rolling up metrics: {e}")
