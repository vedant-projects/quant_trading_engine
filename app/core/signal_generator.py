"""Validate strategy proposals before they enter the execution queue."""

from app.strategies.base import BaseStrategy, MarketBar, Signal


async def generate_signals(
    strategy: BaseStrategy,
    bar: MarketBar,
) -> tuple[Signal, ...]:
    """Reject mismatched or incorrectly dated strategy output."""
    signals = await strategy.on_data(bar)

    if not isinstance(signals, tuple):
        raise TypeError("on_data must return a tuple of Signal objects.")

    for signal in signals:
        if not isinstance(signal, Signal):
            raise TypeError("Strategy returned a non-Signal object.")

        if (
            signal.strategy_id != strategy.strategy_id
            or signal.symbol != bar.symbol
            or signal.timestamp != bar.timestamp
        ):
            raise ValueError("Strategy returned a mismatched signal.")

    return signals
