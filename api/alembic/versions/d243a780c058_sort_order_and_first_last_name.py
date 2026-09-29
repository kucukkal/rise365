"""sort_order and first last name

Revision ID: d243a780c058
Revises: ab142c25822b
Create Date: 2026-09-29 16:25:53.745895

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd243a780c058'
down_revision: Union[str, Sequence[str], None] = 'ab142c25822b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"))
    op.add_column("users", sa.Column("first_name", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(100), nullable=True))
    op.execute("""
        UPDATE users
        SET first_name = split_part(trim(name), ' ', 1),
            last_name  = NULLIF(trim(substr(trim(name), length(split_part(trim(name), ' ', 1)) + 1)), '')
        WHERE name IS NOT NULL
    """)
    op.execute("""
        WITH named AS (
            SELECT pl.id AS level_id,
                   'MyRise_' || regexp_replace(initcap(trim(u.name)), '[^[:alnum:]]', '', 'g') AS base,
                   right(regexp_replace(coalesce(u.phone, ''), '[^0-9]', '', 'g'), 4) AS last4,
                   count(*) OVER (PARTITION BY regexp_replace(initcap(trim(u.name)), '[^[:alnum:]]', '', 'g')) AS dup
            FROM program_levels pl
            JOIN users u ON u.program_level_id::text = pl.id::text
            WHERE pl.level_type = 'myrise'
              AND pl.description = 'Personal MyBuild level'
              AND u.name IS NOT NULL
        )
        UPDATE program_levels p
        SET name = left(CASE WHEN n.dup > 1 THEN n.base || '_' || n.last4 ELSE n.base END, 100)
        FROM named n
        WHERE p.id = n.level_id
    """)


def downgrade() -> None:
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
    op.drop_column("tasks", "sort_order")
