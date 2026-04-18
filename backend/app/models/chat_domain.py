"""Chat SDK Domain and API Key Management."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DomainStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    suspended = "suspended"
    rejected = "rejected"


class ChatDomain(Base):
    """Whitelisted domain for chat SDK embedding."""

    __tablename__ = "chat_domains"

    domain: Mapped[str] = mapped_column(String(256), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=DomainStatus.pending.value,
        index=True,
    )
    api_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Configuration
    allow_file_upload: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    show_knowledge_sources: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    custom_branding: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    widget_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#3B82F6")

    # Tracking
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True, index=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    suspended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_used: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_chat_domains_status_active", "status", "is_active"),
    )
