"""Read-only strategy-instance endpoints."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.dependencies import DbSession, Page
from app.models import Strategy
from app.schemas.strategy import StrategyRead

router = APIRouter(
    prefix="/strategies",
    tags=["strategies"],
)


@router.get("", response_model=list[StrategyRead])
async def list_strategies(
    session: DbSession,
    page: Page,
) -> list[StrategyRead]:
    """List persisted strategy instances, newest first."""
    statement = (
        select(Strategy)
        .order_by(Strategy.created_at.desc(), Strategy.id.desc())
        .limit(page.limit)
        .offset(page.offset)
    )

    result = await session.scalars(statement)

    return [StrategyRead.model_validate(strategy) for strategy in result.all()]


@router.get("/{strategy_id}", response_model=StrategyRead)
async def get_strategy(
    strategy_id: str,
    session: DbSession,
) -> StrategyRead:
    """Return one persisted strategy instance."""
    strategy = await session.get(Strategy, strategy_id)

    if strategy is None:
        raise HTTPException(
            status_code=404,
            detail="Strategy not found.",
        )

    return StrategyRead.model_validate(strategy)
