"""Initial schema migration - mark version only.

Tables are created by the application startup using ORM metadata.
This migration is a placeholder to initialize the alembic_version table.
"""

from __future__ import annotations

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tables are created by app startup; this migration just marks the version
    pass


def downgrade() -> None:
    # Downgrade is a no-op for the initial migration
    pass
