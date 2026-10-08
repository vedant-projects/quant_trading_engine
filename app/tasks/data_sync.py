"""Scheduled artifact heartbeat for local monitoring."""

import json
from datetime import UTC, datetime
from typing import Any

from redis import Redis

from app.config import Settings
from app.tasks.celery_app import celery_app


def artifact_health() -> dict[str, Any]:
    """Store counts of available datasets and reports in Redis."""
    settings = Settings()

    payload: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "dataset_count": len(list(settings.data_directory.glob("*.csv"))),
        "report_count": len(list(settings.report_directory.glob("*.json"))),
    }

    client = Redis.from_url(
        settings.redis_url.get_secret_value(),
        socket_connect_timeout=3,
        socket_timeout=3,
    )

    try:
        client.set(
            "quant:artifact_health",
            json.dumps(payload, allow_nan=False),
            ex=900,
        )
    finally:
        client.close()

    return payload


celery_app.task(name="quant.artifact_health")(artifact_health)
