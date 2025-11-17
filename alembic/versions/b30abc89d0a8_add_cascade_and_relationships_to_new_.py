"""Add cascade and relationships to new models

Revision ID: b30abc89d0a8
Revises: 3b3f297185db
Create Date: 2025-11-16 17:20:57.241365

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b30abc89d0a8"
down_revision: Union[str, Sequence[str], None] = "3b3f297185db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Original intent (unique + cascade) is now handled directly in the
    initial schema migration, so this migration is a no-op for SQLite-only use.
    """
    pass


def downgrade() -> None:
    """Downgrade schema.

    Matches the no-op upgrade; nothing to undo.
    """
    pass

