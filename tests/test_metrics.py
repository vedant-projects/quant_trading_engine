"""Numerical and report-export tests."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.backtest.metrics import (
    maximum_drawdown,
    simple_returns,
    summarize_equity,
)
from app.backtest.report import (
    build_report,
    write_equity_csv,
    write_report_json,
)
from app.schemas.backtest import EquityPoint


def test_simple_returns() -> None:
    """Simple returns use consecutive equity ratios."""
    result = simple_returns([100.0, 110.0, 99.0])

    np.testing.assert_allclose(
        result,
        [0.10, -0.10],
        atol=1e-12,
    )


def test_maximum_drawdown() -> None:
    """A fall from 120 to 90 is a 25 percent drawdown."""
    result = maximum_drawdown([100.0, 120.0, 90.0, 110.0])

    assert result == pytest.approx(0.25)


def test_monotonic_equity_has_zero_drawdown() -> None:
    """A nondecreasing path has no peak-to-trough loss."""
    assert maximum_drawdown([100.0, 101.0, 110.0]) == 0.0


def test_flat_equity_has_undefined_risk_ratios() -> None:
    """Zero dispersion does not produce an infinite Sharpe ratio."""
    metrics = summarize_equity(
        [100.0, 100.0, 100.0],
        periods_per_year=252,
    )

    assert metrics.total_return == 0.0
    assert metrics.max_drawdown == 0.0
    assert metrics.sharpe is None
    assert metrics.sortino is None
    assert metrics.calmar is None


def test_one_return_has_no_sample_volatility() -> None:
    """One return is insufficient for sample standard deviation."""
    metrics = summarize_equity(
        [100.0, 110.0],
        periods_per_year=1,
    )

    assert metrics.return_count == 1
    assert metrics.annualized_volatility is None
    assert metrics.sharpe is None
    assert metrics.total_return == pytest.approx(0.10)


def test_annualized_growth_uses_return_count() -> None:
    """Two observations contain one return period."""
    metrics = summarize_equity(
        [100.0, 110.0],
        periods_per_year=1,
    )

    assert metrics.annualized_return == pytest.approx(0.10)


def test_sharpe_matches_manual_formula() -> None:
    """Sharpe uses sample deviation and square-root annualization."""
    equity = [100.0, 110.0, 99.0, 108.9]
    returns = np.array([0.1, -0.1, 0.1])

    expected = float(np.mean(returns)) / float(np.std(returns, ddof=1)) * np.sqrt(252)

    metrics = summarize_equity(
        equity,
        periods_per_year=252,
    )

    assert metrics.sharpe == pytest.approx(expected)


@pytest.mark.parametrize(
    "equity",
    [
        [],
        [100.0],
        [100.0, 0.0],
        [100.0, -1.0],
        [100.0, float("nan")],
        [100.0, float("inf")],
    ],
)
def test_invalid_equity_is_rejected(equity: list[float]) -> None:
    """Insufficient, nonfinite, and nonpositive paths are invalid."""
    with pytest.raises(ValueError):
        summarize_equity(
            equity,
            periods_per_year=252,
        )


@pytest.mark.parametrize("frequency", [0, -1, True])
def test_invalid_frequency_is_rejected(frequency: int) -> None:
    """Annualization requires a positive integer frequency."""
    with pytest.raises(ValueError):
        summarize_equity(
            [100.0, 110.0],
            periods_per_year=frequency,
        )


@given(
    st.lists(
        st.floats(
            min_value=1.0,
            max_value=1_000_000.0,
            allow_nan=False,
            allow_infinity=False,
        ),
        min_size=2,
        max_size=100,
    )
)
def test_drawdown_is_bounded(equity: list[float]) -> None:
    """Positive finite equity paths have drawdown between zero and one."""
    drawdown = maximum_drawdown(equity)

    assert 0.0 <= drawdown <= 1.0


def make_curve() -> list[EquityPoint]:
    """Construct three chronological daily observations."""
    start = datetime(2026, 1, 1, tzinfo=UTC)

    return [
        EquityPoint(timestamp=start, equity=100.0),
        EquityPoint(
            timestamp=start + timedelta(days=1),
            equity=110.0,
        ),
        EquityPoint(
            timestamp=start + timedelta(days=2),
            equity=105.0,
        ),
    ]


def test_report_exports_json_and_csv(tmp_path: Path) -> None:
    """Reports can be written as parseable JSON and CSV."""
    report = build_report(
        strategy_id="test-strategy",
        symbol="TEST",
        currency="USD",
        equity_curve=make_curve(),
        periods_per_year=252,
    )

    json_path = write_report_json(
        report,
        tmp_path / "report.json",
    )
    csv_path = write_equity_csv(
        report,
        tmp_path / "equity.csv",
    )

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    csv_lines = csv_path.read_text(encoding="utf-8").splitlines()

    assert payload["strategy_id"] == "test-strategy"
    assert payload["metrics"]["observation_count"] == 3
    assert csv_lines[0] == "timestamp,equity"
    assert len(csv_lines) == 4


def test_report_rejects_nonchronological_curve() -> None:
    """Report construction cannot silently reorder observations."""
    curve = make_curve()

    with pytest.raises(ValueError, match="strictly increasing"):
        build_report(
            strategy_id="test-strategy",
            symbol="TEST",
            currency="USD",
            equity_curve=list(reversed(curve)),
            periods_per_year=252,
        )
