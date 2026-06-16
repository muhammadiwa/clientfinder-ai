"""Sprint 4 PR 2 (scout-run-fk-maps-full-data): add scout_run_id FK + GIN index on raw_data

Adds:
- scout_run_id: UUID, nullable, FK to scraping_jobs.id, indexed
- GIN index on raw_data (JSONB) for future "search inside raw_data" queries

The scout_run_id FK links each prospect back to the ScoutRun that
discovered it. The 4-perspective redesign (turn 60) chose Q1=C
(reuse prospects 1:1, no new ScoutResult table). The FK is the
operator's escape hatch: "which ScoutRun found this prospect?"

The GIN index enables future queries like:
    SELECT * FROM prospects WHERE raw_data @> '{"rating": "4.5"}';
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9b8f3c4e2a1d"
down_revision = "7c3f8a1d2b4e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "prospects",
        sa.Column("scout_run_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_prospects_scout_run_id",
        "prospects",
        "scraping_jobs",
        ["scout_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # NOTE: index is created in the migration (not the model) to
    # control the name and avoid a duplicate `ix_prospects_scout_run_id`
    # if SQLAlchemy create_all ever runs alongside alembic.
    op.create_index(
        "ix_prospects_scout_run_id",
        "prospects",
        ["scout_run_id"],
    )
    # GIN index for future "search inside raw_data" queries
    # (e.g. "show me all Maps prospects with rating >= 4.5").
    # IF NOT EXISTS makes the migration idempotent for re-runs.
    # NOTE for production scale: standard CREATE INDEX takes an
    # ACCESS EXCLUSIVE lock and blocks writes for the duration
    # of the build. For a large `prospects` table (>100k rows),
    # this migration should be replaced with a CONCURRENTLY variant
    # (cannot run inside a transaction — needs a separate non-
    # transactional migration). At v1 scale (hundreds of prospects)
    # the lock is negligible.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_prospects_raw_data_gin "
        "ON prospects USING gin (raw_data)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_prospects_raw_data_gin")
    op.drop_index("ix_prospects_scout_run_id", table_name="prospects")
    op.drop_constraint(
        "fk_prospects_scout_run_id", "prospects", type_="foreignkey"
    )
    op.drop_column("prospects", "scout_run_id")
