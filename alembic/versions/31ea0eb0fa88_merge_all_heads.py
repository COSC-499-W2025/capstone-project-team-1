"""merge_all_heads

Revision ID: 31ea0eb0fa88
Revises: 0fb88330df12, 172d4f4751be, 1b366daaa88a
Create Date: 2026-01-17 13:50:26.607140

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31ea0eb0fa88'
down_revision: Union[str, Sequence[str], None] = ('0fb88330df12', '172d4f4751be', '1b366daaa88a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
