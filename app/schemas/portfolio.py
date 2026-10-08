"""Portfolio API response schemas."""

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field

from app.schemas.common import (
    FiniteDecimal,
    NonNegativeDecimal,
    ReadModel,
)


class PortfolioSnapshotRead(ReadModel):
    """Describe a valuation snapshot in one reporting currency."""

    id: UUID
    timestamp: AwareDatetime

    account_id: str = Field(min_length=1, max_length=100)
    currency: str = Field(min_length=1, max_length=20)

    cash: FiniteDecimal
    equity: FiniteDecimal
    gross_exposure: NonNegativeDecimal
    net_exposure: FiniteDecimal
    realized_pnl: FiniteDecimal
    unrealized_pnl: FiniteDecimal

    is_paper: Literal[True]
