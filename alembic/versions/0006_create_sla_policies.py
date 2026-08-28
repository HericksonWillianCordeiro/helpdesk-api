"""create configurable SLA policies

Revision ID: 0006
Revises: 0005
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sla_policies",
        sa.Column(
            "priority",
            sa.dialects.postgresql.ENUM(
                "LOW",
                "MEDIUM",
                "HIGH",
                "CRITICAL",
                name="ticket_priority",
                create_type=False,
            ),
            primary_key=True,
        ),
        sa.Column(
            "resolution_hours",
            sa.Integer(),
            nullable=False,
        ),
    )

    op.execute(
        """
        INSERT INTO sla_policies (priority, resolution_hours)
        VALUES
            ('LOW'::ticket_priority, 72),
            ('MEDIUM'::ticket_priority, 24),
            ('HIGH'::ticket_priority, 8),
            ('CRITICAL'::ticket_priority, 4)
        """
    )


def downgrade() -> None:
    op.drop_table("sla_policies")