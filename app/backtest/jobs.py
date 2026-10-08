"""Run a validated historical job and export its artifacts."""

import asyncio
import hashlib
from typing import Any
from uuid import UUID

from app.backtest.engine import run_backtest
from app.backtest.persistence import persist_simulation
from app.backtest.report import write_equity_csv, write_report_json
from app.config import Settings
from app.data.historical_loader import load_csv
from app.database import Database
from app.schemas.job import BacktestJobInput
from app.strategies.registry import build_strategy


async def _execute(
    request: BacktestJobInput,
    job_id: UUID,
    settings: Settings,
) -> dict[str, Any]:
    """Replay a dataset, optionally persist records, and export reports."""
    dataset_path = settings.data_directory / f"{request.dataset}.csv"

    bars = load_csv(
        dataset_path,
        symbol=request.symbol,
        timeframe=request.timeframe,
    )

    parameters: dict[str, object] = {
        **request.parameters,
        "symbol": request.symbol,
        "timeframe": request.timeframe,
    }

    strategy_id = f"sim-{job_id}"

    strategy = build_strategy(
        request.strategy,
        strategy_id=strategy_id,
        parameters=parameters,
    )

    result = await run_backtest(
        strategy,
        bars,
        initial_cash=request.initial_cash,
        fee_bps=request.fee_bps,
        slippage_bps=request.slippage_bps,
        max_daily_loss_pct=settings.max_daily_loss_pct,
        max_position_pct=settings.max_position_pct,
        periods_per_year=request.periods_per_year,
        currency=request.currency,
    )

    checksum = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    result.report.notes.append(f"Dataset SHA256: {checksum}")

    persisted = False

    if request.persist:
        database = Database(settings)

        try:
            persisted = await persist_simulation(
                database,
                result,
                implementation=request.strategy,
                parameters=parameters,
                account_id=f"simulation-{job_id}",
                currency=request.currency,
            )
        finally:
            await database.close()

    report_path = settings.report_directory / f"{job_id}.json"
    equity_path = settings.report_directory / f"{job_id}.csv"

    write_report_json(result.report, report_path)
    write_equity_csv(result.report, equity_path)

    return {
        "job_id": str(job_id),
        "strategy_id": strategy_id,
        "execution_count": len(result.executions),
        "rejection_count": len(result.rejections),
        "persisted": persisted,
        "metrics": result.report.metrics.model_dump(mode="json"),
    }


def execute_job(
    request: BacktestJobInput,
    job_id: UUID,
) -> dict[str, Any]:
    """Execute a historical job from a CLI or a synchronous Celery task."""
    settings = Settings()
    return asyncio.run(_execute(request, job_id, settings))
