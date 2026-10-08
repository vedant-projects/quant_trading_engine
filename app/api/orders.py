"""Read-only order-inspection endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.dependencies import DbSession, Page
from app.models import Order
from app.schemas.order import OrderRead, OrderStatus

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
)


@router.get("", response_model=list[OrderRead])
async def list_orders(
    session: DbSession,
    page: Page,
    account_id: Annotated[
        str | None,
        Query(min_length=1, max_length=100),
    ] = None,
    strategy_id: Annotated[
        str | None,
        Query(min_length=1, max_length=100),
    ] = None,
    status: Annotated[OrderStatus | None, Query()] = None,
) -> list[OrderRead]:
    """List orders with optional exact-match filters."""
    statement = select(Order)

    if account_id is not None:
        statement = statement.where(Order.account_id == account_id)

    if strategy_id is not None:
        statement = statement.where(Order.strategy_id == strategy_id)

    if status is not None:
        statement = statement.where(Order.status == status)

    statement = (
        statement.order_by(Order.created_at.desc(), Order.id.desc())
        .limit(page.limit)
        .offset(page.offset)
    )

    result = await session.scalars(statement)

    return [OrderRead.model_validate(order) for order in result.all()]


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: UUID,
    session: DbSession,
) -> OrderRead:
    """Return one recorded order."""
    order = await session.get(Order, order_id)

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    return OrderRead.model_validate(order)
