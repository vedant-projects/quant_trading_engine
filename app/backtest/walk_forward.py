"""Chronological evaluation windows with independent simulated accounts."""

from collections.abc import Mapping, Sequence

from app.backtest.engine import SimulationResult, run_backtest
from app.strategies.base import MarketBar
from app.strategies.registry import build_strategy


async def evaluate_windows(
    *,
    strategy_name: str,
    parameters: Mapping[str, object],
    bars: Sequence[MarketBar],
    test_bars: int = 100,
) -> list[SimulationResult]:
    """Evaluate fixed parameters in nonoverlapping post-warmup windows."""
    if test_bars < 2:
        raise ValueError("test_bars must be at least two.")

    prototype = build_strategy(
        strategy_name,
        strategy_id="window-prototype",
        parameters=parameters,
    )

    requirements = prototype.get_required_data()

    if len(requirements) != 1:
        raise ValueError("Only one data stream is supported.")

    warmup = max(requirements[0].warmup_bars, 1)
    results: list[SimulationResult] = []

    for start in range(warmup, len(bars), test_bars):
        end = min(start + test_bars, len(bars))

        if end - start < 2:
            break

        strategy = build_strategy(
            strategy_name,
            strategy_id=f"window-{len(results) + 1}",
            parameters=parameters,
        )

        result = await run_backtest(
            strategy,
            bars[start - warmup : end],
        )
        results.append(result)

    return results
