"""Merge skills schema heads

Revision ID: 83cec4db1e25
Revises: 7a1d3965e0ef, cb8c3f3b2f3a
Create Date: 2025-11-23 16:59:11.887966

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '83cec4db1e25'
down_revision: Union[str, Sequence[str], None] = ('7a1d3965e0ef', 'cb8c3f3b2f3a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
