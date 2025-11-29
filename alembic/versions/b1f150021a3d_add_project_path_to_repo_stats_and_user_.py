"""add project_path to repo_stats and user_repo_stats

Revision ID: b1f150021a3d
Revises: 83cec4db1e25
Create Date: 2025-11-29 11:47:07.480452

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1f150021a3d'
down_revision: Union[str, Sequence[str], None] = '83cec4db1e25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # Add project_path column to repo_stat table
    op.add_column('repo_stat', sa.Column('project_path', sa.String(), nullable=True))
    
    # Add project_path column to user_repo_stat table
    op.add_column('user_repo_stat', sa.Column('project_path', sa.String(), nullable=True))
    
    # Update existing rows with a placeholder value (can be updated later)
    # or set to the project_name as a fallback
    op.execute("UPDATE repo_stat SET project_path = '/unknown/' || project_name WHERE project_path IS NULL")
    op.execute("UPDATE user_repo_stat SET project_path = '/unknown/' || project_name WHERE project_path IS NULL")
    
    # Now make the columns non-nullable
    with op.batch_alter_table('repo_stat') as batch_op:
        batch_op.alter_column('project_path', nullable=False)
    
    with op.batch_alter_table('user_repo_stat') as batch_op:
        batch_op.alter_column('project_path', nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""

    # Remove project_path column from user_repo_stat table
    with op.batch_alter_table('user_repo_stat') as batch_op:
        batch_op.drop_column('project_path')
    
    # Remove project_path column from repo_stat table
    with op.batch_alter_table('repo_stat') as batch_op:
        batch_op.drop_column('project_path')