"""Add AppSettings table for centralized configuration.

Revision ID: 002
Revises: 001
Create Date: 2026-04-19 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create app_settings table."""
    op.create_table(
        "app_settings",
        sa.Column("id", sa.String(36), nullable=False, default="singleton"),
        sa.Column("brand_name", sa.String(255), nullable=False, server_default="RAZE"),
        sa.Column("brand_color", sa.String(50), nullable=False, server_default="#3B82F6"),
        sa.Column("logo_url", sa.String(512), nullable=True),
        sa.Column("favicon_url", sa.String(512), nullable=True),
        sa.Column("page_title", sa.String(255), nullable=False, server_default="RAZE AI - Enterprise Chat"),
        sa.Column("page_description", sa.String(512), nullable=False, server_default="Enterprise AI Assistant"),
        sa.Column("copyright_text", sa.String(255), nullable=False, server_default="© 2026 RAZE. All rights reserved."),
        sa.Column("chat_welcome_message", sa.Text, nullable=False, server_default="Hello! I'm RAZE, your AI assistant. How can I help?"),
        sa.Column("chat_placeholder", sa.String(255), nullable=False, server_default="Ask me anything..."),
        sa.Column("enable_suggestions", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("chat_suggestions", sa.Text, nullable=False, server_default='["What can you do?", "Tell me about yourself", "Help with this task"]'),
        sa.Column("theme_mode", sa.String(20), nullable=False, server_default="dark"),
        sa.Column("accent_color", sa.String(50), nullable=False, server_default="#3B82F6"),
        sa.Column("sdk_api_endpoint", sa.String(512), nullable=False, server_default="http://localhost/api/v1"),
        sa.Column("sdk_websocket_endpoint", sa.String(512), nullable=True),
        sa.Column("sdk_auth_type", sa.String(50), nullable=False, server_default="bearer"),
        sa.Column("enable_knowledge_base", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("enable_web_search", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("enable_memory", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("enable_voice", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("require_source_approval", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("auto_approve_sources", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("max_file_size_mb", sa.Integer, nullable=False, server_default="100"),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop app_settings table."""
    op.drop_table("app_settings")
