"""Celery configuration for historical research jobs."""

from celery import Celery

from app.config import Settings

settings = Settings()

celery_app = Celery(
    "quant_engine",
    broker=settings.redis_url.get_secret_value(),
    backend=settings.redis_url.get_secret_value(),
    include=[
        "app.tasks.strategy_runner",
        "app.tasks.data_sync",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    result_expires=86400,
    worker_prefetch_multiplier=1,
    task_acks_late=False,
    task_publish_retry=False,
    broker_connection_timeout=5,
    broker_connection_retry_on_startup=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "artifact-health-every-five-minutes": {
            "task": "quant.artifact_health",
            "schedule": 300.0,
        },
    },
)
