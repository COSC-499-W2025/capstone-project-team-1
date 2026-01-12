"""add_llm_model_to_consents

Revision ID: 172d4f4751be
Revises: cb8c3f3b2f3a, 85f98443ddf4
Create Date: 2026-01-11 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '172d4f4751be'
down_revision: Union[str, Sequence[str], None] = ('cb8c3f3b2f3a', '85f98443ddf4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add LLM_model column to consents table."""
    # Add LLM_model column to consents table with default value
    op.add_column('consents', sa.Column('LLM_model', sa.String(), nullable=False, server_default='chatGPT'))


def downgrade() -> None:
    """Downgrade schema: Remove LLM_model column from consents table."""
    # Remove LLM_model column from consents table
    op.drop_column('consents', 'LLM_model')
