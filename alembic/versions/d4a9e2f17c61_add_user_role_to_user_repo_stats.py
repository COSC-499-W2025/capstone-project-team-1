"""add_user_role_to_user_repo_stats

Revision ID: d4a9e2f17c61
Revises: 31ea0eb0fa88
Create Date: 2026-02-06 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4a9e2f17c61"
down_revision: Union[str, Sequence[str], None] = "31ea0eb0fa88"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_repo_stats", sa.Column("user_role", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_repo_stats", "user_role")
