"""Concrete strategy configuration and initialization tests."""

from decimal import Decimal

import pytest

from app.data.demo import make_demo_bars
from app.strategies.registry import build_strategy


def test_unknown_strategy_is_rejected() -> None:
    """The registry does not import arbitrary implementations."""
    with pytest.raises(ValueError):
        build_strategy(
            "arbitrary.module",
            strategy_id="test",
            parameters={},
        )


def test_invalid_ma_windows_are_rejected() -> None:
    """Fast and slow windows must have the correct ordering."""
    with pytest.raises(ValueError):
        build_strategy(
            "ma_cross",
            strategy_id="test",
            parameters={
                "fast_window": 20,
                "slow_window": 10,
            },
        )


def test_unknown_parameter_is_rejected() -> None:
    """Misspelled configuration cannot silently change behavior."""
    with pytest.raises(ValueError):
        build_strategy(
            "bollinger",
            strategy_id="test",
            parameters={"widht": "2"},
        )


@pytest.mark.asyncio
async def test_ma_warmup_and_signal_contract() -> None:
    """Warmup emits no signals and later output uses the current close time."""
    strategy = build_strategy(
        "ma_cross",
        strategy_id="test",
        parameters={
            "fast_window": 2,
            "slow_window": 5,
            "quantity": "1",
        },
    )

    bars = make_demo_bars(10)

    await strategy.initialize(bars[:5])
    signals = await strategy.on_data(bars[5])

    assert len(signals) == 1
    assert signals[0].timestamp == bars[5].timestamp
    assert signals[0].strategy_id == "test"
    assert signals[0].target_quantity in {
        Decimal("0"),
        Decimal("1"),
    }
