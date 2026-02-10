"""Add client_name and location to jobs table

Revision ID: 20260210_120000_001_add_client_location
Revises: 
Create Date: 2026-02-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_client_location'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add client_name and location columns to jobs table"""
    # Add client_name column
    op.add_column('jobs', sa.Column('client_name', sa.String(length=255), nullable=True))
    
    # Add location column
    op.add_column('jobs', sa.Column('location', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Remove client_name and location columns from jobs table"""
    # Drop location column
    op.drop_column('jobs', 'location')
    
    # Drop client_name column
    op.drop_column('jobs', 'client_name')