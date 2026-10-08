"""Single-instrument spot portfolio accounting for isolated simulations."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.strategies.base import Fill, Position

ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class PortfolioValuation:
    """Capture one internally consistent account valuation."""

    timestamp: datetime
    cash: Decimal
    equity: Decimal
    gross_exposure: Decimal
    net_exposure: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal


class PortfolioManager:
    """Track cash, long holdings, cost basis, and mark-to-market equity."""

    def __init__(
        self,
        *,
        strategy_id: str,
        symbol: str,
        initial_cash: Decimal,
        started_at: datetime,
    ) -> None:
        """Initialize an isolated, flat simulated account."""
        if not initial_cash.is_finite() or initial_cash <= ZERO:
            raise ValueError("initial_cash must be finite and positive.")

        self.strategy_id = strategy_id
        self.symbol = symbol
        self.cash = initial_cash
        self.quantity = ZERO
        self.average_price = ZERO
        self.mark_price = ZERO
        self.realized_pnl = ZERO
        self._updated_at = started_at

    @property
    def unrealized_pnl(self) -> Decimal:
        """Return marked profit on remaining holdings, excluding future fees."""
        return self.quantity * (self.mark_price - self.average_price)

    @property
    def equity(self) -> Decimal:
        """Return cash plus marked holdings."""
        return self.cash + self.quantity * self.mark_price

    def mark(self, price: Decimal) -> None:
        """Update the valuation price without changing cash or holdings."""
        if not isinstance(price, Decimal):
            raise TypeError("Mark price must be Decimal.")

        if not price.is_finite() or price <= ZERO:
            raise ValueError("Mark price must be finite and positive.")

        self.mark_price = price

    def apply_fill(self, fill: Fill) -> None:
        """Apply a validated execution using average-cost accounting."""
        if fill.strategy_id != self.strategy_id or fill.symbol != self.symbol:
            raise ValueError("Fill does not belong to this portfolio.")

        new_quantity = self.quantity + fill.quantity
        new_cash = self.cash - fill.quantity * fill.price - fill.commission

        if new_quantity < ZERO:
            raise ValueError("Short positions are unsupported.")

        if new_cash < ZERO:
            raise ValueError("Insufficient cash for the execution.")

        if fill.quantity > ZERO:
            total_cost = self.quantity * self.average_price + fill.quantity * fill.price
            new_average = total_cost / new_quantity
            realized_change = -fill.commission
        else:
            sold_quantity = -fill.quantity
            realized_change = (
                sold_quantity * (fill.price - self.average_price) - fill.commission
            )
            new_average = self.average_price

        if new_quantity == ZERO:
            new_average = ZERO

        self.cash = new_cash
        self.quantity = new_quantity
        self.average_price = new_average
        self.realized_pnl += realized_change
        self._updated_at = fill.timestamp

    def position(self) -> Position:
        """Return an authoritative position snapshot."""
        return Position(
            strategy_id=self.strategy_id,
            symbol=self.symbol,
            quantity=self.quantity,
            average_price=self.average_price,
            updated_at=self._updated_at,
        )

    def valuation(self, timestamp: datetime) -> PortfolioValuation:
        """Capture account values using the current mark."""
        exposure = self.quantity * self.mark_price

        return PortfolioValuation(
            timestamp=timestamp,
            cash=self.cash,
            equity=self.equity,
            gross_exposure=abs(exposure),
            net_exposure=exposure,
            realized_pnl=self.realized_pnl,
            unrealized_pnl=self.unrealized_pnl,
        )
