"""Unit tests for strategy contracts and internal domain objects."""

from collections.abc import Sequence
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.strategies.base import (
    BaseStrategy,
    DataRequirement,
    Fill,
    MarketBar,
    Position,
    Signal,
)


@pytest.fixture
def timestamp() -> datetime:
    """Return a deterministic timezone-aware timestamp."""
    return datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def bar(timestamp: datetime) -> MarketBar:
    """Return a valid completed market bar."""
    return MarketBar(
        symbol="TEST",
        timeframe="1m",
        timestamp=timestamp,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal("101"),
        volume=Decimal("1000"),
    )


@pytest.fixture
def position(timestamp: datetime) -> Position:
    """Return a valid long-position snapshot."""
    return Position(
        strategy_id="test-strategy",
        symbol="TEST",
        quantity=Decimal("4"),
        average_price=Decimal("100"),
        updated_at=timestamp,
    )


@pytest.fixture
def signal(timestamp: datetime) -> Signal:
    """Return a valid desired-position signal."""
    return Signal(
        strategy_id="test-strategy",
        symbol="TEST",
        timestamp=timestamp,
        target_quantity=Decimal("10"),
        reason="Test target",
    )


@pytest.fixture
def fill(timestamp: datetime) -> Fill:
    """Return a valid execution record."""
    return Fill(
        strategy_id="test-strategy",
        symbol="TEST",
        order_id="order-001",
        fill_id="fill-001",
        timestamp=timestamp,
        quantity=Decimal("2"),
        price=Decimal("101"),
        commission=Decimal("0.10"),
    )


class ExampleStrategy(BaseStrategy):
    """Provide a minimal concrete strategy for contract tests."""

    def __init__(self) -> None:
        """Initialize observable test state."""
        super().__init__(
            strategy_id="test-strategy",
            parameters={"window": 5},
        )
        self.initialized = False
        self.last_position: Position | None = None

    def validate_parameters(self) -> None:
        """Validate the example's integer lookback window."""
        window = self.parameters.get("window")

        if isinstance(window, bool) or not isinstance(window, int):
            raise TypeError("window must be an integer.")

        if window <= 0:
            raise ValueError("window must be positive.")

    def get_required_data(self) -> tuple[DataRequirement, ...]:
        """Request one stream for the example."""
        return (
            DataRequirement(
                symbol="TEST",
                timeframe="1m",
                warmup_bars=5,
            ),
        )

    async def initialize(self, history: Sequence[MarketBar]) -> None:
        """Record that the initialization callback ran."""
        self.initialized = True

    async def on_data(self, bar: MarketBar) -> tuple[Signal, ...]:
        """Return no signals for this test-only strategy."""
        return ()

    async def on_fill(self, fill: Fill, position: Position) -> None:
        """Record the authoritative position delivered by the engine."""
        self.last_position = position

    def get_position_size(
        self,
        *,
        equity: Decimal,
        entry_price: Decimal,
        stop_price: Decimal,
    ) -> Decimal:
        """Return a fixed test quantity, not a production sizing rule."""
        return Decimal("1")


def test_base_strategy_cannot_be_instantiated() -> None:
    """Incomplete strategies cannot be instantiated."""
    with pytest.raises(TypeError):
        BaseStrategy(strategy_id="incomplete")


def test_data_requirement_accepts_zero_warmup() -> None:
    """Strategies may explicitly request no historical warmup."""
    requirement = DataRequirement(
        symbol="TEST",
        timeframe="1m",
        warmup_bars=0,
    )

    assert requirement.warmup_bars == 0


def test_data_requirement_rejects_negative_warmup() -> None:
    """Negative historical requirements are invalid."""
    with pytest.raises(ValueError):
        DataRequirement(
            symbol="TEST",
            timeframe="1m",
            warmup_bars=-1,
        )


def test_data_requirement_rejects_boolean_warmup() -> None:
    """A boolean is not a valid lookback length."""
    with pytest.raises(TypeError):
        DataRequirement(
            symbol="TEST",
            timeframe="1m",
            warmup_bars=True,
        )


def test_market_bar_accepts_valid_prices(bar: MarketBar) -> None:
    """A valid completed bar preserves its values."""
    assert bar.close == Decimal("101")
    assert bar.volume == Decimal("1000")


@pytest.mark.parametrize(
    "value",
    [
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
    ],
)
def test_market_bar_rejects_invalid_close(
    bar: MarketBar,
    value: Decimal,
) -> None:
    """Prices must be finite and strictly positive."""
    with pytest.raises(ValueError):
        replace(bar, close=value)


def test_market_bar_rejects_float_price(bar: MarketBar) -> None:
    """Financial fields require explicit Decimal construction."""
    with pytest.raises(TypeError):
        replace(bar, close=101.0)


def test_market_bar_rejects_naive_timestamp(bar: MarketBar) -> None:
    """A timestamp without timezone information is invalid."""
    with pytest.raises(ValueError):
        replace(
            bar,
            timestamp=datetime(2026, 1, 1, 12, 0),
        )


def test_market_bar_rejects_negative_volume(bar: MarketBar) -> None:
    """Volume cannot be negative."""
    with pytest.raises(ValueError):
        replace(bar, volume=Decimal("-1"))


def test_market_bar_rejects_close_above_high(bar: MarketBar) -> None:
    """Close must lie inside the high-low range."""
    with pytest.raises(ValueError):
        replace(bar, close=Decimal("103"))


def test_market_bar_rejects_low_above_high(bar: MarketBar) -> None:
    """The high-low interval must be ordered correctly."""
    with pytest.raises(ValueError):
        replace(bar, low=Decimal("103"))


def test_signal_quantity_is_a_target(
    signal: Signal,
    position: Position,
) -> None:
    """A target of ten with four held implies a six-unit difference."""
    difference = signal.target_quantity - position.quantity

    assert difference == Decimal("6")


@pytest.mark.parametrize(
    "quantity",
    [
        Decimal("10"),
        Decimal("-10"),
        Decimal("0"),
    ],
)
def test_signal_accepts_signed_targets(
    signal: Signal,
    quantity: Decimal,
) -> None:
    """Long, short, and flat targets are all valid proposals."""
    updated = replace(signal, target_quantity=quantity)

    assert updated.target_quantity == quantity


def test_signal_ids_are_unique(signal: Signal) -> None:
    """Separate signals receive separate generated identifiers."""
    another = Signal(
        strategy_id=signal.strategy_id,
        symbol=signal.symbol,
        timestamp=signal.timestamp,
        target_quantity=signal.target_quantity,
        reason=signal.reason,
    )

    assert another.signal_id != signal.signal_id


def test_signal_rejects_blank_reason(signal: Signal) -> None:
    """Signals must carry a nonempty explanation."""
    with pytest.raises(ValueError):
        replace(signal, reason="")


def test_domain_object_fields_are_frozen(signal: Signal) -> None:
    """Ordinary field reassignment is blocked."""
    with pytest.raises(FrozenInstanceError):
        signal.reason = "Changed"


def test_flat_position_requires_zero_average(position: Position) -> None:
    """A flat position cannot retain a nonzero average price."""
    with pytest.raises(ValueError):
        replace(position, quantity=Decimal("0"))


def test_valid_flat_position(position: Position) -> None:
    """Zero quantity and zero average price represent a flat position."""
    flat = replace(
        position,
        quantity=Decimal("0"),
        average_price=Decimal("0"),
    )

    assert flat.quantity == Decimal("0")


def test_short_position_accepts_positive_average(position: Position) -> None:
    """Short holdings retain a positive average execution price."""
    short = replace(position, quantity=Decimal("-4"))

    assert short.quantity < Decimal("0")
    assert short.average_price == Decimal("100")


def test_fill_rejects_zero_quantity(fill: Fill) -> None:
    """A zero-quantity event cannot represent an execution."""
    with pytest.raises(ValueError):
        replace(fill, quantity=Decimal("0"))


def test_fill_accepts_sell_quantity(fill: Fill) -> None:
    """Negative fill quantity represents a sell."""
    sale = replace(fill, quantity=Decimal("-2"))

    assert sale.quantity == Decimal("-2")


def test_fill_accepts_fee_rebate(fill: Fill) -> None:
    """Negative commission represents a rebate."""
    rebate = replace(fill, commission=Decimal("-0.01"))

    assert rebate.commission < Decimal("0")


def test_strategy_parameters_are_top_level_read_only() -> None:
    """Top-level strategy settings cannot be reassigned."""
    strategy = ExampleStrategy()

    with pytest.raises(TypeError):
        strategy.parameters["window"] = 10


@pytest.mark.asyncio
async def test_concrete_strategy_lifecycle(
    bar: MarketBar,
    fill: Fill,
    position: Position,
) -> None:
    """A concrete strategy supports the required callbacks."""
    strategy = ExampleStrategy()

    strategy.validate_parameters()
    requirements = strategy.get_required_data()

    await strategy.initialize([bar])
    signals = await strategy.on_data(bar)
    await strategy.on_fill(fill, position)

    assert strategy.strategy_id == "test-strategy"
    assert requirements[0].warmup_bars == 5
    assert strategy.initialized is True
    assert signals == ()
    assert strategy.last_position == position

    assert strategy.get_position_size(
        equity=Decimal("10000"),
        entry_price=Decimal("100"),
        stop_price=Decimal("95"),
    ) == Decimal("1")
