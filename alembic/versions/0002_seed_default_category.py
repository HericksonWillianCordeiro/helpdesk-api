"""seed default category

Revision ID: 0002
Revises: 0001
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    categories = sa.table(
        "categories",
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("is_active", sa.Boolean),
    )
    op.execute(
        sa.insert(categories).from_select(
            ["name", "description", "is_active"],
            sa.select(
                sa.literal("Geral"),
                sa.literal("Solicitações gerais de suporte"),
                sa.literal(True),
            ).where(
                ~sa.exists(
                    sa.select(1)
                    .select_from(categories)
                    .where(categories.c.name == "Geral")
                )
            ),
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM categories WHERE name = 'Geral'"))
