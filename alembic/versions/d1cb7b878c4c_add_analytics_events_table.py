"""add analytics_events table

Revision ID: d1cb7b878c4c
Revises: 43fa706fd444
Create Date: 2026-07-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1cb7b878c4c'
down_revision: Union[str, None] = '43fa706fd444'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('analytics_events',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('event', sa.String(length=64), nullable=False),
    sa.Column('metadata', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('analytics_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_analytics_events_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_events_event'), ['event'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('analytics_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_analytics_events_event'))
        batch_op.drop_index(batch_op.f('ix_analytics_events_user_id'))

    op.drop_table('analytics_events')
