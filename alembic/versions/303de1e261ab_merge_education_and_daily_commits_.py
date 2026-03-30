"""merge education and daily_commits migrations

Revision ID: 303de1e261ab
Revises: 0fe91f6200e5, 1e8f3c7f2a11
Create Date: 2026-03-29 22:53:30.769015

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '303de1e261ab'
down_revision: Union[str, Sequence[str], None] = ('0fe91f6200e5', '1e8f3c7f2a11')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
