"""Shared API-schema configuration and numeric aliases."""

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

FiniteDecimal = Annotated[
    Decimal,
    Field(allow_inf_nan=False),
]

PositiveDecimal = Annotated[
    Decimal,
    Field(gt=0, allow_inf_nan=False),
]

NonNegativeDecimal = Annotated[
    Decimal,
    Field(ge=0, allow_inf_nan=False),
]


class ReadModel(BaseModel):
    """Validate response objects, including SQLAlchemy model instances."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )
