"""user location

Revision ID: e1035fe78463
Revises: d243a780c058
Create Date: 2026-10-03 11:25:05.134029

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1035fe78463'
down_revision: Union[str, Sequence[str], None] = 'd243a780c058'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("state", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("zip_code", sa.String(10), nullable=True))
    op.add_column("users", sa.Column("location_label", sa.String(120), nullable=True))
    op.add_column("users", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("timezone", sa.String(64), nullable=True))


def downgrade() -> None:
    for c in ["timezone", "longitude", "latitude", "location_label", "zip_code", "state", "city"]:
        op.drop_column("users", c)
