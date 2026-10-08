"""Read-only portfolio-valuation endpoints."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.dependencies import DbSession, Page, Window
from app.models import PortfolioSnapshot
from app.schemas.portfolio import PortfolioSnapshotRead

router = APIRouter(
    prefix="/portfolio",
    tags=["portfolio"],
)


@router.get(
    "/snapshots",
    response_model=list[PortfolioSnapshotRead],
)
async def list_snapshots(
    account_id: Annotated[
        str,
        Query(min_length=1, max_length=100),
    ],
    session: DbSession,
    page: Page,
    window: Window,
) -> list[PortfolioSnapshotRead]:
    """List account valuation snapshots within an optional interval."""
    statement = select(PortfolioSnapshot).where(
        PortfolioSnapshot.account_id == account_id
    )

    if window.start is not None:
        statement = statement.where(PortfolioSnapshot.timestamp >= window.start)

    if window.end is not None:
        statement = statement.where(PortfolioSnapshot.timestamp < window.end)

    statement = (
        statement.order_by(
            PortfolioSnapshot.timestamp.desc(),
            PortfolioSnapshot.id.desc(),
        )
        .limit(page.limit)
        .offset(page.offset)
    )

    result = await session.scalars(statement)

    return [PortfolioSnapshotRead.model_validate(snapshot) for snapshot in result.all()]


@router.get(
    "/latest",
    response_model=PortfolioSnapshotRead,
)
async def latest_snapshot(
    account_id: Annotated[
        str,
        Query(min_length=1, max_length=100),
    ],
    session: DbSession,
) -> PortfolioSnapshotRead:
    """Return the latest persisted valuation for one account."""
    statement = (
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.account_id == account_id)
        .order_by(
            PortfolioSnapshot.timestamp.desc(),
            PortfolioSnapshot.id.desc(),
        )
        .limit(1)
    )

    snapshot = await session.scalar(statement)

    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail="No portfolio snapshot found for this account.",
        )

    return PortfolioSnapshotRead.model_validate(snapshot)
