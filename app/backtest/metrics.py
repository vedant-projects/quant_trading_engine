"""Performance metrics for equally spaced, positive equity observations."""

import math
from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from app.schemas.backtest import MetricsSummary


def validate_equity(
    equity: Sequence[float],
) -> NDArray[np.float64]:
    """Require at least two finite, strictly positive equity values."""
    values = np.asarray(equity, dtype=np.float64)

    if values.ndim != 1:
        raise ValueError("Equity must be a one-dimensional sequence.")

    if values.size < 2:
        raise ValueError("At least two equity observations are required.")

    if not np.all(np.isfinite(values)):
        raise ValueError("Equity observations must be finite.")

    if np.any(values <= 0):
        raise ValueError(
            "Equity observations must be strictly positive. "
            "Bankrupt or nonpositive paths require separate handling."
        )

    return values


def simple_returns(
    equity: Sequence[float],
) -> NDArray[np.float64]:
    """Convert an equity sequence to simple period returns."""
    values = validate_equity(equity)

    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        returns = values[1:] / values[:-1] - 1.0

    if not np.all(np.isfinite(returns)):
        raise ValueError("Equity ratios produced nonfinite returns.")

    return returns


def maximum_drawdown(equity: Sequence[float]) -> float:
    """Return the largest peak-to-trough loss as a positive fraction."""
    values = validate_equity(equity)
    running_peak = np.maximum.accumulate(values)

    drawdown = 1.0 - values / running_peak

    return float(np.max(drawdown))


def _finite_or_none(value: float) -> float | None:
    """Represent undefined or overflowing metrics as None."""
    return value if math.isfinite(value) else None


def summarize_equity(
    equity: Sequence[float],
    *,
    periods_per_year: int,
    annual_risk_free_rate: float = 0.0,
) -> MetricsSummary:
    """Compute summary metrics using a caller-specified observation frequency.

    Parameters
    ----------
    equity : Sequence[float]
        Positive equity observations, including starting equity.
    periods_per_year : int
        Number of return observations in one year.
    annual_risk_free_rate : float
        Effective annual risk-free rate, expressed as a fraction.

    Notes
    -----
    Observations must use a consistent frequency and valuation convention.
    The function cannot infer trading calendars from an equity array.

    Sortino uses the root mean square of negative excess returns across all
    observations, not the standard deviation of negative returns alone.
    """
    if (
        isinstance(periods_per_year, bool)
        or not isinstance(periods_per_year, int)
        or periods_per_year <= 0
    ):
        raise ValueError("periods_per_year must be a positive integer.")

    if not math.isfinite(annual_risk_free_rate) or annual_risk_free_rate <= -1:
        raise ValueError("annual_risk_free_rate must be finite and greater than -1.")

    values = validate_equity(equity)
    returns = simple_returns(equity)
    return_count = int(returns.size)

    periodic_risk_free = math.expm1(
        math.log1p(annual_risk_free_rate) / periods_per_year
    )

    excess = returns - periodic_risk_free
    mean_excess = float(np.mean(excess))
    annual_scale = math.sqrt(periods_per_year)

    volatility: float | None = None
    sharpe: float | None = None

    if return_count >= 2:
        sample_std = float(np.std(returns, ddof=1))
        excess_std = float(np.std(excess, ddof=1))

        volatility = _finite_or_none(sample_std * annual_scale)

        if math.isfinite(excess_std) and excess_std > 0:
            sharpe = _finite_or_none(mean_excess / excess_std * annual_scale)

    downside = np.minimum(excess, 0.0)

    with np.errstate(over="ignore", invalid="ignore"):
        downside_deviation = float(np.sqrt(np.mean(np.square(downside))))

    sortino: float | None = None

    if math.isfinite(downside_deviation) and downside_deviation > 0:
        sortino = _finite_or_none(mean_excess / downside_deviation * annual_scale)

    log_growth = math.log(float(values[-1])) - math.log(float(values[0]))

    try:
        annualized_return = _finite_or_none(
            math.expm1(log_growth * periods_per_year / return_count)
        )
    except OverflowError:
        annualized_return = None

    total_return = float(values[-1] / values[0] - 1.0)

    if not math.isfinite(total_return):
        raise ValueError("Total return is not finite.")

    drawdown = maximum_drawdown(equity)

    calmar: float | None = None

    if annualized_return is not None and drawdown > 0:
        calmar = _finite_or_none(annualized_return / drawdown)

    return MetricsSummary(
        observation_count=int(values.size),
        return_count=return_count,
        periods_per_year=periods_per_year,
        total_return=total_return,
        annualized_return=annualized_return,
        annualized_volatility=volatility,
        sharpe=sharpe,
        sortino=sortino,
        calmar=calmar,
        max_drawdown=drawdown,
    )
