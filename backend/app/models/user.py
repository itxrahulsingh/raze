"""
RAZE Enterprise AI OS – User & API Key Models
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.memory import Memory


# ─── Enumerations ─────────────────────────────────────────────────────────────


class UserRole(str, Enum):
    superadmin = "superadmin"
    admin = "admin"
    viewer = "viewer"


# ─── User ─────────────────────────────────────────────────────────────────────


class User(Base):
    """
    Platform user.  Passwords are stored as bcrypt hashes only.
    The ``metadata`` column holds arbitrary per-user JSON (timezone,
    preferences, avatar URL, etc.).
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    role: Mapped[str] = mapped_column(
        String(32), nullable=False, default=UserRole.viewer.value, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    user_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="user", lazy="select"
    )
    memories: Mapped[list["Memory"]] = relationship(
        "Memory", back_populates="user", lazy="select"
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_users_role_active", "role", "is_active"),
        Index("ix_users_email_active", "email", "is_active"),
    )


# ─── API Key ──────────────────────────────────────────────────────────────────


class APIKey(Base):
    """
    Hashed API keys issued to users for programmatic / SDK access.

    ``key_hash``   – bcrypt/SHA-256 hash of the raw key (never stored plain).
    ``key_prefix`` – first 8 chars of the raw key (shown in the UI for identification).
    ``permissions`` – JSON list of permission strings, e.g. ["chat", "knowledge:read"].
    ``rate_limit``  – requests per minute; NULL means inherit the user's default.
    """

    __tablename__ = "api_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    permissions: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    rate_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_used: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_requests: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_api_keys_user_active", "user_id", "is_active"),
        Index("ix_api_keys_prefix", "key_prefix"),
    )
