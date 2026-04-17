"""Initial schema based on current SQLAlchemy models.

This migration intentionally uses the ORM metadata as the schema source of truth
to avoid drift between model definitions and hand-written table declarations.
"""

from __future__ import annotations

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Required extensions for UUID defaults and pgvector columns/indexes.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Import metadata only at runtime inside migration context.
    from app.database import Base
    from app.models import (  # noqa: F401 - imported for side effects (table registration)
        ai_config,
        analytics,
        conversation,
        knowledge,
        memory,
        tool,
        user,
    )

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    from app.database import Base
    from app.models import (  # noqa: F401 - imported for side effects (table registration)
        ai_config,
        analytics,
        conversation,
        knowledge,
        memory,
        tool,
        user,
    )

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
