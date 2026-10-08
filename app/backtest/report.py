"""Construct and export performance reports."""

import csv
from collections.abc import Sequence
from pathlib import Path

from app.backtest.metrics import summarize_equity
from app.schemas.backtest import BacktestReport, EquityPoint


def build_report(
    *,
    strategy_id: str,
    symbol: str,
    currency: str,
    equity_curve: Sequence[EquityPoint],
    periods_per_year: int,
    annual_risk_free_rate: float = 0.0,
) -> BacktestReport:
    """Validate chronological observations and build a performance report."""
    points = list(equity_curve)

    if len(points) < 2:
        raise ValueError("A report requires at least two equity observations.")

    for previous, current in zip(points, points[1:], strict=False):
        if current.timestamp <= previous.timestamp:
            raise ValueError("Equity timestamps must be strictly increasing.")

    metrics = summarize_equity(
        [point.equity for point in points],
        periods_per_year=periods_per_year,
        annual_risk_free_rate=annual_risk_free_rate,
    )

    return BacktestReport(
        strategy_id=strategy_id,
        symbol=symbol,
        currency=currency,
        metrics=metrics,
        equity_curve=points,
        notes=[
            "The caller must supply a consistent observation frequency.",
            "Annualized Sharpe uses square-root-of-time scaling.",
            "Undefined ratios are represented as null.",
            "This report does not establish realistic execution quality.",
        ],
    )


def write_report_json(
    report: BacktestReport,
    destination: Path,
) -> Path:
    """Write a validated report to a UTF-8 JSON file."""
    destination.parent.mkdir(parents=True, exist_ok=True)

    destination.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return destination


def write_equity_csv(
    report: BacktestReport,
    destination: Path,
) -> Path:
    """Write the report's equity observations to CSV."""
    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as output:
        writer = csv.writer(output)
        writer.writerow(["timestamp", "equity"])

        for point in report.equity_curve:
            writer.writerow(
                [
                    point.timestamp.isoformat(),
                    point.equity,
                ]
            )

    return destination
