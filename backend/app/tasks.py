"""Celery tasks for ingestion and maintenance jobs."""

from __future__ import annotations

import asyncio
import uuid

import structlog

from app.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="app.tasks.process_knowledge_source")
def process_knowledge_source(source_id: str) -> dict[str, str]:
    """Ingest/re-index one knowledge source by ID."""
    from app.api.v1.knowledge import _process_knowledge_source_bg

    try:
        asyncio.run(_process_knowledge_source_bg(uuid.UUID(source_id)))
        return {"status": "ok", "source_id": source_id}
    except Exception as exc:
        logger.error("celery.process_knowledge_source.failed", source_id=source_id, error=str(exc))
        raise


@celery_app.task(name="app.tasks.run_maintenance_jobs")
def run_maintenance_jobs() -> dict[str, str]:
    """Run periodic memory/audit maintenance jobs."""
    from app.core.background_tasks import run_all_background_tasks

    try:
        asyncio.run(run_all_background_tasks())
        return {"status": "ok"}
    except Exception as exc:
        logger.error("celery.run_maintenance_jobs.failed", error=str(exc))
        raise
