"""Translate desired positions into incremental simulator orders."""

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_DOWN, Decimal
from uuid import UUID

from app.brokers.base import BaseBroker, PaperOrder
from app.core.portfolio_manager import PortfolioManager
from app.strategies.base import BaseStrategy, Fill, Signal
from app.utils.exceptions import ReconciliationError, RiskRejected


@dataclass(frozen=True, slots=True)
class ExecutedOrder:
    """Associate a completed simulator order with its originating signal."""

    order_id: UUID
    signal_id: UUID
    fill: Fill


class ExecutionManager:
    """Execute one strategy against its isolated simulated account."""

    def __init__(
        self,
        *,
        strategy: BaseStrategy,
        broker: BaseBroker,
        portfolio: PortfolioManager,
        lot_size: Decimal = Decimal("0.00000001"),
    ) -> None:
        """Configure quantity rounding and signal deduplication."""
        if not lot_size.is_finite() or lot_size <= 0:
            raise ValueError("lot_size must be finite and positive.")

        if not broker.is_paper:
            raise ValueError("Only paper execution is supported.")

        self.strategy = strategy
        self.broker = broker
        self.portfolio = portfolio
        self.lot_size = lot_size
        self.executions: list[ExecutedOrder] = []
        self._seen_signals: set[UUID] = set()

    async def execute(
        self,
        signal: Signal,
        *,
        reference_price: Decimal,
        timestamp: datetime,
    ) -> ExecutedOrder | None:
        """Execute a target at a subsequent permitted replay event."""
        if signal.signal_id in self._seen_signals:
            return None

        if (
            signal.strategy_id != self.strategy.strategy_id
            or signal.symbol != self.portfolio.symbol
        ):
            raise RiskRejected("Signal does not belong to this account.")

        if timestamp < signal.timestamp:
            raise RiskRejected("Execution cannot precede the signal.")

        if signal.target_quantity < 0:
            raise RiskRejected("Short targets are unsupported.")

        target = (signal.target_quantity / self.lot_size).to_integral_value(
            rounding=ROUND_DOWN
        ) * self.lot_size

        difference = target - self.portfolio.quantity

        if difference == 0:
            self._seen_signals.add(signal.signal_id)
            return None

        order = PaperOrder(
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            quantity=difference,
            reference_price=reference_price,
            timestamp=timestamp,
            client_order_id=str(signal.signal_id),
        )

        result = await self.broker.place_order(order)

        if result.status != "filled" or result.fill is None:
            raise ReconciliationError(
                "This replay requires confirmed immediate simulator fills."
            )

        self._seen_signals.add(signal.signal_id)

        execution = ExecutedOrder(
            order_id=result.order_id,
            signal_id=signal.signal_id,
            fill=result.fill,
        )
        self.executions.append(execution)

        await self.strategy.on_fill(
            result.fill,
            self.portfolio.position(),
        )

        return execution
