"""add subtotal to receipt

Revision ID: 21b311bae981
Revises: e9a1c0add001
Create Date: 2025-11-01 12:48:35.738882

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21b311bae981'
down_revision: Union[str, Sequence[str], None] = 'e9a1c0add001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add the column as nullable first
    op.add_column('receipts', sa.Column('subtotal', sa.Float(), nullable=True))
    
    # 2. Calculate subtotal for existing rows: total_amount - tax - service_charge
    conn = op.get_bind()
    receipts_table = sa.table(
        'receipts',
        sa.column('id', sa.Integer),
        sa.column('subtotal', sa.Float),
        sa.column('total_amount', sa.Float),
        sa.column('tax', sa.Float),
        sa.column('service_charge', sa.Float)
    )
    # Update all existing receipts with calculated subtotal
    conn.execute(
        sa.update(receipts_table).values(
            subtotal=receipts_table.c.total_amount - receipts_table.c.tax - receipts_table.c.service_charge
        )
    )
    
    # 3. Alter the column to be non-nullable
    op.alter_column('receipts', 'subtotal', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('receipts', 'subtotal')
