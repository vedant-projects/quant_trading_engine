"""Performance-report schemas."""

from typing import Annotated

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
)


class EquityPoint(BaseModel):
    """Represent one chronological equity observation."""

    model_config = ConfigDict(extra="forbid")

    timestamp: AwareDatetime
    equity: Annotated[FiniteFloat, Field(gt=0)]


class MetricsSummary(BaseModel):
    """Describe metrics computed from equally spaced equity observations."""

    model_config = ConfigDict(extra="forbid")

    observation_count: int = Field(ge=2)
    return_count: int = Field(ge=1)
    periods_per_year: int = Field(gt=0)

    total_return: FiniteFloat
    annualized_return: FiniteFloat | None
    annualized_volatility: FiniteFloat | None

    sharpe: FiniteFloat | None
    sortino: FiniteFloat | None
    calmar: FiniteFloat | None

    max_drawdown: Annotated[FiniteFloat, Field(ge=0, le=1)]


class BacktestReport(BaseModel):
    """Package a strategy's equity observations and summary metrics."""

    model_config = ConfigDict(extra="forbid")

    strategy_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    currency: str = Field(min_length=1)

    metrics: MetricsSummary
    equity_curve: list[EquityPoint] = Field(min_length=2)

    notes: list[str] = Field(default_factory=list)
