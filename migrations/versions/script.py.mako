"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}


revision: str = ${repr(up_revision)}
down_revision: str | Sequence[str] | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    """Apply the migration."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Reject automatic destructive rollback."""
    raise RuntimeError(
        "This project uses forward-only migrations. "
        "Create a reviewed corrective migration instead."
    )