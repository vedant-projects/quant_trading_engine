"""Execution API response schemas."""

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator

from app.schemas.common import (
    FiniteDecimal,
    PositiveDecimal,
    ReadModel,
)


class TradeRead(ReadModel):
    """Describe one recorded execution."""

    id: UUID
    timestamp: AwareDatetime
    order_id: UUID

    strategy_id: str = Field(min_length=1, max_length=100)
    account_id: str = Field(min_length=1, max_length=100)
    broker_fill_id: str = Field(min_length=1, max_length=200)

    symbol: str = Field(min_length=1, max_length=100)
    quote_currency: str = Field(min_length=1, max_length=20)

    quantity: FiniteDecimal
    price: PositiveDecimal
    commission: FiniteDecimal
    is_paper: Literal[True]

    @field_validator("quantity")
    @classmethod
    def reject_zero_quantity(cls, value: FiniteDecimal) -> FiniteDecimal:
        """Require an actual buy or sell execution quantity."""
        if value == 0:
            raise ValueError("Execution quantity cannot be zero.")

        return value
