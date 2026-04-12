"""Initial schema - all tables."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Users table
    op.create_table(
        'user',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), default='viewer'),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('last_login', sa.DateTime),
        sa.Column('metadata', postgresql.JSON, default={}),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('now()'))
    )
    
    # API Keys table
    op.create_table(
        'api_key',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('name', sa.String(100)),
        sa.Column('key_hash', sa.String(255), unique=True),
        sa.Column('key_prefix', sa.String(10)),
        sa.Column('permissions', postgresql.JSON, default=[]),
        sa.Column('rate_limit', sa.Integer, default=100),
        sa.Column('last_used', sa.DateTime),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('expires_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()'))
    )
    
    # Conversations table
    op.create_table(
        'conversation',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(100), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id')),
        sa.Column('title', sa.String(255)),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('metadata', postgresql.JSON, default={}),
        sa.Column('message_count', sa.Integer, default=0),
        sa.Column('total_tokens', sa.Integer, default=0),
        sa.Column('started_at', sa.DateTime, server_default=sa.text('now()')),
        sa.Column('ended_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()'))
    )
    
    # Messages table
    op.create_table(
        'message',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('conversation_id', sa.String(36), sa.ForeignKey('conversation.id'), nullable=False),
        sa.Column('role', sa.String(50)),  # user, assistant, system, tool
        sa.Column('content', sa.Text),
        sa.Column('tool_calls', postgresql.JSON, default=[]),
        sa.Column('tool_results', postgresql.JSON, default=[]),
        sa.Column('tokens_used', sa.Integer, default=0),
        sa.Column('model_used', sa.String(100)),
        sa.Column('latency_ms', sa.Integer),
        sa.Column('metadata', postgresql.JSON, default={}),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()'))
    )
    
    # Knowledge Sources
    op.create_table(
        'knowledge_source',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255)),
        sa.Column('type', sa.String(50)),  # pdf, docx, txt, url, manual
        sa.Column('status', sa.String(50), default='pending'),  # pending, processing, approved, rejected
        sa.Column('file_path', sa.String(500)),
        sa.Column('url', sa.String(500)),
        sa.Column('file_size', sa.Integer),
        sa.Column('content_hash', sa.String(64)),
        sa.Column('chunk_count', sa.Integer, default=0),
        sa.Column('embedding_model', sa.String(100)),
        sa.Column('approved_by', sa.String(36), sa.ForeignKey('user.id')),
        sa.Column('approved_at', sa.DateTime),
        sa.Column('mode', sa.String(50)),  # linked, persistent
        sa.Column('tags', postgresql.JSON, default=[]),
        sa.Column('metadata', postgresql.JSON, default={}),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()'))
    )
    
    # Knowledge Chunks
    op.create_table(
        'knowledge_chunk',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('source_id', sa.String(36), sa.ForeignKey('knowledge_source.id'), nullable=False),
        sa.Column('content', sa.Text),
        sa.Column('chunk_index', sa.Integer),
        sa.Column('token_count', sa.Integer),
        sa.Column('embedding', postgresql.JSON),  # Vector type
        sa.Column('metadata', postgresql.JSON, default={}),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()'))
    )
    
    # Memory table
    op.create_table(
        'memory',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id')),
        sa.Column('session_id', sa.String(100)),
        sa.Column('type', sa.String(50)),  # context, user, operational, knowledge
        sa.Column('content', sa.Text),
        sa.Column('importance_score', sa.Float, default=0.5),
        sa.Column('decay_rate', sa.Float, default=0.95),
        sa.Column('access_count', sa.Integer, default=0),
        sa.Column('last_accessed', sa.DateTime),
        sa.Column('expires_at', sa.DateTime),
        sa.Column('embedding', postgresql.JSON),
        sa.Column('metadata', postgresql.JSON, default={}),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()'))
    )
    
    # Memory Retention Policy
    op.create_table(
        'memory_retention_policy',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100)),
        sa.Column('type', sa.String(50)),
        sa.Column('max_count', sa.Integer),
        sa.Column('ttl_days', sa.Integer),
        sa.Column('min_importance', sa.Float),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()'))
    )
    
    # Tools
    op.create_table(
        'tool',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100)),
        sa.Column('description', sa.Text),
        sa.Column('type', sa.String(50)),  # http_api, database, function
        sa.Column('schema', postgresql.JSON),
        sa.Column('endpoint_url', sa.String(500)),
        sa.Column('method', sa.String(20)),  # GET, POST, PUT, DELETE
        sa.Column('auth_type', sa.String(50)),
        sa.Column('auth_config', postgresql.JSON),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('tags', postgresql.JSON, default=[]),
        sa.Column('usage_count', sa.Integer, default=0),
        sa.Column('success_rate', sa.Float, default=1.0),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()'))
    )
    
    # Tool Execution
    op.create_table(
        'tool_execution',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tool_id', sa.String(36), sa.ForeignKey('tool.id'), nullable=False),
        sa.Column('conversation_id', sa.String(36), sa.ForeignKey('conversation.id')),
        sa.Column('input_data', postgresql.JSON),
        sa.Column('output_data', postgresql.JSON),
        sa.Column('status', sa.String(50)),  # success, error
        sa.Column('error_message', sa.Text),
        sa.Column('latency_ms', sa.Integer),
        sa.Column('executed_at', sa.DateTime, server_default=sa.text('now()'))
    )
    
    # AI Config
    op.create_table(
        'ai_config',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100)),
        sa.Column('is_default', sa.Boolean, default=False),
        sa.Column('provider', sa.String(50)),
        sa.Column('model_name', sa.String(100)),
        sa.Column('temperature', sa.Float, default=0.7),
        sa.Column('max_tokens', sa.Integer, default=2000),
        sa.Column('system_prompt', sa.Text),
        sa.Column('fallback_provider', sa.String(50)),
        sa.Column('fallback_model', sa.String(100)),
        sa.Column('cost_limit_daily', sa.Float),
        sa.Column('routing_strategy', sa.String(50)),  # cost, performance, balanced
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()'))
    )
    
    # Observability Log
    op.create_table(
        'observability_log',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('conversation_id', sa.String(36), sa.ForeignKey('conversation.id')),
        sa.Column('message_id', sa.String(36), sa.ForeignKey('message.id')),
        sa.Column('event_type', sa.String(50)),
        sa.Column('intent_detected', sa.String(100)),
        sa.Column('model_selected', sa.String(100)),
        sa.Column('model_reason', sa.String(255)),
        sa.Column('tools_considered', postgresql.JSON, default=[]),
        sa.Column('tool_selected', sa.String(100)),
        sa.Column('confidence_score', sa.Float),
        sa.Column('context_retrieved', postgresql.JSON),
        sa.Column('decision_path', postgresql.JSON),
        sa.Column('latency_ms', sa.Integer),
        sa.Column('cost_usd', sa.Float),
        sa.Column('metadata', postgresql.JSON),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()'))
    )
    
    # Usage Metrics
    op.create_table(
        'usage_metrics',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('date', sa.Date),
        sa.Column('total_requests', sa.Integer),
        sa.Column('total_tokens', sa.Float),
        sa.Column('total_cost_usd', sa.Float),
        sa.Column('avg_latency_ms', sa.Float),
        sa.Column('tool_executions', sa.Integer),
        sa.Column('knowledge_queries', sa.Integer),
        sa.Column('unique_users', sa.Integer),
        sa.Column('error_count', sa.Integer),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()'))
    )
    
    # User Sessions
    op.create_table(
        'user_session',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(100)),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('device_type', sa.String(50)),
        sa.Column('os_info', sa.String(100)),
        sa.Column('browser_info', sa.String(100)),
        sa.Column('country', sa.String(100)),
        sa.Column('city', sa.String(100)),
        sa.Column('started_at', sa.DateTime),
        sa.Column('last_seen', sa.DateTime),
        sa.Column('message_count', sa.Integer),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()'))
    )
    
    # Create indexes
    op.create_index('ix_user_email', 'user', ['email'])
    op.create_index('ix_conversation_user', 'conversation', ['user_id'])
    op.create_index('ix_conversation_session', 'conversation', ['session_id'])
    op.create_index('ix_message_conversation', 'message', ['conversation_id'])
    op.create_index('ix_memory_user', 'memory', ['user_id'])
    op.create_index('ix_observability_log_conversation', 'observability_log', ['conversation_id'])


def downgrade() -> None:
    # Drop all tables
    tables = [
        'user_session', 'usage_metrics', 'observability_log', 'ai_config',
        'tool_execution', 'tool', 'memory_retention_policy', 'memory',
        'knowledge_chunk', 'knowledge_source', 'message', 'conversation',
        'api_key', 'user'
    ]
    
    for table in tables:
        op.drop_table(table, if_exists=True)
    
    op.execute('DROP EXTENSION IF EXISTS vector')
