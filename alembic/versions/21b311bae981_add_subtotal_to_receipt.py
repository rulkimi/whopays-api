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
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
