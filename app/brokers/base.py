"""Broker interface and internal simulation order objects."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from app.strategies.base import Fill, Position


@dataclass(frozen=True, slots=True, kw_only=True)
class PaperOrder:
    """Describe one incremental order sent to a simulator."""

    strategy_id: str
    symbol: str
    quantity: Decimal
    reference_price: Decimal
    timestamp: datetime
    client_order_id: str
    order_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        """Validate order identity, time, quantity, and reference price."""
        for identifier in (
            self.strategy_id,
            self.symbol,
            self.client_order_id,
        ):
            if (
                not isinstance(identifier, str)
                or not identifier
                or identifier != identifier.strip()
            ):
                raise ValueError("Order identifiers must be nonempty and trimmed.")

        for amount in (
            self.quantity,
            self.reference_price,
        ):
            if not isinstance(amount, Decimal) or not amount.is_finite():
                raise ValueError("Order amounts must be finite Decimals.")

        if self.quantity == 0 or self.reference_price <= 0:
            raise ValueError("Invalid quantity or reference price.")

        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("Order timestamp must be timezone-aware.")


@dataclass(frozen=True, slots=True, kw_only=True)
class OrderResult:
    """Separate an acknowledgement from an optional actual fill."""

    order_id: UUID
    status: Literal["accepted", "filled"]
    fill: Fill | None


class BaseBroker(ABC):
    """Define the initial paper execution boundary."""

    @property
    @abstractmethod
    def is_paper(self) -> bool:
        """Report whether this implementation uses a paper environment."""
        raise NotImplementedError

    @abstractmethod
    async def connect(self) -> None:
        """Initialize broker resources."""
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self) -> None:
        """Release broker resources."""
        raise NotImplementedError

    @abstractmethod
    async def place_order(self, order: PaperOrder) -> OrderResult:
        """Submit an incremental order through the broker's risk gate."""
        raise NotImplementedError

    @abstractmethod
    async def get_positions(self) -> tuple[Position, ...]:
        """Return authoritative positions for this implementation."""
        raise NotImplementedError
