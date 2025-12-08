"""add_health_score_to_repo_stats

Revision ID: 85f98443ddf4
Revises: b1f150021a3d
Create Date: 2025-12-07 09:38:17.289136

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '85f98443ddf4'
down_revision: Union[str, Sequence[str], None] = 'b1f150021a3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add health_score column to repo_stats table
    op.add_column('repo_stats', sa.Column('health_score', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove health_score column from repo_stats table
    op.drop_column('repo_stats', 'health_score')
