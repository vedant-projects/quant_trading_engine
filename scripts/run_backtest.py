"""CLI for foreground or Celery-based historical simulations."""

import argparse
import json
from uuid import uuid4

from app.backtest.jobs import execute_job
from app.schemas.job import BacktestJobInput


def main() -> None:
    """Parse a research job and run or enqueue it."""
    parser = argparse.ArgumentParser(
        description="Run an isolated, risk-gated historical simulation."
    )

    parser.add_argument("--dataset", default="demo")
    parser.add_argument(
        "--strategy",
        choices=["ma_cross", "bollinger"],
        default="ma_cross",
    )
    parser.add_argument("--symbol", default="TEST")
    parser.add_argument(
        "--timeframe",
        choices=["1m", "5m", "15m", "1h", "1d"],
        default="1h",
    )
    parser.add_argument("--currency", default="USD")
    parser.add_argument("--cash", default="10000")
    parser.add_argument("--quantity", default="1")
    parser.add_argument("--fee-bps", default="5")
    parser.add_argument("--slippage-bps", default="2")
    parser.add_argument("--periods-per-year", type=int)

    parser.add_argument("--fast", type=int, default=5)
    parser.add_argument("--slow", type=int, default=20)
    parser.add_argument("--window", type=int, default=20)
    parser.add_argument("--width", default="2")

    parser.add_argument("--persist", action="store_true")
    parser.add_argument("--background", action="store_true")

    arguments = parser.parse_args()

    if arguments.strategy == "ma_cross":
        parameters = {
            "fast_window": arguments.fast,
            "slow_window": arguments.slow,
            "quantity": arguments.quantity,
        }
    else:
        parameters = {
            "window": arguments.window,
            "width": arguments.width,
            "quantity": arguments.quantity,
        }

    request = BacktestJobInput.model_validate(
        {
            "dataset": arguments.dataset,
            "strategy": arguments.strategy,
            "symbol": arguments.symbol,
            "timeframe": arguments.timeframe,
            "currency": arguments.currency,
            "parameters": parameters,
            "initial_cash": arguments.cash,
            "fee_bps": arguments.fee_bps,
            "slippage_bps": arguments.slippage_bps,
            "periods_per_year": arguments.periods_per_year,
            "persist": arguments.persist,
        }
    )

    job_id = uuid4()

    if arguments.background:
        from app.tasks.celery_app import celery_app

        celery_app.send_task(
            "quant.run_historical_job",
            args=[request.model_dump(mode="json")],
            task_id=str(job_id),
        )
        print(f"Queued historical job: {job_id}")
    else:
        result = execute_job(request, job_id)
        print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
