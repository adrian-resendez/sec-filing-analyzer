from __future__ import annotations

from celery import Celery

from apps.api.config import get_settings
from apps.api.extensions import initialize_database
from apps.api.utils.logging import configure_logging

configure_logging()
settings = get_settings()
initialize_database(settings.database_url)

celery_app = Celery(
    "sec_filing_analyzer",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "apps.worker.tasks.analyze_filing",
        "apps.worker.tasks.backfill_filings",
    ],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)
