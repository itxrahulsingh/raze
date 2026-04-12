"""
RAZE Enterprise AI OS – Auth Schemas

Covers login, token issuance, user management, and API key CRUD.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.models.user import UserRole


# ─── Shared helpers ───────────────────────────────────────────────────────────


class _TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime


# ─── Login ────────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    """Credentials submitted to POST /auth/login."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=1, max_length=256)
    remember_me: bool = Field(default=False)

    model_config = {"str_strip_whitespace": True}


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


# ─── Token ────────────────────────────────────────────────────────────────────


class TokenResponse(BaseModel):
    """Returned by both /auth/login and /auth/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token lifetime in seconds")


# ─── User ────────────────────────────────────────────────────────────────────


class UserCreate(BaseModel):
    """Body for POST /auth/register (or admin POST /users)."""

    email: EmailStr
    username: str = Field(
        ...,
        min_length=3,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_\-\.]+$",
        description="Alphanumeric username (underscores, hyphens, dots allowed)",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=256,
        description="At least 8 characters",
    )
    full_name: str | None = Field(default=None, max_length=256)
    role: UserRole = Field(default=UserRole.viewer)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    model_config = {"str_strip_whitespace": True}


class UserUpdate(BaseModel):
    """Body for PATCH /users/{id} – all fields optional."""

    email: EmailStr | None = None
    username: str | None = Field(
        default=None, min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_\-\.]+$"
    )
    full_name: str | None = Field(default=None, max_length=256)
    role: UserRole | None = None
    is_active: bool | None = None
    user_metadata: dict[str, Any] | None = None

    model_config = {"str_strip_whitespace": True}


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=256)
    new_password: str = Field(..., min_length=8, max_length=256)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserResponse(_TimestampMixin):
    """Safe user representation – no password hash exposed."""

    id: uuid.UUID
    email: EmailStr
    username: str
    full_name: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    last_login: datetime | None
    user_metadata: dict[str, Any] | None

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int


# ─── API Key ──────────────────────────────────────────────────────────────────


class APIKeyCreate(BaseModel):
    """Body for POST /api-keys."""

    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=1024)
    permissions: list[str] = Field(
        default_factory=list,
        description=(
            "Scopes granted to this key, e.g. ['chat', 'knowledge:read']. "
            "Empty list = all permissions of the issuing user."
        ),
    )
    rate_limit: int | None = Field(
        default=None,
        ge=1,
        le=10000,
        description="Requests per minute; NULL = inherit user default",
    )
    expires_at: datetime | None = Field(
        default=None, description="Optional hard expiry timestamp (UTC)"
    )

    model_config = {"str_strip_whitespace": True}


class APIKeyCreateResponse(BaseModel):
    """
    Returned ONCE at creation time.  ``raw_key`` is shown only here;
    it is never retrievable afterwards.
    """

    id: uuid.UUID
    name: str
    raw_key: str = Field(..., description="Full API key – store it now, shown once")
    key_prefix: str
    permissions: list[str]
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class APIKeyResponse(_TimestampMixin):
    """Safe API key representation (no key hash / raw key)."""

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: str | None
    key_prefix: str
    permissions: list[str]
    rate_limit: int | None
    last_used: datetime | None
    total_requests: int
    is_active: bool
    expires_at: datetime | None

    model_config = {"from_attributes": True}


class APIKeyListResponse(BaseModel):
    items: list[APIKeyResponse]
    total: int
