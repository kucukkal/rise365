"""circle_contests

Revision ID: b3f291c08e1a
Revises: a68157b83e3f
Create Date: 2026-10-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b3f291c08e1a'
down_revision = 'a68157b83e3f'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'circle_contests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('circle_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('circles.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(100), nullable=False),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('min_progress_pct', sa.Float(), nullable=True),
        sa.Column('min_days', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'circle_contest_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('contest_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('circle_contests.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('daily_pct', sa.Float(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('contest_id', 'user_id', 'snapshot_date',
                            name='uq_contest_snapshot'),
    )


def downgrade():
    op.drop_table('circle_contest_snapshots')
    op.drop_table('circle_contests')
