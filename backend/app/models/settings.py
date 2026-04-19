"""Application settings and configuration model."""
from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AppConfig(Base):
    """Centralized application configuration - stored once, cached forever."""
    __tablename__ = "app_config"

    key: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    value: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), index=True, default="system")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AppConfig key={self.key}>"


class AppSettings(Base):
    """All application settings in one place."""
    __tablename__ = "app_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="singleton")

    # Branding
    brand_name: Mapped[str] = mapped_column(String(255), default="RAZE")
    brand_color: Mapped[str] = mapped_column(String(50), default="#3B82F6")
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Page Configuration
    page_title: Mapped[str] = mapped_column(String(255), default="RAZE AI - Enterprise Chat")
    page_description: Mapped[str] = mapped_column(String(512), default="Enterprise AI Assistant")
    copyright_text: Mapped[str] = mapped_column(String(255), default="© 2026 RAZE. All rights reserved.")

    # Chat Configuration
    chat_welcome_message: Mapped[str] = mapped_column(Text, default="Hello! I'm RAZE, your AI assistant. How can I help?")
    chat_placeholder: Mapped[str] = mapped_column(String(255), default="Ask me anything...")
    enable_suggestions: Mapped[bool] = mapped_column(Boolean, default=True)

    # Chat Suggestions/Chips
    chat_suggestions: Mapped[str] = mapped_column(Text, default='["What can you do?", "Tell me about yourself", "Help with this task"]')

    # Theme
    theme_mode: Mapped[str] = mapped_column(String(20), default="dark")  # dark, light, auto
    accent_color: Mapped[str] = mapped_column(String(50), default="#3B82F6")

    # SDK Configuration
    sdk_api_endpoint: Mapped[str] = mapped_column(String(512), default="http://localhost/api/v1")
    sdk_websocket_endpoint: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sdk_auth_type: Mapped[str] = mapped_column(String(50), default="bearer")  # bearer, api-key

    # Feature Flags
    enable_knowledge_base: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_web_search: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_memory: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_voice: Mapped[bool] = mapped_column(Boolean, default=False)

    # Knowledge Base
    require_source_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_approve_sources: Mapped[bool] = mapped_column(Boolean, default=True)
    max_file_size_mb: Mapped[int] = mapped_column(default=100)

    # Timestamp
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AppSettings {self.brand_name}>"
