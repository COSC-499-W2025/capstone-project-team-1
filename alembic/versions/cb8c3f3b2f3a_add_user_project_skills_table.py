"""Add user-scoped project skills table.

Revision ID: cb8c3f3b2f3a
Revises: b30abc89d0a8
Create Date: 2025-11-17 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "cb8c3f3b2f3a"
down_revision: Union[str, Sequence[str], None] = "b30abc89d0a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_project_skills",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("repo_stat_id", sa.Integer(), sa.ForeignKey("repo_stats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_email", sa.String(), nullable=False),
        sa.Column("proficiency", sa.Float(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("repo_stat_id", "skill_id", "user_email", name="uq_user_project_skill"),
    )


def downgrade() -> None:
    op.drop_table("user_project_skills")
