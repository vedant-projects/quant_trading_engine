"""Signal API response schemas."""

from uuid import UUID

from pydantic import AwareDatetime, Field

from app.schemas.common import FiniteDecimal, ReadModel


class SignalRead(ReadModel):
    """Describe one persisted desired-position signal."""

    id: UUID
    timestamp: AwareDatetime
    strategy_id: str = Field(min_length=1, max_length=100)
    symbol: str = Field(min_length=1, max_length=100)
    target_quantity: FiniteDecimal
    reason: str = Field(min_length=1)
