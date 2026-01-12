"""Add portfolio_id column to uploaded_zips table.

Revision ID: a5f7c2e91d4b
Revises: cb8c3f3b2f3a
Create Date: 2026-01-11 21:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a5f7c2e91d4b"
down_revision: Union[str, Sequence[str], None] = "cb8c3f3b2f3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "uploaded_zips",
        sa.Column("portfolio_id", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_uploaded_zips_portfolio_id",
        "uploaded_zips",
        ["portfolio_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_uploaded_zips_portfolio_id", table_name="uploaded_zips")
    op.drop_column("uploaded_zips", "portfolio_id")
