"""
RAZE Enterprise AI OS – Input Validation & Sanitization

Comprehensive validation for:
  - File uploads (size, type, content)
  - Knowledge inputs (content, duplicates)
  - Memory inputs (size, format)
  - API inputs (schema, constraints)
"""

from __future__ import annotations

import hashlib
import mimetypes
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class FileValidator:
    """Validate file uploads."""

    ALLOWED_MIME_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/html",
        "text/csv",
        "application/json",
        "text/markdown",
    }

    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB default

    @classmethod
    def validate_upload(
        cls,
        file_bytes: bytes,
        mime_type: str | None,
        filename: str,
        max_size_mb: int | None = None,
    ) -> None:
        """
        Validate a file upload.

        Args:
            file_bytes: File content
            mime_type: MIME type (e.g., 'application/pdf')
            filename: Original filename
            max_size_mb: Max size in MB (default 50)

        Raises:
            ValidationError: If validation fails
        """
        max_bytes = (max_size_mb or 50) * 1024 * 1024

        # Size check
        if len(file_bytes) == 0:
            raise ValidationError("File is empty")
        if len(file_bytes) > max_bytes:
            raise ValidationError(
                f"File too large: {len(file_bytes)} bytes (max {max_bytes})"
            )

        # MIME type check
        if mime_type and mime_type not in cls.ALLOWED_MIME_TYPES:
            raise ValidationError(f"MIME type not allowed: {mime_type}")

        # Infer from filename if needed
        if not mime_type:
            inferred, _ = mimetypes.guess_type(filename)
            if inferred and inferred not in cls.ALLOWED_MIME_TYPES:
                raise ValidationError(f"File type not allowed: {filename}")

        # Basic content checks
        if len(file_bytes) < 10:
            raise ValidationError("File too small to be valid")

        logger.info("file_validation_passed", filename=filename, size=len(file_bytes))

    @staticmethod
    def compute_hash(data: bytes) -> str:
        """Compute SHA-256 hash of file."""
        return hashlib.sha256(data).hexdigest()


class KnowledgeValidator:
    """Validate knowledge inputs."""

    MIN_CONTENT_LENGTH = 10
    MAX_CONTENT_LENGTH = 100_000  # Chunks should be reasonably sized

    @classmethod
    def validate_chunk_content(cls, content: str) -> None:
        """
        Validate knowledge chunk content.

        Args:
            content: Chunk text

        Raises:
            ValidationError: If validation fails
        """
        if not content or not content.strip():
            raise ValidationError("Content cannot be empty")

        if len(content) < cls.MIN_CONTENT_LENGTH:
            raise ValidationError(f"Content too short (min {cls.MIN_CONTENT_LENGTH} chars)")

        if len(content) > cls.MAX_CONTENT_LENGTH:
            raise ValidationError(f"Content too long (max {cls.MAX_CONTENT_LENGTH} chars)")

    @classmethod
    def validate_source_metadata(cls, metadata: dict[str, Any]) -> None:
        """
        Validate knowledge source metadata.

        Args:
            metadata: Source metadata dict

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(metadata, dict):
            raise ValidationError("Metadata must be a dictionary")

        if len(metadata) > 100:
            raise ValidationError("Metadata too large (max 100 keys)")


class MemoryValidator:
    """Validate memory inputs."""

    MIN_CONTENT_LENGTH = 5
    MAX_CONTENT_LENGTH = 10_000

    @classmethod
    def validate_memory_content(cls, content: str) -> None:
        """
        Validate memory content.

        Args:
            content: Memory text

        Raises:
            ValidationError: If validation fails
        """
        if not content or not content.strip():
            raise ValidationError("Memory content cannot be empty")

        if len(content) < cls.MIN_CONTENT_LENGTH:
            raise ValidationError(f"Memory too short (min {cls.MIN_CONTENT_LENGTH} chars)")

        if len(content) > cls.MAX_CONTENT_LENGTH:
            raise ValidationError(f"Memory too long (max {cls.MAX_CONTENT_LENGTH} chars)")

    @classmethod
    def validate_importance_score(cls, score: float) -> None:
        """
        Validate importance score.

        Args:
            score: Score (0.0 to 1.0)

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(score, (int, float)):
            raise ValidationError("Importance score must be a number")

        if score < 0.0 or score > 1.0:
            raise ValidationError("Importance score must be between 0.0 and 1.0")


class ToolValidator:
    """Validate tool inputs."""

    @classmethod
    def validate_tool_schema(cls, schema: dict[str, Any]) -> None:
        """
        Validate tool function schema.

        Args:
            schema: OpenAI function schema

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(schema, dict):
            raise ValidationError("Schema must be a dictionary")

        # Basic OpenAI schema validation
        if "type" not in schema or schema["type"] != "object":
            raise ValidationError("Schema type must be 'object'")

        if "properties" not in schema:
            raise ValidationError("Schema must have 'properties'")

    @classmethod
    def validate_tool_input(cls, input_data: dict[str, Any], schema: dict[str, Any]) -> None:
        """
        Validate tool input against schema.

        Args:
            input_data: Input to validate
            schema: Expected schema

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(input_data, dict):
            raise ValidationError("Tool input must be a dictionary")

        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in input_data:
                raise ValidationError(f"Required field missing: {field}")


class URLValidator:
    """Validate URLs."""

    ALLOWED_SCHEMES = ("http", "https")

    @classmethod
    def validate_url(cls, url: str) -> None:
        """
        Validate a URL.

        Args:
            url: URL to validate

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(url, str):
            raise ValidationError("URL must be a string")

        if not url.strip():
            raise ValidationError("URL cannot be empty")

        if len(url) > 2048:
            raise ValidationError("URL too long")

        # Basic scheme check
        if "://" not in url:
            raise ValidationError("URL must include scheme (http/https)")

        scheme = url.split("://", 1)[0].lower()
        if scheme not in cls.ALLOWED_SCHEMES:
            raise ValidationError(f"Scheme not allowed: {scheme}")
