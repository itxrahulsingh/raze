"""Add CHECK constraints and enterprise-grade validation.

Adds:
- CHECK constraints for all enum columns
- NOT NULL constraints where missing
- Audit trail tables
- SystemConfig table
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add CHECK constraints for enum columns
    op.create_check_constraint(
        'ck_users_role',
        'users',
        "role IN ('superadmin', 'admin', 'viewer')"
    )
    
    op.create_check_constraint(
        'ck_knowledge_sources_status',
        'knowledge_sources',
        "status IN ('pending', 'processing', 'approved', 'rejected', 'failed')"
    )
    
    op.create_check_constraint(
        'ck_knowledge_sources_type',
        'knowledge_sources',
        "type IN ('pdf', 'docx', 'txt', 'url', 'manual', 'csv', 'html', 'json')"
    )
    
    op.create_check_constraint(
        'ck_knowledge_sources_mode',
        'knowledge_sources',
        "mode IN ('linked', 'persistent')"
    )
    
    op.create_check_constraint(
        'ck_knowledge_chunks_content_not_empty',
        'knowledge_chunks',
        "content IS NOT NULL AND length(trim(content)) > 0"
    )
    
    op.create_check_constraint(
        'ck_conversations_status',
        'conversations',
        "status IN ('active', 'idle', 'ended', 'archived', 'error')"
    )
    
    op.create_check_constraint(
        'ck_messages_role',
        'messages',
        "role IN ('user', 'assistant', 'system', 'tool')"
    )
    
    op.create_check_constraint(
        'ck_memories_type',
        'memories',
        "type IN ('context', 'user', 'operational', 'knowledge')"
    )
    
    op.create_check_constraint(
        'ck_tools_type',
        'tools',
        "type IN ('http_api', 'database', 'function', 'mcp')"
    )
    
    op.create_check_constraint(
        'ck_tool_executions_status',
        'tool_executions',
        "status IN ('success', 'failed', 'timeout', 'rate_limited', 'auth_error')"
    )
    
    # Add SystemConfig table for global settings
    op.create_table(
        'system_configs',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=sa.func.gen_random_uuid()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('key', sa.String(256), nullable=False, unique=True, index=True),
        sa.Column('value', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Index('ix_system_configs_key_active', 'key', 'is_active'),
    )
    
    # Add AuditLog table for tracking changes
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=sa.func.gen_random_uuid()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(64), nullable=False, index=True),
        sa.Column('resource_type', sa.String(64), nullable=False, index=True),
        sa.Column('resource_id', sa.String(256), nullable=False),
        sa.Column('changes', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Index('ix_audit_logs_user_action', 'user_id', 'action'),
        sa.Index('ix_audit_logs_resource', 'resource_type', 'resource_id'),
        sa.Index('ix_audit_logs_created', 'created_at'),
    )


def downgrade() -> None:
    # Drop CHECK constraints
    op.drop_constraint('ck_users_role', 'users')
    op.drop_constraint('ck_knowledge_sources_status', 'knowledge_sources')
    op.drop_constraint('ck_knowledge_sources_type', 'knowledge_sources')
    op.drop_constraint('ck_knowledge_sources_mode', 'knowledge_sources')
    op.drop_constraint('ck_knowledge_chunks_content_not_empty', 'knowledge_chunks')
    op.drop_constraint('ck_conversations_status', 'conversations')
    op.drop_constraint('ck_messages_role', 'messages')
    op.drop_constraint('ck_memories_type', 'memories')
    op.drop_constraint('ck_tools_type', 'tools')
    op.drop_constraint('ck_tool_executions_status', 'tool_executions')
    
    # Drop tables
    op.drop_table('audit_logs')
    op.drop_table('system_configs')
