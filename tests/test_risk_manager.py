"""Risk-gate and circuit-breaker tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.core.portfolio_manager import PortfolioManager
from app.core.risk_manager import RiskManager
from app.strategies.base import Fill
from app.utils.exceptions import CircuitBreakerTripped, RiskRejected


def make_account() -> tuple[PortfolioManager, RiskManager, datetime]:
    """Create a deterministic simulated account."""
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)

    portfolio = PortfolioManager(
        strategy_id="test",
        symbol="TEST",
        initial_cash=Decimal("1000"),
        started_at=timestamp,
    )
    portfolio.mark(Decimal("100"))

    risk = RiskManager(
        portfolio,
        max_daily_loss_pct=Decimal("2"),
        max_position_pct=Decimal("10"),
    )
    risk.observe(timestamp)

    return portfolio, risk, timestamp


def test_position_cap_rejects_large_buy() -> None:
    """A proposed 20 percent position exceeds a 10 percent cap."""
    _, risk, timestamp = make_account()

    with pytest.raises(RiskRejected, match="cap"):
        risk.check_order(
            quantity=Decimal("2"),
            price=Decimal("100"),
            commission=Decimal("0"),
            timestamp=timestamp,
        )


def test_cash_limit_rejects_unaffordable_order() -> None:
    """An order cannot create negative cash."""
    _, risk, timestamp = make_account()

    with pytest.raises(RiskRejected, match="cash"):
        risk.check_order(
            quantity=Decimal("20"),
            price=Decimal("100"),
            commission=Decimal("0"),
            timestamp=timestamp,
        )


def test_daily_breaker_latches_across_rollover() -> None:
    """A date change does not automatically resume trading."""
    portfolio, risk, timestamp = make_account()

    portfolio.apply_fill(
        Fill(
            strategy_id="test",
            symbol="TEST",
            order_id="order",
            fill_id="fill",
            timestamp=timestamp,
            quantity=Decimal("1"),
            price=Decimal("100"),
        )
    )

    portfolio.mark(Decimal("70"))
    risk.observe(timestamp + timedelta(hours=1))

    assert risk.tripped is True

    next_day = timestamp + timedelta(days=1)
    risk.observe(next_day)

    with pytest.raises(CircuitBreakerTripped):
        risk.check_order(
            quantity=Decimal("-1"),
            price=Decimal("70"),
            commission=Decimal("0"),
            timestamp=next_day,
        )

    risk.manual_reset(next_day, acknowledge=True)

    assert risk.tripped is False


def test_short_order_is_rejected() -> None:
    """A flat account cannot sell into a short position."""
    _, risk, timestamp = make_account()

    with pytest.raises(RiskRejected, match="Short"):
        risk.check_order(
            quantity=Decimal("-1"),
            price=Decimal("100"),
            commission=Decimal("0"),
            timestamp=timestamp,
        )
