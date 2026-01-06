"""Add missing_kb_items and question_logs tables

Revision ID: a7455c17a382
Revises: 
Create Date: 2025-12-28 21:25:06.858587

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7455c17a382'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create missing_kb_items table
    op.create_table(
        'missing_kb_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('missing_detail', sa.Text(), nullable=False),
        sa.Column('ai_response_preview', sa.Text(), nullable=True),
        sa.Column('suggested_namespace', sa.String(), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by_kb_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_missing_kb_items_id'), 'missing_kb_items', ['id'], unique=False)
    op.create_index(op.f('ix_missing_kb_items_user_id'), 'missing_kb_items', ['user_id'], unique=False)
    op.create_index(op.f('ix_missing_kb_items_is_resolved'), 'missing_kb_items', ['is_resolved'], unique=False)
    op.create_index(op.f('ix_missing_kb_items_created_at'), 'missing_kb_items', ['created_at'], unique=False)

    # Create question_logs table
    op.create_table(
        'question_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('normalized_question', sa.String(), nullable=True),
        sa.Column('context_type', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('user_tier', sa.String(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('has_sources', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_question_logs_id'), 'question_logs', ['id'], unique=False)
    op.create_index(op.f('ix_question_logs_user_id'), 'question_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_question_logs_question'), 'question_logs', ['question'], unique=False)
    op.create_index(op.f('ix_question_logs_normalized_question'), 'question_logs', ['normalized_question'], unique=False)
    op.create_index(op.f('ix_question_logs_context_type'), 'question_logs', ['context_type'], unique=False)
    op.create_index(op.f('ix_question_logs_category'), 'question_logs', ['category'], unique=False)
    op.create_index(op.f('ix_question_logs_user_tier'), 'question_logs', ['user_tier'], unique=False)
    op.create_index(op.f('ix_question_logs_created_at'), 'question_logs', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop question_logs table
    op.drop_index(op.f('ix_question_logs_created_at'), table_name='question_logs')
    op.drop_index(op.f('ix_question_logs_user_tier'), table_name='question_logs')
    op.drop_index(op.f('ix_question_logs_category'), table_name='question_logs')
    op.drop_index(op.f('ix_question_logs_context_type'), table_name='question_logs')
    op.drop_index(op.f('ix_question_logs_normalized_question'), table_name='question_logs')
    op.drop_index(op.f('ix_question_logs_question'), table_name='question_logs')
    op.drop_index(op.f('ix_question_logs_user_id'), table_name='question_logs')
    op.drop_index(op.f('ix_question_logs_id'), table_name='question_logs')
    op.drop_table('question_logs')

    # Drop missing_kb_items table
    op.drop_index(op.f('ix_missing_kb_items_created_at'), table_name='missing_kb_items')
    op.drop_index(op.f('ix_missing_kb_items_is_resolved'), table_name='missing_kb_items')
    op.drop_index(op.f('ix_missing_kb_items_user_id'), table_name='missing_kb_items')
    op.drop_index(op.f('ix_missing_kb_items_id'), table_name='missing_kb_items')
    op.drop_table('missing_kb_items')
