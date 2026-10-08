"""Validated historical-job configuration."""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from app.schemas.common import PositiveDecimal


class BacktestJobInput(BaseModel):
    """Describe an isolated CSV-based historical simulation."""

    model_config = ConfigDict(extra="forbid")

    dataset: str = Field(
        default="demo",
        pattern=r"^[A-Za-z0-9_-]{1,80}$",
    )

    strategy: Literal["ma_cross", "bollinger"] = "ma_cross"

    symbol: str = Field(
        default="TEST",
        min_length=1,
        max_length=100,
    )

    timeframe: Literal[
        "1m",
        "5m",
        "15m",
        "1h",
        "1d",
    ] = "1h"

    currency: str = Field(
        default="USD",
        min_length=1,
        max_length=20,
    )

    parameters: dict[str, JsonValue] = Field(default_factory=dict)

    initial_cash: PositiveDecimal = Field(
        default=Decimal("10000"),
    )

    fee_bps: PositiveDecimal = Field(
        default=Decimal("5"),
        le=500,
    )

    slippage_bps: PositiveDecimal = Field(
        default=Decimal("2"),
        le=500,
    )

    periods_per_year: (
        Annotated[
            int,
            Field(gt=0),
        ]
        | None
    ) = None

    persist: bool = False
