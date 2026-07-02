"""initial schema

Revision ID: eb729e80d93c
Revises: 
Create Date: 2026-06-27 11:45:38.317993

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb729e80d93c'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'players',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=True),
        sa.Column('first_name', sa.String(length=128), nullable=False),
        sa.Column('language', sa.String(length=8), nullable=True),
        sa.Column('skill_level', sa.Float(), nullable=True),
        sa.Column('home_area', sa.String(length=64), nullable=True),
        sa.Column('preferred_courts', sa.Text(), nullable=True),
        sa.Column('level_source', sa.String(length=32), nullable=True),
        sa.Column('available_now', sa.Boolean(), nullable=False),
        sa.Column('available_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rating', sa.Float(), nullable=False),
        sa.Column('matches_played', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('players', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_players_telegram_id'), ['telegram_id'], unique=True)

    op.create_table(
        'games',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('creator_id', sa.Integer(), nullable=False),
        sa.Column('court', sa.String(length=256), nullable=False),
        sa.Column('area', sa.String(length=64), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('time', sa.Time(), nullable=False),
        sa.Column('match_type', sa.Enum('singles', 'doubles', name='matchtype'), nullable=False),
        sa.Column('required_level', sa.Float(), nullable=True),
        sa.Column('status', sa.Enum('open', 'full', 'cancelled', 'completed', name='gamestatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['creator_id'], ['players.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'game_players',
        sa.Column('game_id', sa.Integer(), nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('invited', 'accepted', 'declined', 'confirmed', name='gameplayerstatus'), nullable=False),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('game_id', 'player_id'),
    )


def downgrade() -> None:
    op.drop_table('game_players')
    op.drop_table('games')
    with op.batch_alter_table('players', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_players_telegram_id'))
    op.drop_table('players')
