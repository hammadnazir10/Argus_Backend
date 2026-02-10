"""Remove gc_name column from jobs table

Revision ID: 20260210_130000_002_remove_gc_name
Revises: 001_client_location
Create Date: 2026-02-10 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_remove_gc_name'
down_revision = '001_client_location'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove gc_name column from jobs table"""
    op.drop_column('jobs', 'gc_name')


def downgrade() -> None:
    """Add back gc_name column to jobs table"""
    op.add_column('jobs', sa.Column('gc_name', sa.String(length=255), nullable=True))