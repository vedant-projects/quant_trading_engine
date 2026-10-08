"""Tests for API response validation."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.backtest import EquityPoint
from app.schemas.order import OrderRead
from app.schemas.signal import SignalRead
from app.schemas.trade import TradeRead


@pytest.fixture
def timestamp() -> datetime:
    """Return a deterministic timezone-aware timestamp."""
    return datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def order_data(timestamp: datetime) -> dict[str, object]:
    """Return a complete valid market-order response payload."""
    return {
        "id": uuid4(),
        "strategy_id": "test-strategy",
        "account_id": "paper-account",
        "client_order_id": "client-001",
        "broker_order_id": None,
        "symbol": "TEST",
        "side": "buy",
        "order_type": "market",
        "quantity": Decimal("10"),
        "filled_quantity": Decimal("0"),
        "limit_price": None,
        "status": "new",
        "is_paper": True,
        "risk_reason": None,
        "signal_id": None,
        "created_at": timestamp,
    }


@pytest.fixture
def trade_data(timestamp: datetime) -> dict[str, object]:
    """Return a complete valid execution response payload."""
    return {
        "id": uuid4(),
        "timestamp": timestamp,
        "order_id": uuid4(),
        "strategy_id": "test-strategy",
        "account_id": "paper-account",
        "broker_fill_id": "fill-001",
        "symbol": "TEST",
        "quote_currency": "USD",
        "quantity": Decimal("2"),
        "price": Decimal("100"),
        "commission": Decimal("0.1"),
        "is_paper": True,
    }


def test_order_schema_accepts_valid_market_order(
    order_data: dict[str, object],
) -> None:
    """A market order does not require a limit price."""
    order = OrderRead.model_validate(order_data)

    assert order.quantity == Decimal("10")
    assert order.limit_price is None


def test_order_schema_rejects_live_record(
    order_data: dict[str, object],
) -> None:
    """The current API schema rejects live-order records."""
    order_data["is_paper"] = False

    with pytest.raises(ValidationError):
        OrderRead.model_validate(order_data)


def test_limit_order_requires_price(
    order_data: dict[str, object],
) -> None:
    """Limit orders cannot omit their price."""
    order_data["order_type"] = "limit"

    with pytest.raises(ValidationError, match="limit_price"):
        OrderRead.model_validate(order_data)


def test_market_order_rejects_limit_price(
    order_data: dict[str, object],
) -> None:
    """Market orders cannot carry a limit price."""
    order_data["limit_price"] = Decimal("100")

    with pytest.raises(ValidationError, match="limit_price"):
        OrderRead.model_validate(order_data)


def test_order_rejects_overfill(
    order_data: dict[str, object],
) -> None:
    """Recorded filled quantity cannot exceed order quantity."""
    order_data["filled_quantity"] = Decimal("11")

    with pytest.raises(ValidationError, match="filled_quantity"):
        OrderRead.model_validate(order_data)


def test_trade_schema_accepts_signed_sell(
    trade_data: dict[str, object],
) -> None:
    """A negative execution quantity represents a sell."""
    trade_data["quantity"] = Decimal("-2")

    trade = TradeRead.model_validate(trade_data)

    assert trade.quantity == Decimal("-2")


@pytest.mark.parametrize(
    "quantity",
    [
        Decimal("0"),
        Decimal("NaN"),
        Decimal("Infinity"),
    ],
)
def test_trade_schema_rejects_invalid_quantity(
    trade_data: dict[str, object],
    quantity: Decimal,
) -> None:
    """Zero and nonfinite execution quantities are invalid."""
    trade_data["quantity"] = quantity

    with pytest.raises(ValidationError):
        TradeRead.model_validate(trade_data)


def test_trade_schema_rejects_naive_timestamp(
    trade_data: dict[str, object],
) -> None:
    """Execution timestamps must contain timezone information."""
    trade_data["timestamp"] = datetime(2026, 1, 1)

    with pytest.raises(ValidationError):
        TradeRead.model_validate(trade_data)


def test_signal_schema_accepts_flat_target(
    timestamp: datetime,
) -> None:
    """A zero target proposes closing the strategy's position."""
    signal = SignalRead(
        id=uuid4(),
        timestamp=timestamp,
        strategy_id="test-strategy",
        symbol="TEST",
        target_quantity=Decimal("0"),
        reason="Exit",
    )

    assert signal.target_quantity == Decimal("0")


def test_response_schema_rejects_extra_fields(
    trade_data: dict[str, object],
) -> None:
    """Unexpected dictionary fields are not silently accepted."""
    trade_data["unexpected"] = "value"

    with pytest.raises(ValidationError):
        TradeRead.model_validate(trade_data)


@pytest.mark.parametrize(
    "equity",
    [0.0, -1.0, float("nan"), float("inf")],
)
def test_equity_point_requires_positive_finite_equity(
    timestamp: datetime,
    equity: float,
) -> None:
    """The initial reporting implementation supports positive paths."""
    with pytest.raises(ValidationError):
        EquityPoint(
            timestamp=timestamp,
            equity=equity,
        )
