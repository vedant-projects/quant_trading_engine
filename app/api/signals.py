"""Read-only signal-history endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.dependencies import DbSession, Page, Window
from app.models import SignalRecord
from app.schemas.signal import SignalRead

router = APIRouter(
    prefix="/signals",
    tags=["signals"],
)


@router.get("", response_model=list[SignalRead])
async def list_signals(
    session: DbSession,
    page: Page,
    window: Window,
    strategy_id: Annotated[
        str | None,
        Query(min_length=1, max_length=100),
    ] = None,
    symbol: Annotated[
        str | None,
        Query(min_length=1, max_length=100),
    ] = None,
) -> list[SignalRead]:
    """List signals using exact identifier filters and a time interval."""
    statement = select(SignalRecord)

    if strategy_id is not None:
        statement = statement.where(SignalRecord.strategy_id == strategy_id)

    if symbol is not None:
        statement = statement.where(SignalRecord.symbol == symbol)

    if window.start is not None:
        statement = statement.where(SignalRecord.timestamp >= window.start)

    if window.end is not None:
        statement = statement.where(SignalRecord.timestamp < window.end)

    statement = (
        statement.order_by(SignalRecord.timestamp.desc(), SignalRecord.id.desc())
        .limit(page.limit)
        .offset(page.offset)
    )

    result = await session.scalars(statement)

    return [SignalRead.model_validate(signal) for signal in result.all()]
