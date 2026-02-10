"""Change bid_time from Time to String in jobs table

Revision ID: 20260210_150000_004_change_bid_time_to_string
Revises: 003_replace_due_date
Create Date: 2026-02-10 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_change_bid_time_to_string'
down_revision = '003_replace_due_date'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Change bid_time from Time to String(20) to preserve AM/PM format"""
    # Alter column type from Time to String
    # Using batch mode for better compatibility
    with op.batch_alter_table('jobs') as batch_op:
        batch_op.alter_column(
            'bid_time',
            type_=sa.String(20),
            existing_type=sa.Time(),
            nullable=True,
            postgresql_using='bid_time::text'
        )


def downgrade() -> None:
    """Revert bid_time from String back to Time"""
    # Alter column type from String back to Time
    with op.batch_alter_table('jobs') as batch_op:
        batch_op.alter_column(
            'bid_time',
            type_=sa.Time(),
            existing_type=sa.String(20),
            nullable=True,
            postgresql_using='bid_time::time'
        )
