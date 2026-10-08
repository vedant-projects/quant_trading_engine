"""Persisted account-level portfolio valuation snapshots."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin, decimal_type


class PortfolioSnapshot(UUIDPrimaryKeyMixin, Base):
    """Represent one account valuation in one reporting currency."""

    __tablename__ = "portfolio_snapshots"

    __table_args__ = (
        CheckConstraint(
            "gross_exposure >= 0",
            name="ck_portfolio_snapshots_nonnegative_gross",
        ),
        CheckConstraint(
            "is_paper = true",
            name="ck_portfolio_snapshots_paper_only",
        ),
        Index(
            "ix_portfolio_snapshots_account_timestamp",
            "account_id",
            "timestamp",
        ),
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    account_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    cash: Mapped[Decimal] = mapped_column(
        decimal_type(),
        nullable=False,
    )

    equity: Mapped[Decimal] = mapped_column(
        decimal_type(),
        nullable=False,
    )

    gross_exposure: Mapped[Decimal] = mapped_column(
        decimal_type(),
        nullable=False,
    )

    net_exposure: Mapped[Decimal] = mapped_column(
        decimal_type(),
        nullable=False,
    )

    realized_pnl: Mapped[Decimal] = mapped_column(
        decimal_type(),
        nullable=False,
    )

    unrealized_pnl: Mapped[Decimal] = mapped_column(
        decimal_type(),
        nullable=False,
    )

    is_paper: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
