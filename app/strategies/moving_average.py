"""Long/flat simple-moving-average strategy for pipeline validation."""

from collections import deque
from collections.abc import Mapping, Sequence
from decimal import Decimal

from app.data.timeframes import timeframe_duration
from app.strategies.base import (
    BaseStrategy,
    DataRequirement,
    Fill,
    MarketBar,
    Position,
    Signal,
)
from app.strategies.parameters import (
    decimal_parameter,
    integer_parameter,
    reject_unknown_parameters,
    text_parameter,
)


class MovingAverageStrategy(BaseStrategy):
    """Target a fixed long quantity when the fast average exceeds the slow."""

    def __init__(
        self,
        *,
        strategy_id: str,
        parameters: Mapping[str, object] | None = None,
    ) -> None:
        """Validate configuration and allocate indicator state."""
        super().__init__(
            strategy_id=strategy_id,
            parameters=parameters,
        )
        self.validate_parameters()

        self._prices: deque[Decimal] = deque(maxlen=self.slow_window)
        self._initialized = False

    def validate_parameters(self) -> None:
        """Validate the supported configuration."""
        reject_unknown_parameters(
            self.parameters,
            {
                "symbol",
                "timeframe",
                "fast_window",
                "slow_window",
                "quantity",
            },
        )

        self.symbol = text_parameter(self.parameters, "symbol", "TEST")
        self.timeframe = text_parameter(self.parameters, "timeframe", "1h")
        self.fast_window = integer_parameter(self.parameters, "fast_window", 5)
        self.slow_window = integer_parameter(self.parameters, "slow_window", 20)
        self.quantity = decimal_parameter(self.parameters, "quantity", "1")

        timeframe_duration(self.timeframe)

        if self.fast_window >= self.slow_window:
            raise ValueError("fast_window must be smaller than slow_window.")

    def get_required_data(self) -> tuple[DataRequirement, ...]:
        """Declare the single stream and slow-window warmup."""
        return (
            DataRequirement(
                symbol=self.symbol,
                timeframe=self.timeframe,
                warmup_bars=self.slow_window,
            ),
        )

    async def initialize(self, history: Sequence[MarketBar]) -> None:
        """Load the indicator without generating warmup signals."""
        matching = [
            bar
            for bar in history
            if bar.symbol == self.symbol and bar.timeframe == self.timeframe
        ]

        if len(matching) < self.slow_window:
            raise ValueError("Insufficient moving-average warmup.")

        self._prices.clear()
        self._prices.extend(bar.close for bar in matching[-self.slow_window :])
        self._initialized = True

    async def on_data(self, bar: MarketBar) -> tuple[Signal, ...]:
        """Emit a fixed long target or a flat target."""
        if not self._initialized:
            raise RuntimeError("Strategy must be initialized first.")

        if bar.symbol != self.symbol or bar.timeframe != self.timeframe:
            raise ValueError("Unexpected market-data stream.")

        self._prices.append(bar.close)
        prices = list(self._prices)

        fast = sum(prices[-self.fast_window :], Decimal("0"))
        fast /= self.fast_window

        slow = sum(prices, Decimal("0")) / self.slow_window

        target = self.quantity if fast > slow else Decimal("0")

        return (
            Signal(
                strategy_id=self.strategy_id,
                symbol=self.symbol,
                timestamp=bar.timestamp,
                target_quantity=target,
                reason=f"MA regime: fast={fast}, slow={slow}",
            ),
        )

    async def on_fill(self, fill: Fill, position: Position) -> None:
        """Validate notifications without treating proposals as fills."""
        if (
            fill.strategy_id != self.strategy_id
            or position.strategy_id != self.strategy_id
            or fill.symbol != self.symbol
            or position.symbol != self.symbol
        ):
            raise ValueError("Execution notification does not match strategy.")

    def get_position_size(
        self,
        *,
        equity: Decimal,
        entry_price: Decimal,
        stop_price: Decimal,
    ) -> Decimal:
        """Return this validation strategy's configured unit quantity."""
        return self.quantity
