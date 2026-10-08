"""Historical replay causality tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.backtest.engine import run_backtest
from app.strategies.base import MarketBar
from app.strategies.registry import build_strategy


def make_bars() -> list[MarketBar]:
    """Build a small series with recognizable opening prices."""
    start = datetime(2026, 1, 1, tzinfo=UTC)
    closes = ["100", "101", "102", "103", "104", "105"]

    bars: list[MarketBar] = []

    for index, value in enumerate(closes):
        close = Decimal(value)
        opening = Decimal("100") if index == 0 else Decimal(closes[index - 1])

        bars.append(
            MarketBar(
                symbol="TEST",
                timeframe="1h",
                timestamp=start + timedelta(hours=index + 1),
                open=opening,
                high=max(opening, close) + Decimal("1"),
                low=min(opening, close) - Decimal("1"),
                close=close,
                volume=Decimal("100"),
            )
        )

    return bars


@pytest.mark.asyncio
async def test_signal_executes_on_following_bar() -> None:
    """A post-warmup signal cannot fill on its own bar."""
    bars = make_bars()

    strategy = build_strategy(
        "ma_cross",
        strategy_id="test",
        parameters={
            "symbol": "TEST",
            "timeframe": "1h",
            "fast_window": 1,
            "slow_window": 2,
            "quantity": "1",
        },
    )

    result = await run_backtest(
        strategy,
        bars,
        fee_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
    )

    assert len(result.executions) == 1

    execution = result.executions[0]
    originating = next(
        signal for signal in result.signals if signal.signal_id == execution.signal_id
    )

    assert originating.timestamp == bars[2].timestamp
    assert execution.fill.timestamp == bars[3].timestamp - timedelta(hours=1)
    assert execution.fill.price == bars[3].open
    assert execution.fill.price != bars[2].open


@pytest.mark.asyncio
async def test_repeated_long_targets_do_not_stack_positions() -> None:
    """Repeated desired quantities produce one incremental purchase."""
    strategy = build_strategy(
        "ma_cross",
        strategy_id="test",
        parameters={
            "symbol": "TEST",
            "timeframe": "1h",
            "fast_window": 1,
            "slow_window": 2,
            "quantity": "1",
        },
    )

    result = await run_backtest(
        strategy,
        make_bars(),
        fee_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
    )

    bought = sum(
        (execution.fill.quantity for execution in result.executions),
        Decimal("0"),
    )

    assert bought == Decimal("1")
