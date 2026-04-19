"""Celery application wiring for async production workers."""

from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "raze",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer=settings.celery_task_serializer,
    result_serializer=settings.celery_task_serializer,
    accept_content=["json"],
    result_expires=settings.celery_result_expires,
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    beat_schedule={
        "raze-memory-decay-and-prune": {
            "task": "app.tasks.run_maintenance_jobs",
            "schedule": 60 * 30,  # every 30 minutes
        }
    },
)
