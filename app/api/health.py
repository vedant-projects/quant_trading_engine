"""Health endpoints without trading side effects."""

import asyncio

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import AppDatabase, AppSettings
from app.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
)
async def health(settings: AppSettings) -> HealthResponse:
    """Report process liveness for the supported paper-only mode."""
    if settings.is_paper is not True:
        raise HTTPException(
            status_code=503,
            detail="Unsupported trading mode.",
        )

    return HealthResponse(
        application=settings.app_name,
        environment=settings.app_env,
        is_paper=True,
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={
        503: {
            "model": ReadinessResponse,
            "description": "PostgreSQL is unavailable or timed out.",
        },
    },
)
async def readiness(
    database: AppDatabase,
    settings: AppSettings,
) -> ReadinessResponse | JSONResponse:
    """Check PostgreSQL connectivity within the configured timeout."""
    try:
        await asyncio.wait_for(
            database.ping(),
            timeout=settings.database_health_timeout_seconds,
        )
    except (
        SQLAlchemyError,
        OSError,
        TimeoutError,
    ):
        response = ReadinessResponse(
            status="unavailable",
            database="unavailable",
        )

        return JSONResponse(
            status_code=503,
            content=response.model_dump(),
        )

    return ReadinessResponse(
        status="ready",
        database="reachable",
    )
