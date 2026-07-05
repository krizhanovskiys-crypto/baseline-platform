"""add tournament platform v1

Revision ID: a1b2c3d4e5f6
Revises: f0f6e3703ad9
Create Date: 2026-07-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f0f6e3703ad9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('tournaments',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('organizer_player_id', sa.Integer(), nullable=False),
    sa.Column('area', sa.String(length=64), nullable=False),
    sa.Column('court', sa.String(length=256), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('start_time', sa.Time(), nullable=False),
    sa.Column('registration_deadline', sa.Date(), nullable=False),
    sa.Column('max_players', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('DRAFT', 'REGISTRATION_OPEN', 'REGISTRATION_CLOSED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', name='tournamentstatus'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['organizer_player_id'], ['players.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('tournament_players',
    sa.Column('tournament_id', sa.Integer(), nullable=False),
    sa.Column('player_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('REGISTERED', 'WITHDRAWN', name='tournamentplayerstatus'), nullable=False),
    sa.Column('registered_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('tournament_id', 'player_id')
    )

    with op.batch_alter_table('players', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_verified_coach', sa.Boolean(), server_default=sa.text('0'), nullable=False))

    with op.batch_alter_table('games', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tournament_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_games_tournament_id_tournaments', 'tournaments', ['tournament_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    with op.batch_alter_table('games', schema=None) as batch_op:
        batch_op.drop_constraint('fk_games_tournament_id_tournaments', type_='foreignkey')
        batch_op.drop_column('tournament_id')

    with op.batch_alter_table('players', schema=None) as batch_op:
        batch_op.drop_column('is_verified_coach')

    op.drop_table('tournament_players')
    sa.Enum(name='tournamentplayerstatus').drop(op.get_bind(), checkfirst=True)

    op.drop_table('tournaments')
    sa.Enum(name='tournamentstatus').drop(op.get_bind(), checkfirst=True)
