"""Time-series storage for strategy position proposals."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, decimal_type


class SignalRecord(Base):
    """Represent a signal stored in a TimescaleDB hypertable."""

    __tablename__ = "signals"

    __table_args__ = (
        Index(
            "ix_signals_strategy_timestamp",
            "strategy_id",
            "timestamp",
        ),
        Index(
            "ix_signals_symbol_timestamp",
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

    strategy_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("strategies.id", ondelete="RESTRICT"),
        nullable=False,
    )

    symbol: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    target_quantity: Mapped[Decimal] = mapped_column(
        decimal_type(),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
