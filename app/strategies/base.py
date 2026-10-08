"""Shared strategy contracts and internal trading-domain objects.

Strategies consume completed market bars and emit desired-position signals.
They do not submit broker orders.

Execution, risk checks, and authoritative position accounting belong to
separate components.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from types import MappingProxyType
from uuid import UUID, uuid4

ZERO = Decimal("0")


def _validate_text(value: str, name: str) -> None:
    """Require a nonempty string without surrounding whitespace."""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")

    if not value or value != value.strip():
        raise ValueError(f"{name} must be nonempty and have no surrounding whitespace.")


def _validate_decimal(value: Decimal, name: str) -> None:
    """Require a finite Decimal rather than silently converting floats."""
    if not isinstance(value, Decimal):
        raise TypeError(
            f"{name} must be a Decimal. "
            'Construct it from a string, for example Decimal("100.25").'
        )

    if not value.is_finite():
        raise ValueError(f"{name} must be finite.")


def _validate_timestamp(value: datetime, name: str) -> None:
    """Require a timezone-aware datetime."""
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime.")

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware.")


@dataclass(frozen=True, slots=True, kw_only=True)
class DataRequirement:
    """Describe one market-data stream required by a strategy.

    Parameters
    ----------
    symbol : str
        Provider-specific instrument identifier.
    timeframe : str
        Bar interval, such as "1m", "5m", or "1d".
    warmup_bars : int
        Number of completed historical bars required before live processing.
    """

    symbol: str
    timeframe: str
    warmup_bars: int

    def __post_init__(self) -> None:
        """Validate the requested stream and warmup length."""
        _validate_text(self.symbol, "symbol")
        _validate_text(self.timeframe, "timeframe")

        if isinstance(self.warmup_bars, bool) or not isinstance(self.warmup_bars, int):
            raise TypeError("warmup_bars must be an integer.")

        if self.warmup_bars < 0:
            raise ValueError("warmup_bars cannot be negative.")


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketBar:
    """Represent a completed OHLCV bar.

    Notes
    -----
    `timestamp` is the bar's closing time, not its opening time.
    The data router must not deliver this bar before it has completed.
    Volume represents the provider's reported volume units.
    """

    symbol: str
    timeframe: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    def __post_init__(self) -> None:
        """Validate prices, volume, and the bar timestamp."""
        _validate_text(self.symbol, "symbol")
        _validate_text(self.timeframe, "timeframe")
        _validate_timestamp(self.timestamp, "timestamp")

        for name in ("open", "high", "low", "close", "volume"):
            _validate_decimal(getattr(self, name), name)

        if min(self.open, self.high, self.low, self.close) <= ZERO:
            raise ValueError("OHLC prices must be strictly positive.")

        if self.volume < ZERO:
            raise ValueError("volume cannot be negative.")

        if self.low > self.high:
            raise ValueError("low cannot exceed high.")

        if not self.low <= self.open <= self.high:
            raise ValueError("open must lie between low and high.")

        if not self.low <= self.close <= self.high:
            raise ValueError("close must lie between low and high.")


@dataclass(frozen=True, slots=True, kw_only=True)
class Signal:
    """Express a desired signed position for one strategy and instrument.

    Parameters
    ----------
    strategy_id : str
        Identifier of the strategy instance producing the signal.
    symbol : str
        Instrument to which the signal applies.
    timestamp : datetime
        Decision time. Must not precede the data used for the decision.
    target_quantity : Decimal
        Desired total strategy position, not an incremental order quantity.
        Positive means long, negative means short, and zero means flat.
    reason : str
        Human-readable explanation of the decision.
    signal_id : UUID
        Unique identifier for logging, persistence, and execution tracking.

    Notes
    -----
    A signal is a proposal, not permission to trade.
    Risk and execution components must independently validate it.
    """

    strategy_id: str
    symbol: str
    timestamp: datetime
    target_quantity: Decimal
    reason: str
    signal_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        """Validate the desired-position signal."""
        _validate_text(self.strategy_id, "strategy_id")
        _validate_text(self.symbol, "symbol")
        _validate_text(self.reason, "reason")
        _validate_timestamp(self.timestamp, "timestamp")
        _validate_decimal(self.target_quantity, "target_quantity")

        if not isinstance(self.signal_id, UUID):
            raise TypeError("signal_id must be a UUID.")


@dataclass(frozen=True, slots=True, kw_only=True)
class Position:
    """Represent an authoritative strategy-level position snapshot.

    Notes
    -----
    Quantity is signed: positive for long, negative for short.
    A flat position has quantity zero and average_price zero.
    Average price excludes fees; fee accounting belongs to the portfolio.
    """

    strategy_id: str
    symbol: str
    quantity: Decimal
    average_price: Decimal
    updated_at: datetime

    def __post_init__(self) -> None:
        """Validate quantity, cost basis, and update time."""
        _validate_text(self.strategy_id, "strategy_id")
        _validate_text(self.symbol, "symbol")
        _validate_timestamp(self.updated_at, "updated_at")
        _validate_decimal(self.quantity, "quantity")
        _validate_decimal(self.average_price, "average_price")

        if self.quantity == ZERO:
            if self.average_price != ZERO:
                raise ValueError(
                    "A flat position must have average_price equal to zero."
                )
        elif self.average_price <= ZERO:
            raise ValueError("A nonzero position must have a positive average_price.")


@dataclass(frozen=True, slots=True, kw_only=True)
class Fill:
    """Represent one execution, including a possible partial fill.

    Notes
    -----
    Quantity is signed: positive for a buy, negative for a sell.
    Commission is expressed in the instrument's quote currency.
    Negative commission is permitted to represent a fee rebate.
    """

    strategy_id: str
    symbol: str
    order_id: str
    fill_id: str
    timestamp: datetime
    quantity: Decimal
    price: Decimal
    commission: Decimal = ZERO

    def __post_init__(self) -> None:
        """Validate identifiers and execution amounts."""
        for name in ("strategy_id", "symbol", "order_id", "fill_id"):
            _validate_text(getattr(self, name), name)

        _validate_timestamp(self.timestamp, "timestamp")

        for name in ("quantity", "price", "commission"):
            _validate_decimal(getattr(self, name), name)

        if self.quantity == ZERO:
            raise ValueError("A fill must have a nonzero quantity.")

        if self.price <= ZERO:
            raise ValueError("A fill must have a positive price.")


class BaseStrategy(ABC):
    """Define the interface implemented by every trading strategy.

    Parameters
    ----------
    strategy_id : str
        Unique identifier for this strategy instance.
    parameters : Mapping[str, object] or None
        Strategy-specific configuration. The top-level mapping is read-only.

    Notes
    -----
    The engine must validate parameters before requesting data or initializing
    a strategy.

    Callbacks must run sequentially for each strategy instance. This class
    does not provide locking or make mutable strategy state thread-safe.

    Strategies receive data and execution notifications but must not receive
    broker credentials or submit broker orders.
    """

    def __init__(
        self,
        *,
        strategy_id: str,
        parameters: Mapping[str, object] | None = None,
    ) -> None:
        """Store the strategy identity and a configuration snapshot."""
        _validate_text(strategy_id, "strategy_id")

        self._strategy_id = strategy_id
        self._parameters: Mapping[str, object] = MappingProxyType(
            dict(parameters) if parameters is not None else {}
        )

    @property
    def strategy_id(self) -> str:
        """Return the strategy instance identifier."""
        return self._strategy_id

    @property
    def parameters(self) -> Mapping[str, object]:
        """Return the top-level read-only parameter mapping."""
        return self._parameters

    @abstractmethod
    def validate_parameters(self) -> None:
        """Raise TypeError or ValueError when parameters are invalid."""
        raise NotImplementedError

    @abstractmethod
    def get_required_data(self) -> tuple[DataRequirement, ...]:
        """Return the streams and historical warmup lengths required."""
        raise NotImplementedError

    @abstractmethod
    async def initialize(self, history: Sequence[MarketBar]) -> None:
        """Initialize indicators from completed bars without emitting signals.

        Notes
        -----
        History must be chronological, oldest first, and contain only the
        requested streams. Warmup data must precede subsequent on_data calls.
        """
        raise NotImplementedError

    @abstractmethod
    async def on_data(self, bar: MarketBar) -> tuple[Signal, ...]:
        """Consume one completed bar and return zero or more signals.

        Notes
        -----
        Return an empty tuple when no position change is proposed.
        Returned signals must identify this strategy instance.
        """
        raise NotImplementedError

    @abstractmethod
    async def on_fill(self, fill: Fill, position: Position) -> None:
        """Observe an execution and its updated authoritative position.

        Notes
        -----
        Execution accounting must deduplicate fills and update the position
        before invoking this callback.
        """
        raise NotImplementedError

    @abstractmethod
    def get_position_size(
        self,
        *,
        equity: Decimal,
        entry_price: Decimal,
        stop_price: Decimal,
    ) -> Decimal:
        """Propose a nonnegative position magnitude in instrument units.

        Notes
        -----
        The strategy chooses direction separately when constructing a signal.
        Risk checks, affordability checks, and lot-size rounding remain the
        responsibility of risk and execution components.

        This initial interface targets unleveraged spot/equity instruments.
        Derivatives require additional contract and margin specifications.
        """
        raise NotImplementedError
