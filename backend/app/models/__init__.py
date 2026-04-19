"""
RAZE Enterprise AI OS – ORM Model Registry

Importing this package registers every model class with SQLAlchemy's
metadata so that ``Base.metadata.create_all()`` and Alembic autogenerate
both discover all tables automatically.

Usage::

    from app.models import *          # load all models
    from app.models.user import User  # import a specific model
"""

from app.models.ai_config import AIConfig, LLMProvider, RoutingStrategy
from app.models.analytics import ObservabilityLog, UsageMetrics, UserSession
from app.models.conversation import Conversation, ConversationStatus, Message, MessageRole
from app.models.knowledge import (
    KnowledgeChunk,
    KnowledgeSource,
    KnowledgeSourceMode,
    KnowledgeSourceStatus,
    KnowledgeSourceType,
)
from app.models.knowledge_version import KnowledgeChunkVersion
from app.models.memory import Memory, MemoryRetentionPolicy, MemoryType
from app.models.settings import AppSettings, AppConfig
from app.models.system import AuditLog, SystemConfig
from app.models.tool import Tool, ToolExecution, ToolExecutionStatus, ToolType
from app.models.user import APIKey, User, UserRole

__all__ = [
    # User & Auth
    "User",
    "UserRole",
    "APIKey",
    # Conversation
    "Conversation",
    "ConversationStatus",
    "Message",
    "MessageRole",
    # Knowledge
    "KnowledgeSource",
    "KnowledgeSourceType",
    "KnowledgeSourceStatus",
    "KnowledgeSourceMode",
    "KnowledgeChunk",
    "KnowledgeChunkVersion",
    # Memory
    "Memory",
    "MemoryType",
    "MemoryRetentionPolicy",
    # Settings
    "AppSettings",
    "AppConfig",
    # Tool
    "Tool",
    "ToolType",
    "ToolExecution",
    "ToolExecutionStatus",
    # AI Config
    "AIConfig",
    "LLMProvider",
    "RoutingStrategy",
    # System
    "SystemConfig",
    "AuditLog",
    # Analytics
    "ObservabilityLog",
    "UsageMetrics",
    "UserSession",
]
