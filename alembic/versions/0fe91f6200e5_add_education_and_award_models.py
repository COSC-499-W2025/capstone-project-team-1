"""add_education_and_award_models

Revision ID: 0fe91f6200e5
Revises: 9b4e55b3f8c4
Create Date: 2026-03-29 18:23:24.623155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0fe91f6200e5'
down_revision: Union[str, Sequence[str], None] = '9b4e55b3f8c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create education table
    op.create_table('education',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.String(), nullable=False),
        sa.Column('institution', sa.String(), nullable=False),
        sa.Column('degree', sa.String(), nullable=False),
        sa.Column('field_of_study', sa.String(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('gpa', sa.String(), nullable=True),
        sa.Column('honors', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_education_id'), 'education', ['id'], unique=False)
    op.create_index(op.f('ix_education_portfolio_id'), 'education', ['portfolio_id'], unique=False)

    # Create awards table
    op.create_table('awards',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('issuer', sa.String(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_awards_id'), 'awards', ['id'], unique=False)
    op.create_index(op.f('ix_awards_portfolio_id'), 'awards', ['portfolio_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_awards_portfolio_id'), table_name='awards')
    op.drop_index(op.f('ix_awards_id'), table_name='awards')
    op.drop_table('awards')
    op.drop_index(op.f('ix_education_portfolio_id'), table_name='education')
    op.drop_index(op.f('ix_education_id'), table_name='education')
    op.drop_table('education')
