"""Read-only execution-history endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.dependencies import DbSession, Page, Window
from app.models import Trade
from app.schemas.trade import TradeRead

router = APIRouter(
    prefix="/trades",
    tags=["trades"],
)


@router.get("", response_model=list[TradeRead])
async def list_trades(
    session: DbSession,
    page: Page,
    window: Window,
    account_id: Annotated[
        str | None,
        Query(min_length=1, max_length=100),
    ] = None,
    strategy_id: Annotated[
        str | None,
        Query(min_length=1, max_length=100),
    ] = None,
    symbol: Annotated[
        str | None,
        Query(min_length=1, max_length=100),
    ] = None,
) -> list[TradeRead]:
    """List recorded fills, newest first."""
    statement = select(Trade)

    if account_id is not None:
        statement = statement.where(Trade.account_id == account_id)

    if strategy_id is not None:
        statement = statement.where(Trade.strategy_id == strategy_id)

    if symbol is not None:
        statement = statement.where(Trade.symbol == symbol)

    if window.start is not None:
        statement = statement.where(Trade.timestamp >= window.start)

    if window.end is not None:
        statement = statement.where(Trade.timestamp < window.end)

    statement = (
        statement.order_by(Trade.timestamp.desc(), Trade.id.desc())
        .limit(page.limit)
        .offset(page.offset)
    )

    result = await session.scalars(statement)

    return [TradeRead.model_validate(trade) for trade in result.all()]
