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
            sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="ticket_priority"),
            primary_key=True,
        ),
        sa.Column("resolution_hours", sa.Integer(), nullable=False),
    )
    op.bulk_insert(
        sa.table(
            "sla_policies",
            sa.column("priority", sa.String),
            sa.column("resolution_hours", sa.Integer),
        ),
        [
            {"priority": "LOW", "resolution_hours": 72},
            {"priority": "MEDIUM", "resolution_hours": 24},
            {"priority": "HIGH", "resolution_hours": 8},
            {"priority": "CRITICAL", "resolution_hours": 4},
        ],
    )


def downgrade() -> None:
    op.drop_table("sla_policies")
