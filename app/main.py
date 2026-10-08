"""FastAPI application factory and process resource lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.health import router as health_router
from app.api.router import api_router
from app.config import Settings, get_settings
from app.database import Database
from app.utils.logger import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construct the local, paper-only monitoring API."""
    configuration = settings if settings is not None else get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Initialize process resources and release them during shutdown."""
        configure_logging(configuration.log_level)
        logger = structlog.get_logger("quant_engine")

        database = Database(configuration)

        application.state.settings = configuration
        application.state.database = database

        logger.info(
            "application_started",
            environment=configuration.app_env,
            is_paper=configuration.is_paper,
        )

        try:
            yield
        finally:
            await database.close()
            logger.info("application_stopped")

    application = FastAPI(
        title=configuration.app_name,
        version="0.1.0",
        description=(
            "Local, paper-only monitoring API. "
            "Order submission and strategy deployment are not enabled."
        ),
        lifespan=lifespan,
    )

    @application.exception_handler(SQLAlchemyError)
    async def database_error_handler(
        request: Request,
        error: SQLAlchemyError,
    ) -> JSONResponse:
        """Hide database exception details from API clients and logs."""
        logger = structlog.get_logger("quant_engine")

        logger.warning(
            "database_operation_failed",
            error_type=type(error).__name__,
        )

        return JSONResponse(
            status_code=503,
            content={
                "detail": "Database operation unavailable.",
            },
        )

    application.include_router(health_router)
    application.include_router(api_router)

    return application
