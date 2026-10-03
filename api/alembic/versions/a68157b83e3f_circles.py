"""circles

Revision ID: a68157b83e3f
Revises: d243a780c058
Create Date: 2026-10-02 23:57:12.785231

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a68157b83e3f'
down_revision: Union[str, Sequence[str], None] = 'd243a780c058'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "circles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("name_key", sa.String(40), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("owner_id", name="uq_circle_owner"),
    )
    op.create_index("ix_circles_name_key", "circles", ["name_key"], unique=True)
    op.create_table(
        "circle_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("circle_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("circles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("circle_id", "user_id", name="uq_circle_member"),
    )
    op.create_index("ix_circle_members_circle_id", "circle_members", ["circle_id"])
    op.create_index("ix_circle_members_user_id", "circle_members", ["user_id"])


def downgrade() -> None:
    op.drop_table("circle_members")
    op.drop_table("circles")
