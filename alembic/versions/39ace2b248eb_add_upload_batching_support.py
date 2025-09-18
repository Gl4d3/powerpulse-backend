"""add_upload_batching_support

Revision ID: 39ace2b248eb
Revises: 15bad82d620e
Create Date: 2025-09-17 18:49:12.915994

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '39ace2b248eb'
down_revision: Union[str, Sequence[str], None] = '15bad82d620e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create upload_sessions table
    op.create_table('upload_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('upload_id', sa.String(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('upload_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('mode', sa.String(), nullable=False),
        sa.Column('force_reprocess', sa.Boolean(), default=False),
        sa.Column('total_conversations', sa.Integer(), nullable=True),
        sa.Column('total_messages', sa.Integer(), nullable=True),
        sa.Column('estimated_interactions', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('progress_percentage', sa.Float(), default=0.0),
        sa.Column('current_stage', sa.String(), nullable=True),
        sa.Column('conversations_processed', sa.Integer(), default=0),
        sa.Column('interactions_detected', sa.Integer(), default=0),
        sa.Column('interactions_analyzed', sa.Integer(), default=0),
        sa.Column('avg_csi_score', sa.Float(), nullable=True),
        sa.Column('processing_start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_processing_time_seconds', sa.Float(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('error_details', sa.JSON(), nullable=True),
        sa.Column('job_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_upload_sessions_upload_id', 'upload_sessions', ['upload_id'])
    op.create_index('idx_upload_sessions_status', 'upload_sessions', ['status'])

    # Create batch_contexts table
    op.create_table('batch_contexts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('batch_number', sa.Integer(), nullable=False),
        sa.Column('context_window_size', sa.Integer(), default=20000),
        sa.Column('actual_tokens_used', sa.Integer(), nullable=True),
        sa.Column('interaction_count', sa.Integer(), nullable=False),
        sa.Column('conversation_ids', sa.JSON(), nullable=True),
        sa.Column('interaction_ids', sa.JSON(), nullable=True),
        sa.Column('batch_start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('batch_end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_duration_seconds', sa.Float(), nullable=True),
        sa.Column('api_calls_count', sa.Integer(), default=0),
        sa.Column('successful_interactions', sa.Integer(), default=0),
        sa.Column('failed_interactions', sa.Integer(), default=0),
        sa.Column('avg_batch_csi', sa.Float(), nullable=True),
        sa.Column('errors', sa.JSON(), nullable=True),
        sa.Column('retry_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_batch_contexts_job_id', 'batch_contexts', ['job_id'])

    # Add new fields to existing jobs table
    op.add_column('jobs', sa.Column('total_conversations', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('processed_conversations', sa.Integer(), default=0))
    op.add_column('jobs', sa.Column('total_interactions', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('processed_interactions', sa.Integer(), default=0))
    op.add_column('jobs', sa.Column('current_stage', sa.String(), nullable=True))
    op.add_column('jobs', sa.Column('avg_csi_score', sa.Float(), nullable=True))
    op.add_column('jobs', sa.Column('success_rate', sa.Float(), nullable=True))
    op.add_column('jobs', sa.Column('processing_time_seconds', sa.Float(), nullable=True))
    op.add_column('jobs', sa.Column('total_tokens_used', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('api_calls_made', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('error_count', sa.Integer(), default=0))
    op.add_column('jobs', sa.Column('error_details', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove added columns from jobs table
    op.drop_column('jobs', 'error_details')
    op.drop_column('jobs', 'error_count')
    op.drop_column('jobs', 'api_calls_made')
    op.drop_column('jobs', 'total_tokens_used')
    op.drop_column('jobs', 'processing_time_seconds')
    op.drop_column('jobs', 'success_rate')
    op.drop_column('jobs', 'avg_csi_score')
    op.drop_column('jobs', 'current_stage')
    op.drop_column('jobs', 'processed_interactions')
    op.drop_column('jobs', 'total_interactions')
    op.drop_column('jobs', 'processed_conversations')
    op.drop_column('jobs', 'total_conversations')

    # Drop batch_contexts table
    op.drop_index('idx_batch_contexts_job_id', 'batch_contexts')
    op.drop_table('batch_contexts')

    # Drop upload_sessions table
    op.drop_index('idx_upload_sessions_status', 'upload_sessions')
    op.drop_index('idx_upload_sessions_upload_id', 'upload_sessions')
    op.drop_table('upload_sessions')
