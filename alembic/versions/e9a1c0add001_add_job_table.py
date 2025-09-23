"""add job table

Revision ID: e9a1c0add001
Revises: ba5e8b458e4d
Create Date: 2025-09-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9a1c0add001'
down_revision: Union[str, Sequence[str], None] = 'ba5e8b458e4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
	"""Upgrade schema."""
	op.create_table(
		'jobs',
		sa.Column('id', sa.Integer(), nullable=False),
		sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
		sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
		sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
		sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
		sa.Column('user_id', sa.Integer(), nullable=False),
		sa.Column('job_type', sa.String(), nullable=False),
		sa.Column('status', sa.String(), nullable=False),
		sa.Column('progress', sa.SmallInteger(), nullable=False, server_default=sa.text('0')),
		sa.Column('payload', sa.Text(), nullable=True),
		sa.Column('result', sa.Text(), nullable=True),
		sa.Column('error_code', sa.String(), nullable=True),
		sa.Column('error_message', sa.Text(), nullable=True),
		sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
		sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
		sa.Column('receipt_id', sa.Integer(), nullable=True),
		sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
		sa.ForeignKeyConstraint(['receipt_id'], ['receipts.id'], ondelete='SET NULL'),
		sa.PrimaryKeyConstraint('id')
	)
	op.create_index(op.f('ix_jobs_id'), 'jobs', ['id'], unique=False)
	op.create_index(op.f('ix_jobs_user_id'), 'jobs', ['user_id'], unique=False)
	op.create_index(op.f('ix_jobs_job_type'), 'jobs', ['job_type'], unique=False)
	op.create_index(op.f('ix_jobs_status'), 'jobs', ['status'], unique=False)
	op.create_index(op.f('ix_jobs_receipt_id'), 'jobs', ['receipt_id'], unique=False)
	# Composite indexes for frequent queries
	op.create_index('ix_jobs_user_created_at', 'jobs', ['user_id', 'created_at'], unique=False)
	op.create_index('ix_jobs_status_created_at', 'jobs', ['status', 'created_at'], unique=False)
	op.create_index('ix_jobs_type_status', 'jobs', ['job_type', 'status'], unique=False)


def downgrade() -> None:
	"""Downgrade schema."""
	op.drop_index('ix_jobs_type_status', table_name='jobs')
	op.drop_index('ix_jobs_status_created_at', table_name='jobs')
	op.drop_index('ix_jobs_user_created_at', table_name='jobs')
	op.drop_index(op.f('ix_jobs_receipt_id'), table_name='jobs')
	op.drop_index(op.f('ix_jobs_status'), table_name='jobs')
	op.drop_index(op.f('ix_jobs_job_type'), table_name='jobs')
	op.drop_index(op.f('ix_jobs_user_id'), table_name='jobs')
	op.drop_index(op.f('ix_jobs_id'), table_name='jobs')
	op.drop_table('jobs')


