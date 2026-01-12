"""Add representation_prefs table

Revision ID: 1b366daaa88a
Revises: b1f150021a3d
Create Date: 2026-01-11 21:19:38.678327

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b366daaa88a'
down_revision: Union[str, Sequence[str], None] = 'b1f150021a3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'representation_prefs',
        sa.Column('portfolio_id', sa.String(), nullable=False),
        sa.Column('prefs_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('portfolio_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('representation_prefs')
