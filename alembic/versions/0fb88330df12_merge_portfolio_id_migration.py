"""merge portfolio_id migration

Revision ID: 0fb88330df12
Revises: 85f98443ddf4, a5f7c2e91d4b
Create Date: 2026-01-11 21:47:37.486726

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0fb88330df12'
down_revision: Union[str, Sequence[str], None] = ('85f98443ddf4', 'a5f7c2e91d4b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
