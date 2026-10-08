"""Risk-gated, single-instrument event-driven historical replay."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.backtest.report import build_report
from app.brokers.paper import PaperBroker
from app.core.execution_manager import ExecutedOrder, ExecutionManager
from app.core.portfolio_manager import (
    PortfolioManager,
    PortfolioValuation,
)
from app.core.risk_manager import RiskManager
from app.core.strategy_engine import StrategyEngine
from app.data.historical_loader import validate_bar_sequence
from app.data.timeframes import calendar_periods_per_year
from app.schemas.backtest import BacktestReport, EquityPoint
from app.strategies.base import BaseStrategy, MarketBar, Signal


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """Collect a report and its auditable simulator records."""

    report: BacktestReport
    signals: tuple[Signal, ...]
    executions: tuple[ExecutedOrder, ...]
    snapshots: tuple[PortfolioValuation, ...]
    rejections: tuple[str, ...]


async def run_backtest(
    strategy: BaseStrategy,
    bars: Sequence[MarketBar],
    *,
    initial_cash: Decimal = Decimal("10000"),
    fee_bps: Decimal = Decimal("5"),
    slippage_bps: Decimal = Decimal("2"),
    max_daily_loss_pct: Decimal = Decimal("2"),
    max_position_pct: Decimal = Decimal("10"),
    periods_per_year: int | None = None,
    currency: str = "USD",
) -> SimulationResult:
    """Replay fixed-width continuous bars through the mandatory risk gate."""
    validate_bar_sequence(bars)
    strategy.validate_parameters()

    requirements = strategy.get_required_data()

    if len(requirements) != 1:
        raise ValueError("The initial replay supports one data stream.")

    requirement = requirements[0]

    if (
        bars[0].symbol != requirement.symbol
        or bars[0].timeframe != requirement.timeframe
    ):
        raise ValueError("Dataset does not match strategy requirements.")

    warmup = max(requirement.warmup_bars, 1)

    if len(bars) < warmup + 2:
        raise ValueError("At least two post-warmup bars are required.")

    history = bars[:warmup]
    await strategy.initialize(history)

    portfolio = PortfolioManager(
        strategy_id=strategy.strategy_id,
        symbol=requirement.symbol,
        initial_cash=initial_cash,
        started_at=history[-1].timestamp,
    )
    portfolio.mark(history[-1].close)

    risk_manager = RiskManager(
        portfolio,
        max_daily_loss_pct=max_daily_loss_pct,
        max_position_pct=max_position_pct,
    )
    risk_manager.observe(history[-1].timestamp)

    broker = PaperBroker(
        risk_manager,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
    )

    execution_manager = ExecutionManager(
        strategy=strategy,
        broker=broker,
        portfolio=portfolio,
    )
    engine = StrategyEngine(
        strategy=strategy,
        execution_manager=execution_manager,
        risk_manager=risk_manager,
    )

    snapshots = [portfolio.valuation(history[-1].timestamp)]

    await broker.connect()

    try:
        for bar in bars[warmup:]:
            await engine.process_bar(bar)
            snapshots.append(portfolio.valuation(bar.timestamp))
    finally:
        await broker.disconnect()

    frequency = (
        periods_per_year
        if periods_per_year is not None
        else calendar_periods_per_year(requirement.timeframe)
    )

    report = build_report(
        strategy_id=strategy.strategy_id,
        symbol=requirement.symbol,
        currency=currency,
        equity_curve=[
            EquityPoint(
                timestamp=snapshot.timestamp,
                equity=float(snapshot.equity),
            )
            for snapshot in snapshots
        ],
        periods_per_year=frequency,
    )

    report.notes.extend(
        [
            "Local long-only simulator; not broker paper trading.",
            "Signals execute at the following bar's opening event.",
            "Fixed-bps adverse slippage and proportional commissions.",
            "The final pending signal is not executed.",
            "Open positions remain marked; no forced final liquidation.",
            "UTC daily-loss state is isolated to this simulation.",
            f"Risk-rejected proposals: {len(engine.rejections)}.",
        ]
    )

    return SimulationResult(
        report=report,
        signals=tuple(engine.signals),
        executions=tuple(execution_manager.executions),
        snapshots=tuple(snapshots),
        rejections=tuple(engine.rejections),
    )
