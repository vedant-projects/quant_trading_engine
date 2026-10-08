"""Create the initial paper-only trading schema.

Revision ID: 0001_foundation
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


revision: str = "0001_foundation"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def amount(
    name: str,
    *,
    nullable: bool = False,
    default: str | None = None,
) -> sa.Column:
    """Build a fixed-precision monetary or quantity column."""
    return sa.Column(
        name,
        sa.Numeric(28, 10),
        nullable=nullable,
        server_default=default,
    )


def paper_column() -> sa.Column:
    """Build the paper-mode column shared by several tables."""
    return sa.Column(
        "is_paper",
        sa.Boolean(),
        nullable=False,
        server_default=sa.text("true"),
    )


def created_at_column() -> sa.Column:
    """Build a timezone-aware creation timestamp."""
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )


def strategy_foreign_key() -> sa.ForeignKeyConstraint:
    """Reference the normal strategy table from another table."""
    return sa.ForeignKeyConstraint(
        ["strategy_id"],
        ["strategies.id"],
        ondelete="RESTRICT",
    )


def upgrade() -> None:
    """Create the schema and its time-partitioned tables."""
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS timescaledb"))

    op.create_table(
        "strategies",
        sa.Column("id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("implementation", sa.String(200), nullable=False),
        sa.Column(
            "parameters",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="stopped",
        ),
        paper_column(),
        created_at_column(),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('stopped', 'running', 'error')",
            name="ck_strategies_valid_status",
        ),
        sa.CheckConstraint(
            "is_paper = true",
            name="ck_strategies_paper_only",
        ),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("strategy_id", sa.String(100), nullable=False),
        sa.Column("account_id", sa.String(100), nullable=False),
        sa.Column("client_order_id", sa.String(100), nullable=False),
        sa.Column("broker_order_id", sa.String(200), nullable=True),
        sa.Column("symbol", sa.String(100), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column(
            "order_type",
            sa.String(20),
            nullable=False,
            server_default="market",
        ),
        amount("quantity"),
        amount("filled_quantity", default="0"),
        amount("limit_price", nullable=True),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="new",
        ),
        paper_column(),
        sa.Column("risk_reason", sa.String(500), nullable=True),
        sa.Column("signal_id", sa.Uuid(), nullable=True),
        created_at_column(),
        sa.PrimaryKeyConstraint("id"),
        strategy_foreign_key(),
        sa.UniqueConstraint(
            "account_id",
            "client_order_id",
            name="uq_orders_account_client_order",
        ),
        sa.CheckConstraint(
            "side IN ('buy', 'sell')",
            name="ck_orders_valid_side",
        ),
        sa.CheckConstraint(
            "order_type IN ('market', 'limit')",
            name="ck_orders_valid_type",
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_orders_positive_quantity",
        ),
        sa.CheckConstraint(
            "filled_quantity >= 0 AND filled_quantity <= quantity",
            name="ck_orders_valid_filled_quantity",
        ),
        sa.CheckConstraint(
            "(order_type = 'market' AND limit_price IS NULL) OR "
            "(order_type = 'limit' AND limit_price IS NOT NULL AND limit_price > 0)",
            name="ck_orders_valid_limit_price",
        ),
        sa.CheckConstraint(
            "status IN ("
            "'new', 'risk_rejected', 'approved', 'submitted', "
            "'partially_filled', 'filled', 'canceled', "
            "'rejected', 'expired', 'unknown'"
            ")",
            name="ck_orders_valid_status",
        ),
        sa.CheckConstraint(
            "is_paper = true",
            name="ck_orders_paper_only",
        ),
    )

    op.create_table(
        "signals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("strategy_id", sa.String(100), nullable=False),
        sa.Column("symbol", sa.String(100), nullable=False),
        amount("target_quantity"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", "timestamp"),
        strategy_foreign_key(),
    )

    op.create_table(
        "trades",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("strategy_id", sa.String(100), nullable=False),
        sa.Column("account_id", sa.String(100), nullable=False),
        sa.Column("broker_fill_id", sa.String(200), nullable=False),
        sa.Column("symbol", sa.String(100), nullable=False),
        sa.Column("quote_currency", sa.String(20), nullable=False),
        amount("quantity"),
        amount("price"),
        amount("commission", default="0"),
        paper_column(),
        sa.PrimaryKeyConstraint("id", "timestamp"),
        strategy_foreign_key(),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "quantity <> 0",
            name="ck_trades_nonzero_quantity",
        ),
        sa.CheckConstraint(
            "price > 0",
            name="ck_trades_positive_price",
        ),
        sa.CheckConstraint(
            "is_paper = true",
            name="ck_trades_paper_only",
        ),
    )

    op.create_table(
        "fill_receipts",
        sa.Column("account_id", sa.String(100), nullable=False),
        sa.Column("broker_fill_id", sa.String(200), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("trade_id", sa.Uuid(), nullable=False),
        sa.Column(
            "trade_timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        created_at_column(),
        sa.PrimaryKeyConstraint("account_id", "broker_fill_id"),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="RESTRICT",
        ),
    )

    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("account_id", sa.String(100), nullable=False),
        sa.Column("currency", sa.String(20), nullable=False),
        amount("cash"),
        amount("equity"),
        amount("gross_exposure"),
        amount("net_exposure"),
        amount("realized_pnl"),
        amount("unrealized_pnl"),
        paper_column(),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "gross_exposure >= 0",
            name="ck_portfolio_snapshots_nonnegative_gross",
        ),
        sa.CheckConstraint(
            "is_paper = true",
            name="ck_portfolio_snapshots_paper_only",
        ),
    )

    op.execute(
        sa.text(
            "SELECT create_hypertable("
            "'signals', by_range('timestamp', INTERVAL '7 days'), "
            "if_not_exists => TRUE)"
        )
    )

    op.execute(
        sa.text(
            "SELECT create_hypertable("
            "'trades', by_range('timestamp', INTERVAL '7 days'), "
            "if_not_exists => TRUE)"
        )
    )

    indexes = (
        (
            "ix_orders_strategy_created",
            "orders",
            ["strategy_id", "created_at"],
        ),
        (
            "ix_orders_account_status",
            "orders",
            ["account_id", "status"],
        ),
        (
            "ix_signals_strategy_timestamp",
            "signals",
            ["strategy_id", "timestamp"],
        ),
        (
            "ix_signals_symbol_timestamp",
            "signals",
            ["symbol", "timestamp"],
        ),
        (
            "ix_trades_strategy_timestamp",
            "trades",
            ["strategy_id", "timestamp"],
        ),
        (
            "ix_trades_order_timestamp",
            "trades",
            ["order_id", "timestamp"],
        ),
        (
            "ix_trades_symbol_timestamp",
            "trades",
            ["symbol", "timestamp"],
        ),
        (
            "ix_portfolio_snapshots_account_timestamp",
            "portfolio_snapshots",
            ["account_id", "timestamp"],
        ),
    )

    for name, table, columns in indexes:
        op.create_index(name, table, columns, unique=False)


def downgrade() -> None:
    """Refuse automatic deletion of the trading schema."""
    raise RuntimeError(
        "The foundation migration is forward-only. "
        "Use a reviewed corrective migration or restore a tested backup."
    )