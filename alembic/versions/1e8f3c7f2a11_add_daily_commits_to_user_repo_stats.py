"""add_daily_commits_to_user_repo_stats

Revision ID: 1e8f3c7f2a11
Revises: 9b4e55b3f8c4
Create Date: 2026-03-29 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1e8f3c7f2a11"
down_revision: Union[str, Sequence[str], None] = "9b4e55b3f8c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "user_repo_stats",
        sa.Column("daily_commits", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user_repo_stats", "daily_commits")
