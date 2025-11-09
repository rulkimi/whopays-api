"""add subtotal to receipt

Revision ID: 20251109174418
Revises: ba5e8b458e4d
Create Date: 2025-11-09 17:44:18.755943

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251109174418'
down_revision: Union[str, Sequence[str], None] = 'ba5e8b458e4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'receipts',
        sa.Column(
            'subtotal',
            sa.Float(),
            nullable=False,
            server_default='0'
        )
    )
    op.alter_column('receipts', 'subtotal', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('receipts', 'subtotal')
