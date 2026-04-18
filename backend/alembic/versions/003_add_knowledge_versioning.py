"""Add knowledge chunk versioning for full audit trail and rollback.

Adds:
- KnowledgeChunkVersion table for immutable version history
- Indexes on chunk_id, version and changed_by
- Enables full rollback and change attribution
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_chunk_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("old_content", sa.Text(), nullable=True),
        sa.Column("new_content", sa.Text(), nullable=False),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("change_reason", sa.String(512), nullable=True),
        sa.ForeignKeyConstraint(["chunk_id"], ["knowledge_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for efficient querying
    op.create_index(
        "ix_knowledge_chunk_versions_chunk_version",
        "knowledge_chunk_versions",
        ["chunk_id", "version"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_chunk_versions_changed_by",
        "knowledge_chunk_versions",
        ["changed_by"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_chunk_versions_created",
        "knowledge_chunk_versions",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunk_versions_created", table_name="knowledge_chunk_versions")
    op.drop_index("ix_knowledge_chunk_versions_changed_by", table_name="knowledge_chunk_versions")
    op.drop_index("ix_knowledge_chunk_versions_chunk_version", table_name="knowledge_chunk_versions")
    op.drop_table("knowledge_chunk_versions")
