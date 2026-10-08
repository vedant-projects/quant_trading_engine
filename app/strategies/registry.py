"""Explicit allowlist of executable strategy implementations."""

from collections.abc import Mapping

from app.strategies.base import BaseStrategy
from app.strategies.bollinger import BollingerStrategy
from app.strategies.moving_average import MovingAverageStrategy

STRATEGIES: dict[str, type[BaseStrategy]] = {
    "ma_cross": MovingAverageStrategy,
    "bollinger": BollingerStrategy,
}


def build_strategy(
    name: str,
    *,
    strategy_id: str,
    parameters: Mapping[str, object],
) -> BaseStrategy:
    """Construct a registered strategy without arbitrary dynamic imports."""
    try:
        implementation = STRATEGIES[name]
    except KeyError as exc:
        raise ValueError(f"Unsupported strategy: {name}") from exc

    return implementation(
        strategy_id=strategy_id,
        parameters=parameters,
    )
