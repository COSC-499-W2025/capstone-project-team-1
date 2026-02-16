"""add_thumbnail_url_to_repo_stats

Revision ID: 9b4e55b3f8c4
Revises: d4a9e2f17c61, ed979e56c446
Create Date: 2026-02-13 15:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9b4e55b3f8c4"
down_revision: Union[str, Sequence[str], None] = ("d4a9e2f17c61", "ed979e56c446")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("repo_stats", sa.Column("thumbnail_url", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("repo_stats", "thumbnail_url")
