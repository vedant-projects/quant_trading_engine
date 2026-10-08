"""Execution records and broker-fill deduplication receipts."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, decimal_type


class Trade(Base):
    """Represent one fill, not a completed round-trip trade."""

    __tablename__ = "trades"

    __table_args__ = (
        CheckConstraint(
            "quantity <> 0",
            name="ck_trades_nonzero_quantity",
        ),
        CheckConstraint(
            "price > 0",
            name="ck_trades_positive_price",
        ),
        CheckConstraint(
            "is_paper = true",
            name="ck_trades_paper_only",
        ),
        Index(
            "ix_trades_strategy_timestamp",
            "strategy_id",
            "timestamp",
        ),
        Index(
            "ix_trades_order_timestamp",
            "order_id",
            "timestamp",
        ),
        Index(
            "ix_trades_symbol_timestamp",
            "symbol",
            "timestamp",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
    )

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
    )

    strategy_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("strategies.id", ondelete="RESTRICT"),
        nullable=False,
    )

    account_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    broker_fill_id: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    symbol: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    quote_currency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    quantity: Mapped[Decimal] = mapped_column(
        decimal_type(),
        nullable=False,
    )

    price: Mapped[Decimal] = mapped_column(
        decimal_type(),
        nullable=False,
    )

    commission: Mapped[Decimal] = mapped_column(
        decimal_type(),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
    )

    is_paper: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )


class FillReceipt(CreatedAtMixin, Base):
    """Provide an account-scoped unique identifier for an ingested fill.

    Notes
    -----
    The execution layer must insert this receipt and its corresponding Trade
    in one transaction.

    trade_id and trade_timestamp are correlation fields, not a foreign key.
    This table alone does not implement an exactly-once ingestion workflow.
    """

    __tablename__ = "fill_receipts"

    account_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    broker_fill_id: Mapped[str] = mapped_column(
        String(200),
        primary_key=True,
    )

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
    )

    trade_id: Mapped[UUID] = mapped_column(
        nullable=False,
    )

    trade_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
