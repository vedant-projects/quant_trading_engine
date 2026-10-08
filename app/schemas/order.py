"""Order API response schemas."""

from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from app.schemas.common import (
    NonNegativeDecimal,
    PositiveDecimal,
    ReadModel,
)

OrderStatus = Literal[
    "new",
    "risk_rejected",
    "approved",
    "submitted",
    "partially_filled",
    "filled",
    "canceled",
    "rejected",
    "expired",
    "unknown",
]


class OrderRead(ReadModel):
    """Describe an order and its recorded lifecycle state."""

    id: UUID
    strategy_id: str = Field(min_length=1, max_length=100)
    account_id: str = Field(min_length=1, max_length=100)
    client_order_id: str = Field(min_length=1, max_length=100)
    broker_order_id: str | None

    symbol: str = Field(min_length=1, max_length=100)
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit"]

    quantity: PositiveDecimal
    filled_quantity: NonNegativeDecimal
    limit_price: PositiveDecimal | None

    status: OrderStatus
    is_paper: Literal[True]
    risk_reason: str | None
    signal_id: UUID | None
    created_at: AwareDatetime

    @model_validator(mode="after")
    def validate_order_amounts(self) -> Self:
        """Reject inconsistent quantities or price specifications."""
        if self.filled_quantity > self.quantity:
            raise ValueError("filled_quantity cannot exceed quantity.")

        if self.order_type == "market" and self.limit_price is not None:
            raise ValueError("A market order cannot specify limit_price.")

        if self.order_type == "limit" and self.limit_price is None:
            raise ValueError("A limit order must specify limit_price.")

        return self
