"""Database-free tests for ORM metadata and schema structure."""

import pytest
from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.models import (
    Base,
    FillReceipt,
    Order,
    PortfolioSnapshot,
    SignalRecord,
    Strategy,
    Trade,
)

EXPECTED_TABLES = {
    "strategies",
    "orders",
    "signals",
    "trades",
    "fill_receipts",
    "portfolio_snapshots",
}


def test_all_models_register_their_tables() -> None:
    """Importing the public model package registers every table."""
    assert set(Base.metadata.tables) == EXPECTED_TABLES


@pytest.mark.parametrize(
    "model",
    [SignalRecord, Trade],
)
def test_hypertable_primary_key_includes_timestamp(model: type) -> None:
    """Time-series primary keys include the time partitioning column."""
    columns = set(model.__table__.primary_key.columns.keys())

    assert columns == {"id", "timestamp"}


def test_strategy_primary_key_matches_domain_identifier() -> None:
    """Persisted strategy IDs use the domain's string identifier."""
    columns = list(Strategy.__table__.primary_key.columns)

    assert len(columns) == 1
    assert columns[0].name == "id"
    assert columns[0].type.python_type is str


def test_order_primary_key_is_not_time_partitioned() -> None:
    """Orders remain normal tables with a UUID primary key."""
    columns = set(Order.__table__.primary_key.columns.keys())

    assert columns == {"id"}


def test_fill_receipt_uniqueness_is_account_scoped() -> None:
    """Broker fill identifiers are unique within an account."""
    columns = set(FillReceipt.__table__.primary_key.columns.keys())

    assert columns == {"account_id", "broker_fill_id"}


def test_client_order_identifier_is_account_scoped() -> None:
    """Client order identifiers cannot repeat within the same account."""
    constraints = [
        constraint
        for constraint in Order.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert any(
        set(constraint.columns.keys()) == {"account_id", "client_order_id"}
        for constraint in constraints
    )


@pytest.mark.parametrize(
    ("model", "constraint_name"),
    [
        (Strategy, "ck_strategies_paper_only"),
        (Order, "ck_orders_paper_only"),
        (Trade, "ck_trades_paper_only"),
        (PortfolioSnapshot, "ck_portfolio_snapshots_paper_only"),
    ],
)
def test_paper_only_constraint_is_present(
    model: type,
    constraint_name: str,
) -> None:
    """Execution-related tables declare the paper-only constraint."""
    constraints = {
        constraint.name: constraint
        for constraint in model.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert constraint_name in constraints
    assert "is_paper = true" in str(constraints[constraint_name].sqltext)


@pytest.mark.parametrize(
    "model",
    [
        Strategy,
        Order,
        SignalRecord,
        Trade,
        FillReceipt,
        PortfolioSnapshot,
    ],
)
def test_model_ddl_compiles_for_postgresql(model: type) -> None:
    """Each table definition can compile to PostgreSQL CREATE TABLE SQL."""
    statement = CreateTable(model.__table__)
    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "CREATE TABLE" in sql
    assert model.__tablename__ in sql


def test_all_foreign_key_targets_resolve() -> None:
    """Foreign keys point to registered metadata columns."""
    for table in Base.metadata.tables.values():
        for foreign_key in table.foreign_keys:
            assert foreign_key.column is not None


def test_trade_quantity_and_price_use_fixed_precision() -> None:
    """Execution amounts use the intended numeric storage precision."""
    for column_name in ("quantity", "price", "commission"):
        column = Trade.__table__.columns[column_name]

        assert column.type.precision == 28
        assert column.type.scale == 10


def test_time_series_timestamps_are_timezone_aware() -> None:
    """The time partition columns preserve timezone-aware timestamps."""
    assert SignalRecord.__table__.columns.timestamp.type.timezone is True
    assert Trade.__table__.columns.timestamp.type.timezone is True


def test_signal_correlation_is_not_an_invalid_uuid_only_foreign_key() -> None:
    """Orders do not reference a hypertable using its UUID alone."""
    assert len(Order.__table__.columns.signal_id.foreign_keys) == 0
