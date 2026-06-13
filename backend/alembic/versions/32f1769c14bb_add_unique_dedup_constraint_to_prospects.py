"""add unique dedup constraint to prospects

Revision ID: 32f1769c14bb
Revises: 241b0a81cd44
Create Date: 2026-06-13 13:43:31.120365

Adds a unique partial index on (LOWER(company_name), LOWER(COALESCE(location_city, chr(39) || chr(39))))
so that INSERT ... ON CONFLICT DO NOTHING works for dedup in the
scout pipeline. The index is on a function expression to make it
case-insensitive.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "32f1769c14bb"
down_revision: Union[str, None] = "241b0a81cd44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_prospects_company_city "
        "ON prospects (LOWER(company_name), LOWER(COALESCE(location_city, chr(39) || chr(39)))) "
        "WHERE deleted_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_prospects_company_city")
