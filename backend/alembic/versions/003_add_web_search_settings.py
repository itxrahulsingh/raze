"""Add web search configuration to AppSettings.

Revision ID: 003
Revises: 002
Create Date: 2026-04-19 12:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add web search fields to app_settings table."""
    op.add_column(
        "app_settings",
        sa.Column(
            "web_search_engine",
            sa.String(50),
            nullable=False,
            server_default="duckduckgo",
            comment="Web search engine: duckduckgo (free, no key needed)"
        ),
    )
    op.add_column(
        "app_settings",
        sa.Column(
            "web_search_max_results",
            sa.Integer,
            nullable=False,
            server_default="5",
            comment="Maximum web search results per query"
        ),
    )
    op.add_column(
        "app_settings",
        sa.Column(
            "include_web_search_in_chat",
            sa.Boolean,
            nullable=False,
            server_default="true",
            comment="Include web search results in chat responses"
        ),
    )


def downgrade() -> None:
    """Remove web search fields from app_settings table."""
    op.drop_column("app_settings", "web_search_engine")
    op.drop_column("app_settings", "web_search_max_results")
    op.drop_column("app_settings", "include_web_search_in_chat")
