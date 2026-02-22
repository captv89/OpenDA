"""Celery application factory."""

from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "openda",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,            # re-queue on worker crash
    worker_prefetch_multiplier=1,   # one task at a time per worker
    result_expires=3600,            # keep results for 1 hour
    timezone="UTC",
    enable_utc=True,
)
