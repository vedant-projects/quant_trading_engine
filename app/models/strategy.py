"""Persisted strategy-instance configuration."""

from typing import Any

from sqlalchemy import Boolean, CheckConstraint, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin


class Strategy(CreatedAtMixin, Base):
    """Represent a configured strategy instance."""

    __tablename__ = "strategies"

    __table_args__ = (
        CheckConstraint(
            "status IN ('stopped', 'running', 'error')",
            name="ck_strategies_valid_status",
        ),
        CheckConstraint(
            "is_paper = true",
            name="ck_strategies_paper_only",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    implementation: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="stopped",
        server_default="stopped",
    )

    is_paper: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
