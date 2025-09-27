"""add request logs table

Revision ID: f1a2b3c4d5e6
Revises: e9a1c0add001
Create Date: 2025-09-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e9a1c0add001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
	"""Upgrade schema."""
	op.create_table(
		'request_logs',
		sa.Column('id', sa.Integer(), nullable=False),
		sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
		sa.Column('correlation_id', sa.String(length=64), nullable=False),
		sa.Column('direction', sa.String(length=16), nullable=False),
		sa.Column('connection_type', sa.String(length=16), nullable=True),
		sa.Column('method', sa.String(length=16), nullable=True),
		sa.Column('path_template', sa.String(length=512), nullable=True),
		sa.Column('raw_path', sa.String(length=512), nullable=True),
		sa.Column('route_name', sa.String(length=128), nullable=True),
		sa.Column('status_code', sa.Integer(), nullable=True),
		sa.Column('duration_ms', sa.Integer(), nullable=False),
		sa.Column('client_ip', sa.String(length=64), nullable=True),
		sa.Column('user_agent', sa.String(length=256), nullable=True),
		sa.Column('auth_type', sa.String(length=16), nullable=True),
		sa.Column('user_id', sa.Integer(), nullable=True),
		sa.Column('provider', sa.String(length=64), nullable=True),
		sa.Column('target', sa.String(length=256), nullable=True),
		sa.Column('error_code', sa.String(length=64), nullable=True),
		sa.PrimaryKeyConstraint('id')
	)
	op.create_index('ix_request_logs_created_at', 'request_logs', ['created_at'], unique=False)
	op.create_index('ix_request_logs_correlation_id', 'request_logs', ['correlation_id'], unique=False)
	op.create_index('ix_request_logs_direction_connection', 'request_logs', ['direction', 'connection_type'], unique=False)
	op.create_index('ix_request_logs_path_template', 'request_logs', ['path_template'], unique=False)
	op.create_index('ix_request_logs_status_code', 'request_logs', ['status_code'], unique=False)
	op.create_index('ix_request_logs_user_id', 'request_logs', ['user_id'], unique=False)
	op.create_index('ix_request_logs_provider_target', 'request_logs', ['provider', 'target'], unique=False)
	op.create_index('ix_request_logs_duration_ms', 'request_logs', ['duration_ms'], unique=False)


def downgrade() -> None:
	"""Downgrade schema."""
	op.drop_index('ix_request_logs_duration_ms', table_name='request_logs')
	op.drop_index('ix_request_logs_provider_target', table_name='request_logs')
	op.drop_index('ix_request_logs_user_id', table_name='request_logs')
	op.drop_index('ix_request_logs_status_code', table_name='request_logs')
	op.drop_index('ix_request_logs_path_template', table_name='request_logs')
	op.drop_index('ix_request_logs_direction_connection', table_name='request_logs')
	op.drop_index('ix_request_logs_correlation_id', table_name='request_logs')
	op.drop_index('ix_request_logs_created_at', table_name='request_logs')
	op.drop_table('request_logs')


