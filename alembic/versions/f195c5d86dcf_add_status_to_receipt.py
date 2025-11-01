"""add status to receipt

Revision ID: f195c5d86dcf
Revises: 21b311bae981
Create Date: 2025-01-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f195c5d86dcf'
down_revision: Union[str, Sequence[str], None] = '21b311bae981'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add status column with default value
    op.add_column('receipts', sa.Column('status', sa.String(), nullable=False, server_default='ready'))
    
    # Update existing receipts to 'ready' status (they're already processed)
    conn = op.get_bind()
    receipts_table = sa.table('receipts', sa.column('status', sa.String))
    conn.execute(receipts_table.update().values(status='ready'))
    
    # Create index on status column
    op.create_index(op.f('ix_receipts_status'), 'receipts', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_receipts_status'), table_name='receipts')
    op.drop_column('receipts', 'status')

