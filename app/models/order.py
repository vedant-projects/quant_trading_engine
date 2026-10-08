"""Persisted order intentions and broker lifecycle state."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    CreatedAtMixin,
    UUIDPrimaryKeyMixin,
    decimal_type,
)


class Order(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Represent one order tracked by the execution manager."""

    __tablename__ = "orders"

    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "client_order_id",
            name="uq_orders_account_client_order",
        ),
        CheckConstraint(
            "side IN ('buy', 'sell')",
            name="ck_orders_valid_side",
        ),
        CheckConstraint(
            "order_type IN ('market', 'limit')",
            name="ck_orders_valid_type",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_orders_positive_quantity",
        ),
        CheckConstraint(
            "filled_quantity >= 0 AND filled_quantity <= quantity",
            name="ck_orders_valid_filled_quantity",
        ),
        CheckConstraint(
            "(order_type = 'market' AND limit_price IS NULL) OR "
            "(order_type = 'limit' AND limit_price IS NOT NULL AND limit_price > 0)",
            name="ck_orders_valid_limit_price",
        ),
        CheckConstraint(
            "status IN ("
            "'new', 'risk_rejected', 'approved', 'submitted', "
            "'partially_filled', 'filled', 'canceled', "
            "'rejected', 'expired', 'unknown'"
            ")",
            name="ck_orders_valid_status",
        ),
        CheckConstraint(
            "is_paper = true",
            name="ck_orders_paper_only",
        ),
        Index(
            "ix_orders_strategy_created",
            "strategy_id",
            "created_at",
        ),
        Index(
            "ix_orders_account_status",
            "account_id",
            "status",
        ),
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

    client_order_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    broker_order_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    symbol: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    side: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    order_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="market",
        server_default="market",
    )

    quantity: Mapped[Decimal] = mapped_column(
        decimal_type(),
        nullable=False,
    )

    filled_quantity: Mapped[Decimal] = mapped_column(
        decimal_type(),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
    )

    limit_price: Mapped[Decimal | None] = mapped_column(
        decimal_type(),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="new",
        server_default="new",
    )

    is_paper: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    risk_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Correlation identifier only. It is not a foreign key to the hypertable.
    signal_id: Mapped[UUID | None] = mapped_column(
        nullable=True,
    )
