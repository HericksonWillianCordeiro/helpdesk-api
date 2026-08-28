"""seed support categories

Revision ID: 0003
Revises: 0002
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    categories = sa.table(
        "categories",
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("is_active", sa.Boolean),
    )
    for name, description in (
        ("Hardware", "Computadores, periféricos e equipamentos"),
        ("Software", "Sistemas, aplicativos e acessos"),
    ):
        op.execute(
            sa.insert(categories).from_select(
                ["name", "description", "is_active"],
                sa.select(
                    sa.literal(name),
                    sa.literal(description),
                    sa.literal(True),
                ).where(
                    ~sa.exists(
                        sa.select(1)
                        .select_from(categories)
                        .where(categories.c.name == name)
                    )
                ),
            )
        )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM categories WHERE name IN ('Hardware', 'Software')"))
