"""add_project_evidence_table

Revision ID: ed979e56c446
Revises: 31ea0eb0fa88
Create Date: 2026-02-08 12:42:35.488226

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed979e56c446'
down_revision: Union[str, Sequence[str], None] = '31ea0eb0fa88'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "project_evidence",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("repo_stat_id", sa.Integer(), sa.ForeignKey("repo_stats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("project_evidence")
