"""Local simulator tests."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.brokers.base import PaperOrder
from app.brokers.paper import PaperBroker
from app.core.portfolio_manager import PortfolioManager
from app.core.risk_manager import RiskManager
from app.utils.exceptions import RiskRejected


@pytest.mark.asyncio
async def test_repeated_order_is_not_applied_twice() -> None:
    """Identical client-order submissions return one applied fill."""
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)

    portfolio = PortfolioManager(
        strategy_id="test",
        symbol="TEST",
        initial_cash=Decimal("10000"),
        started_at=timestamp,
    )
    portfolio.mark(Decimal("100"))

    risk = RiskManager(
        portfolio,
        max_daily_loss_pct=Decimal("2"),
        max_position_pct=Decimal("10"),
    )

    broker = PaperBroker(
        risk,
        fee_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
    )
    await broker.connect()

    order = PaperOrder(
        strategy_id="test",
        symbol="TEST",
        quantity=Decimal("1"),
        reference_price=Decimal("100"),
        timestamp=timestamp,
        client_order_id="client-1",
    )

    first = await broker.place_order(order)
    second = await broker.place_order(order)

    assert first == second
    assert portfolio.quantity == Decimal("1")
    assert portfolio.cash == Decimal("9900")


@pytest.mark.asyncio
async def test_public_broker_method_cannot_skip_risk_gate() -> None:
    """An oversized order is rejected before holdings change."""
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)

    portfolio = PortfolioManager(
        strategy_id="test",
        symbol="TEST",
        initial_cash=Decimal("1000"),
        started_at=timestamp,
    )

    risk = RiskManager(
        portfolio,
        max_daily_loss_pct=Decimal("2"),
        max_position_pct=Decimal("10"),
    )

    broker = PaperBroker(risk)
    await broker.connect()

    with pytest.raises(RiskRejected):
        await broker.place_order(
            PaperOrder(
                strategy_id="test",
                symbol="TEST",
                quantity=Decimal("5"),
                reference_price=Decimal("100"),
                timestamp=timestamp,
                client_order_id="oversized",
            )
        )

    assert portfolio.quantity == Decimal("0")
    assert portfolio.cash == Decimal("1000")
