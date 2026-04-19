"""Add industry configuration and SDK branding fields.

Revision ID: 004
Revises: 003
Create Date: 2026-04-19 16:00:00.000000

This migration adds:
- Industry-wide configuration to app_settings (industry name, topics, tone, system prompt)
- Per-domain branding to chat_domains (bot name, welcome message)
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add industry and SDK branding fields."""
    # Add to app_settings table
    op.add_column(
        "app_settings",
        sa.Column(
            "industry_name",
            sa.String(100),
            nullable=True,
            comment="Industry/vertical: Travel, Healthcare, Legal, etc."
        ),
    )
    op.add_column(
        "app_settings",
        sa.Column(
            "industry_topics",
            sa.Text(),
            nullable=True,
            comment="JSON array of allowed topic strings for industry restriction"
        ),
    )
    op.add_column(
        "app_settings",
        sa.Column(
            "industry_tone",
            sa.String(50),
            nullable=False,
            server_default="friendly",
            comment="Tone: professional/friendly/casual/formal"
        ),
    )
    op.add_column(
        "app_settings",
        sa.Column(
            "industry_restriction_mode",
            sa.String(20),
            nullable=False,
            server_default="strict",
            comment="Restriction mode: strict (refuse off-topic) or soft (prefer on-topic)"
        ),
    )
    op.add_column(
        "app_settings",
        sa.Column(
            "industry_system_prompt",
            sa.Text(),
            nullable=True,
            comment="System prompt for the AI assistant (auto-generated or manual override)"
        ),
    )
    op.add_column(
        "app_settings",
        sa.Column(
            "company_name",
            sa.String(255),
            nullable=True,
            comment="Company/organization name for personalization"
        ),
    )

    # Add to chat_domains table
    op.add_column(
        "chat_domains",
        sa.Column(
            "bot_name",
            sa.String(128),
            nullable=False,
            server_default="Assistant",
            comment="Custom bot name for this domain"
        ),
    )
    op.add_column(
        "chat_domains",
        sa.Column(
            "welcome_message",
            sa.Text(),
            nullable=True,
            comment="Custom welcome message for this domain"
        ),
    )


def downgrade() -> None:
    """Remove industry and SDK branding fields."""
    # From app_settings
    op.drop_column("app_settings", "company_name")
    op.drop_column("app_settings", "industry_system_prompt")
    op.drop_column("app_settings", "industry_restriction_mode")
    op.drop_column("app_settings", "industry_tone")
    op.drop_column("app_settings", "industry_topics")
    op.drop_column("app_settings", "industry_name")

    # From chat_domains
    op.drop_column("chat_domains", "welcome_message")
    op.drop_column("chat_domains", "bot_name")
