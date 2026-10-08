"""Celery entrypoint for isolated historical simulations."""

from typing import Any
from uuid import UUID

from app.backtest.jobs import execute_job
from app.schemas.job import BacktestJobInput
from app.tasks.celery_app import celery_app


def run_historical_job(
    task: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate and execute one job without automatic order-related retries."""
    request = BacktestJobInput.model_validate(payload)
    job_id = UUID(str(task.request.id))

    return execute_job(request, job_id)


celery_app.task(
    bind=True,
    name="quant.run_historical_job",
)(run_historical_job)
