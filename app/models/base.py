"""Shared SQLAlchemy model infrastructure."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, MetaData, Numeric, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(UTC)


def decimal_type() -> Numeric[Decimal]:
    """Return the project's initial fixed-precision numeric type."""
    return Numeric(precision=28, scale=10, asdecimal=True)


class Base(DeclarativeBase):
    """Provide the shared metadata for all ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    """Provide an application-generated UUID primary key."""

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )


class CreatedAtMixin:
    """Provide a timezone-aware record creation timestamp."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
