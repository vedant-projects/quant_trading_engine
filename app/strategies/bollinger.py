"""Long-only Bollinger mean-reversion strategy."""

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


class BollingerStrategy(BaseStrategy):
    """Enter below the lower band and exit at the rolling mean."""

    def __init__(
        self,
        *,
        strategy_id: str,
        parameters: Mapping[str, object] | None = None,
    ) -> None:
        """Validate parameters and allocate rolling state."""
        super().__init__(
            strategy_id=strategy_id,
            parameters=parameters,
        )
        self.validate_parameters()

        self._prices: deque[Decimal] = deque(maxlen=self.window)
        self._held_quantity = Decimal("0")
        self._initialized = False

    def validate_parameters(self) -> None:
        """Validate supported strategy parameters."""
        reject_unknown_parameters(
            self.parameters,
            {"symbol", "timeframe", "window", "width", "quantity"},
        )

        self.symbol = text_parameter(self.parameters, "symbol", "TEST")
        self.timeframe = text_parameter(self.parameters, "timeframe", "1h")
        self.window = integer_parameter(self.parameters, "window", 20)
        self.width = decimal_parameter(self.parameters, "width", "2")
        self.quantity = decimal_parameter(self.parameters, "quantity", "1")

        timeframe_duration(self.timeframe)

        if self.window < 2:
            raise ValueError("window must be at least two.")

    def get_required_data(self) -> tuple[DataRequirement, ...]:
        """Declare the required completed-bar history."""
        return (
            DataRequirement(
                symbol=self.symbol,
                timeframe=self.timeframe,
                warmup_bars=self.window,
            ),
        )

    async def initialize(self, history: Sequence[MarketBar]) -> None:
        """Initialize rolling prices for a fresh simulated account."""
        matching = [
            bar
            for bar in history
            if bar.symbol == self.symbol and bar.timeframe == self.timeframe
        ]

        if len(matching) < self.window:
            raise ValueError("Insufficient Bollinger warmup.")

        self._prices.clear()
        self._prices.extend(bar.close for bar in matching[-self.window :])
        self._held_quantity = Decimal("0")
        self._initialized = True

    async def on_data(self, bar: MarketBar) -> tuple[Signal, ...]:
        """Propose an entry or exit using only completed observations."""
        if not self._initialized:
            raise RuntimeError("Strategy must be initialized first.")

        if bar.symbol != self.symbol or bar.timeframe != self.timeframe:
            raise ValueError("Unexpected market-data stream.")

        self._prices.append(bar.close)

        mean = sum(self._prices, Decimal("0")) / self.window
        variance = (
            sum(
                ((price - mean) ** 2 for price in self._prices),
                Decimal("0"),
            )
            / self.window
        )

        deviation = variance.sqrt()

        if deviation == 0:
            return ()

        lower = mean - self.width * deviation

        if self._held_quantity == 0 and bar.close < lower:
            target = self.quantity
            reason = "Close below lower Bollinger band"
        elif self._held_quantity > 0 and bar.close >= mean:
            target = Decimal("0")
            reason = "Close recovered to Bollinger mean"
        else:
            return ()

        return (
            Signal(
                strategy_id=self.strategy_id,
                symbol=self.symbol,
                timestamp=bar.timestamp,
                target_quantity=target,
                reason=reason,
            ),
        )

    async def on_fill(self, fill: Fill, position: Position) -> None:
        """Update holdings only after an actual simulated execution."""
        if (
            fill.strategy_id != self.strategy_id
            or position.strategy_id != self.strategy_id
            or fill.symbol != self.symbol
            or position.symbol != self.symbol
        ):
            raise ValueError("Execution notification does not match strategy.")

        self._held_quantity = position.quantity

    def get_position_size(
        self,
        *,
        equity: Decimal,
        entry_price: Decimal,
        stop_price: Decimal,
    ) -> Decimal:
        """Return the configured pipeline-validation quantity."""
        return self.quantity
