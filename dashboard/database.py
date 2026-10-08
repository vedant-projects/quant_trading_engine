"""Asynchronous database resources and FastAPI session dependency.

This module does not create tables. Schema changes belong to Alembic.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings


class Database:
    """Own one engine and its session factory within one process/event loop."""

    def __init__(self, settings: Settings) -> None:
        """Configure the engine without immediately connecting to PostgreSQL."""
        self.engine: AsyncEngine = create_async_engine(
            settings.database_url.get_secret_value(),
            echo=False,
            hide_parameters=True,
            pool_pre_ping=True,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            connect_args={
                "timeout": settings.database_connect_timeout_seconds,
            },
        )

        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield a fresh session without automatically committing.

        Notes
        -----
        Callers must explicitly define write transactions.
        Closing the session releases resources and rolls back any
        unfinished transaction.
        """
        async with self._session_factory() as session:
            yield session

    async def ping(self) -> None:
        """Verify that PostgreSQL accepts a simple query."""
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def close(self) -> None:
        """Dispose of the engine's connection pool."""
        await self.engine.dispose()


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Provide an independent session to one FastAPI request."""
    database = cast(Database, request.app.state.database)

    async with database.session() as session:
        yield session
