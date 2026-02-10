"""Replace due_date with bid_date and bid_time in jobs table

Revision ID: 20260210_140000_003_replace_due_date
Revises: 002_remove_gc_name
Create Date: 2026-02-10 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_replace_due_date'
down_revision = '002_remove_gc_name'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Replace due_date with bid_date and bid_time columns"""
    # Drop due_date column
    op.drop_column('jobs', 'due_date')
    
    # Add bid_date column (Date type)
    op.add_column('jobs', sa.Column('bid_date', sa.Date(), nullable=True))
    
    # Add bid_time column (Time type)
    op.add_column('jobs', sa.Column('bid_time', sa.Time(), nullable=True))


def downgrade() -> None:
    """Replace bid_date and bid_time back with due_date"""
    # Drop bid_date and bid_time columns
    op.drop_column('jobs', 'bid_time')
    op.drop_column('jobs', 'bid_date')
    
    # Add back due_date column
    op.add_column('jobs', sa.Column('due_date', sa.DateTime(), nullable=True))
