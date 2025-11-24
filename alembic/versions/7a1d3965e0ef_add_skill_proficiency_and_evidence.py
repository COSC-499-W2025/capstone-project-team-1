"""Add proficiency and evidence columns to project_skills."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "7a1d3965e0ef"
down_revision: Union[str, Sequence[str], None] = "b30abc89d0a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with richer project skill metadata."""
    op.add_column("project_skills", sa.Column("proficiency", sa.Float(), nullable=True))
    op.add_column("project_skills", sa.Column("evidence", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema changes."""
    op.drop_column("project_skills", "evidence")
    op.drop_column("project_skills", "proficiency")
