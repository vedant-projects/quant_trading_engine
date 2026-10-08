"""Immediate-fill local simulator with mandatory risk checks."""

import asyncio
from decimal import Decimal
from uuid import uuid4

from app.brokers.base import BaseBroker, OrderResult, PaperOrder
from app.core.risk_manager import RiskManager
from app.strategies.base import Fill, Position
from app.utils.exceptions import BrokerError

BPS = Decimal("10000")


class PaperBroker(BaseBroker):
    """Simulate long-only spot executions with adverse fixed-bps slippage."""

    def __init__(
        self,
        risk_manager: RiskManager,
        *,
        fee_bps: Decimal = Decimal("5"),
        slippage_bps: Decimal = Decimal("2"),
    ) -> None:
        """Configure costs and initialize an empty idempotency map."""
        for value in (fee_bps, slippage_bps):
            if not value.is_finite() or not Decimal("0") <= value <= Decimal("500"):
                raise ValueError("Simulator cost bps must be in [0, 500].")

        self.risk_manager = risk_manager
        self.portfolio = risk_manager.portfolio
        self.fee_bps = fee_bps
        self.slippage_bps = slippage_bps

        self._connected = False
        self._lock = asyncio.Lock()
        self._orders: dict[str, tuple[PaperOrder, OrderResult]] = {}

    @property
    def is_paper(self) -> bool:
        """Always identify this implementation as a local simulator."""
        return True

    async def connect(self) -> None:
        """Enable the local simulator without network activity."""
        self._connected = True

    async def disconnect(self) -> None:
        """Disable new simulated submissions."""
        self._connected = False

    async def get_positions(self) -> tuple[Position, ...]:
        """Return the account's single authoritative position."""
        return (self.portfolio.position(),)

    async def place_order(self, order: PaperOrder) -> OrderResult:
        """Risk-check and atomically apply one simulated fill."""
        async with self._lock:
            if not self._connected:
                raise BrokerError("Simulator is disconnected.")

            existing = self._orders.get(order.client_order_id)

            if existing is not None:
                previous_order, previous_result = existing

                if previous_order != order:
                    raise BrokerError(
                        "A client order ID was reused for different content."
                    )

                return previous_result

            if (
                order.strategy_id != self.portfolio.strategy_id
                or order.symbol != self.portfolio.symbol
            ):
                raise BrokerError("Order does not match the simulated account.")

            self.portfolio.mark(order.reference_price)

            direction = Decimal("1") if order.quantity > 0 else Decimal("-1")
            price = order.reference_price * (
                Decimal("1") + direction * self.slippage_bps / BPS
            )
            commission = abs(order.quantity) * price * self.fee_bps / BPS

            self.risk_manager.check_order(
                quantity=order.quantity,
                price=price,
                commission=commission,
                timestamp=order.timestamp,
            )

            fill = Fill(
                strategy_id=order.strategy_id,
                symbol=order.symbol,
                order_id=str(order.order_id),
                fill_id=str(uuid4()),
                timestamp=order.timestamp,
                quantity=order.quantity,
                price=price,
                commission=commission,
            )

            self.portfolio.apply_fill(fill)
            self.risk_manager.observe(order.timestamp)

            result = OrderResult(
                order_id=order.order_id,
                status="filled",
                fill=fill,
            )

            self._orders[order.client_order_id] = (order, result)
            return result
