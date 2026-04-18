"""
RAZE Enterprise AI OS – System Configuration & Audit Models
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# ─── System Configuration ─────────────────────────────────────────────────────


class SystemConfig(Base):
    """
    Global system configuration values.

    Used for feature flags, rate limits, cost controls, etc.
    Managed exclusively by superadmin role.

    ``key``   – configuration key (e.g., "feature:knowledge_versioning")
    ``value`` – configuration value (JSON)
    """

    __tablename__ = "system_configs"

    key: Mapped[str] = mapped_column(
        String(256), nullable=False, unique=True, index=True
    )
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_system_configs_key_active", "key", "is_active"),
    )


# ─── Audit Log ────────────────────────────────────────────────────────────────


class AuditLog(Base):
    """
    Immutable audit trail of all significant system changes.

    Tracks who did what, when, from where. Used for:
    - Compliance & regulatory requirements
    - Security incident investigation
    - Change tracking for knowledge, memory, users, etc.

    ``action``        – what happened (e.g., "create", "update", "delete", "approve")
    ``resource_type`` – what was modified (e.g., "knowledge_source", "user", "memory")
    ``resource_id``   – ID of the modified resource
    ``changes``       – JSON delta of what changed (old vs new)
    """

    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    resource_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    resource_id: Mapped[str] = mapped_column(
        String(256), nullable=False
    )
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_audit_logs_user_action", "user_id", "action"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_created", "created_at"),
    )
