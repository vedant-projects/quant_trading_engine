"""Transactional persistence of completed historical simulation jobs."""

from uuid import UUID

from sqlalchemy.dialects.postgresql import insert

from app.backtest.engine import SimulationResult
from app.database import Database
from app.models import (
    FillReceipt,
    Order,
    PortfolioSnapshot,
    SignalRecord,
    Strategy,
    Trade,
)


async def persist_simulation(
    database: Database,
    result: SimulationResult,
    *,
    implementation: str,
    parameters: dict[str, object],
    account_id: str,
    currency: str,
) -> bool:
    """Insert a complete simulation or skip an already persisted job."""
    strategy_id = result.report.strategy_id

    async with database.session() as session:
        async with session.begin():
            statement = (
                insert(Strategy)
                .values(
                    id=strategy_id,
                    name=f"Historical simulation: {implementation}",
                    implementation=implementation,
                    parameters=parameters,
                    status="stopped",
                    is_paper=True,
                )
                .on_conflict_do_nothing(index_elements=["id"])
                .returning(Strategy.id)
            )

            inserted = await session.scalar(statement)

            if inserted is None:
                return False

            session.add_all(
                [
                    SignalRecord(
                        id=signal.signal_id,
                        timestamp=signal.timestamp,
                        strategy_id=strategy_id,
                        symbol=signal.symbol,
                        target_quantity=signal.target_quantity,
                        reason=signal.reason,
                    )
                    for signal in result.signals
                ]
            )

            for execution in result.executions:
                fill = execution.fill

                session.add(
                    Order(
                        id=execution.order_id,
                        strategy_id=strategy_id,
                        account_id=account_id,
                        client_order_id=str(execution.signal_id),
                        broker_order_id=str(execution.order_id),
                        symbol=fill.symbol,
                        side="buy" if fill.quantity > 0 else "sell",
                        order_type="market",
                        quantity=abs(fill.quantity),
                        filled_quantity=abs(fill.quantity),
                        limit_price=None,
                        status="filled",
                        is_paper=True,
                        risk_reason="Approved by local simulation risk gate",
                        signal_id=execution.signal_id,
                        created_at=fill.timestamp,
                    )
                )

            # Orders must exist before their trade and receipt references.
            await session.flush()

            for execution in result.executions:
                fill = execution.fill

                trade_id = UUID(fill.fill_id)

                session.add(
                    Trade(
                        id=trade_id,
                        timestamp=fill.timestamp,
                        order_id=execution.order_id,
                        strategy_id=strategy_id,
                        account_id=account_id,
                        broker_fill_id=fill.fill_id,
                        symbol=fill.symbol,
                        quote_currency=currency,
                        quantity=fill.quantity,
                        price=fill.price,
                        commission=fill.commission,
                        is_paper=True,
                    )
                )

                session.add(
                    FillReceipt(
                        account_id=account_id,
                        broker_fill_id=fill.fill_id,
                        order_id=execution.order_id,
                        trade_id=trade_id,
                        trade_timestamp=fill.timestamp,
                    )
                )

            session.add_all(
                [
                    PortfolioSnapshot(
                        timestamp=snapshot.timestamp,
                        account_id=account_id,
                        currency=currency,
                        cash=snapshot.cash,
                        equity=snapshot.equity,
                        gross_exposure=snapshot.gross_exposure,
                        net_exposure=snapshot.net_exposure,
                        realized_pnl=snapshot.realized_pnl,
                        unrealized_pnl=snapshot.unrealized_pnl,
                        is_paper=True,
                    )
                    for snapshot in result.snapshots
                ]
            )

    return True
