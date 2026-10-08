"""Shared dependencies for read-only API routes."""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Query, Request
from pydantic import AwareDatetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database import Database, get_db_session


@dataclass(frozen=True, slots=True)
class Pagination:
    """Describe bounded offset pagination."""

    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class TimeRange:
    """Describe an optional inclusive-start, exclusive-end interval."""

    start: datetime | None
    end: datetime | None


def get_pagination(
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
) -> Pagination:
    """Validate pagination before querying the database."""
    return Pagination(limit=limit, offset=offset)


def get_time_range(
    start: Annotated[AwareDatetime | None, Query()] = None,
    end: Annotated[AwareDatetime | None, Query()] = None,
) -> TimeRange:
    """Validate optional timezone-aware interval boundaries."""
    if start is not None and end is not None and start >= end:
        raise HTTPException(
            status_code=422,
            detail="start must precede end.",
        )

    return TimeRange(start=start, end=end)


def get_application_settings(request: Request) -> Settings:
    """Return the settings belonging to the running application."""
    return cast(Settings, request.app.state.settings)


def get_database(request: Request) -> Database:
    """Return the database resources belonging to this application."""
    return cast(Database, request.app.state.database)


DbSession = Annotated[AsyncSession, Depends(get_db_session)]
Page = Annotated[Pagination, Depends(get_pagination)]
Window = Annotated[TimeRange, Depends(get_time_range)]

AppSettings = Annotated[Settings, Depends(get_application_settings)]
AppDatabase = Annotated[Database, Depends(get_database)]
