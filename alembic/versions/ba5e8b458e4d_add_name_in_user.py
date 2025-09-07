"""add name in user

Revision ID: ba5e8b458e4d
Revises: e8da1cb12e2a
Create Date: 2025-09-07 14:07:07.927692

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba5e8b458e4d'
down_revision: Union[str, Sequence[str], None] = 'e8da1cb12e2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
	"""Upgrade schema."""
	# 1. Add the column as nullable first
	op.add_column('users', sa.Column('name', sa.String(), nullable=True))
	# 2. Fill in placeholder data for existing rows with null name
	conn = op.get_bind()
	users_table = sa.table(
		'users',
		sa.column('id', sa.Integer),
		sa.column('name', sa.String)
	)
	# Set all null names to a placeholder, e.g., 'Unknown'
	conn.execute(
		users_table.update().where(users_table.c.name == None).values(name='Unknown')
	)
	# 3. Alter the column to be non-nullable
	op.alter_column('users', 'name', nullable=False)


def downgrade() -> None:
	"""Downgrade schema."""
	op.drop_column('users', 'name')
