"""Mandatory risk checks for isolated, long-only simulated accounts."""

from datetime import UTC, date, datetime
from decimal import Decimal

from app.core.portfolio_manager import PortfolioManager
from app.utils.exceptions import CircuitBreakerTripped, RiskRejected

ZERO = Decimal("0")
HUNDRED = Decimal("100")


class RiskManager:
    """Check projected cash, exposure, and a latched UTC daily-loss limit."""

    def __init__(
        self,
        portfolio: PortfolioManager,
        *,
        max_daily_loss_pct: Decimal,
        max_position_pct: Decimal,
    ) -> None:
        """Initialize limits and an unset daily equity baseline."""
        for value in (max_daily_loss_pct, max_position_pct):
            if not value.is_finite() or not ZERO < value <= HUNDRED:
                raise ValueError("Risk percentages must be in (0, 100].")

        self.portfolio = portfolio
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_position_pct = max_position_pct

        self.tripped = False
        self._day: date | None = None
        self._day_start_equity: Decimal | None = None
        self._last_timestamp: datetime | None = None

    def observe(self, timestamp: datetime) -> None:
        """Update the daily baseline and latch losses using marked equity."""
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("Risk timestamps must be timezone-aware.")

        if self._last_timestamp is not None and timestamp < self._last_timestamp:
            raise ValueError("Risk observations cannot move backward.")

        self._last_timestamp = timestamp
        day = timestamp.astimezone(UTC).date()

        if day != self._day:
            self._day = day
            self._day_start_equity = self.portfolio.equity

        equity = self.portfolio.equity

        if equity <= ZERO:
            self.tripped = True
            return

        if self.daily_loss_pct >= self.max_daily_loss_pct:
            self.tripped = True

    @property
    def daily_loss_pct(self) -> Decimal:
        """Return loss relative to this UTC day's first observed equity."""
        baseline = self._day_start_equity

        if baseline is None or baseline <= ZERO:
            return ZERO

        loss = (baseline - self.portfolio.equity) / baseline * HUNDRED
        return max(loss, ZERO)

    def check_order(
        self,
        *,
        quantity: Decimal,
        price: Decimal,
        commission: Decimal,
        timestamp: datetime,
    ) -> None:
        """Reject any order that violates the simulator's safety rules."""
        self.observe(timestamp)

        if self.tripped:
            raise CircuitBreakerTripped("Daily-loss circuit breaker is latched.")

        for value in (quantity, price, commission):
            if not isinstance(value, Decimal) or not value.is_finite():
                raise RiskRejected("Order amounts must be finite Decimals.")

        if quantity == ZERO or price <= ZERO or commission < ZERO:
            raise RiskRejected("Invalid order quantity, price, or commission.")

        portfolio = self.portfolio
        target_quantity = portfolio.quantity + quantity

        if target_quantity < ZERO:
            raise RiskRejected("Short positions are unsupported.")

        projected_cash = portfolio.cash - quantity * price - commission

        if projected_cash < ZERO:
            raise RiskRejected("Order would create negative cash.")

        projected_equity = (
            portfolio.equity + quantity * (portfolio.mark_price - price) - commission
        )

        if projected_equity <= ZERO:
            raise RiskRejected("Order would create nonpositive equity.")

        # A reduction may be allowed even if a market move caused an old
        # position to exceed its cap. Increasing exposure is not allowed.
        if target_quantity > portfolio.quantity:
            cap = projected_equity * self.max_position_pct / HUNDRED

            if target_quantity * price > cap:
                raise RiskRejected("Projected position exceeds its cap.")

    def manual_reset(
        self,
        timestamp: datetime,
        *,
        acknowledge: bool,
    ) -> None:
        """Reset only after explicit acknowledgement and a safe observation."""
        if acknowledge is not True:
            raise ValueError("Explicit acknowledgement is required.")

        self.observe(timestamp)

        if (
            self.portfolio.equity <= ZERO
            or self.daily_loss_pct >= self.max_daily_loss_pct
        ):
            raise RiskRejected(
                "Cannot reset while the current loss limit remains breached."
            )

        self.tripped = False
