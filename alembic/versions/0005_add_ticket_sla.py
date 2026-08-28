"""add ticket SLA deadline

Revision ID: 0005
Revises: 0004
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("sla_due_at", sa.DateTime(timezone=True)))
    if op.get_bind().dialect.name == "postgresql":
        expression = """
            created_at + CASE priority
                WHEN 'CRITICAL' THEN INTERVAL '4 hours'
                WHEN 'HIGH' THEN INTERVAL '8 hours'
                WHEN 'MEDIUM' THEN INTERVAL '24 hours'
                ELSE INTERVAL '72 hours'
            END
        """
    else:
        expression = """
            datetime(created_at, CASE priority
                WHEN 'CRITICAL' THEN '+4 hours'
                WHEN 'HIGH' THEN '+8 hours'
                WHEN 'MEDIUM' THEN '+24 hours'
                ELSE '+72 hours'
            END)
        """
    op.execute(
        sa.text(
            f"UPDATE tickets SET sla_due_at = {expression} WHERE sla_due_at IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("tickets", "sla_due_at")
