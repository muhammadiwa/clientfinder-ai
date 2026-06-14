"""Sprint 3B — persist tier + industry_specific

Adds 3 columns to prospects:
- tier: varchar(20), nullable (SMB/Mid/Enterprise/Unknown)
- tier_confidence: float, nullable
- industry_specific: varchar(255), nullable

These are populated by:
1. POST /api/v1/prospects/{id}/classify (manual)
2. Auto-classify during enrich (orchestrator hook)

The existing prospectus fields stay backward compatible
(null until classification runs).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7c3f8a1d2b4e"
down_revision = "b8c2f5a3e1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "prospects",
        sa.Column("tier", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "prospects",
        sa.Column("tier_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "prospects",
        sa.Column("industry_specific", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_prospects_tier",
        "prospects",
        ["tier"],
    )


def downgrade() -> None:
    op.drop_index("ix_prospects_tier", table_name="prospects")
    op.drop_column("prospects", "industry_specific")
    op.drop_column("prospects", "tier_confidence")
    op.drop_column("prospects", "tier")
