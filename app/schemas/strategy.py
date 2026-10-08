"""Strategy API response schemas."""

from typing import Literal

from pydantic import AwareDatetime, Field, JsonValue

from app.schemas.common import ReadModel


class StrategyRead(ReadModel):
    """Describe a persisted strategy instance."""

    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    implementation: str = Field(min_length=1, max_length=200)

    parameters: dict[str, JsonValue]

    status: Literal["stopped", "running", "error"]
    is_paper: Literal[True]
    created_at: AwareDatetime
