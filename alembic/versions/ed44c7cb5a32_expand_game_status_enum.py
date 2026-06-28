"""expand game status enum

Revision ID: ed44c7cb5a32
Revises: e2d884368c94
Create Date: 2026-06-28 18:13:51.655466

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed44c7cb5a32'
down_revision: Union[str, None] = 'e2d884368c94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_VALUES = ('open', 'full', 'cancelled', 'completed')
NEW_VALUES = ('draft', 'open', 'partially_filled', 'full', 'confirmed', 'in_progress', 'completed', 'cancelled', 'expired')


def upgrade() -> None:
    with op.batch_alter_table('games', schema=None) as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.Enum(*OLD_VALUES, name='gamestatus'),
            type_=sa.Enum(*NEW_VALUES, name='gamestatus'),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table('games', schema=None) as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.Enum(*NEW_VALUES, name='gamestatus'),
            type_=sa.Enum(*OLD_VALUES, name='gamestatus'),
            existing_nullable=False,
        )
