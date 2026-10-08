"""Process-liveness and dependency-readiness response schemas."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Describe API-process liveness."""

    status: Literal["ok"] = "ok"
    application: str
    environment: Literal["development", "test", "production"]
    is_paper: Literal[True]


class ReadinessResponse(BaseModel):
    """Describe PostgreSQL connectivity readiness."""

    status: Literal["ready", "unavailable"]
    database: Literal["reachable", "unavailable"]
