"""add 4 prospect fields (owner_name, employee_count, revenue_estimate, closing_probability)

Sprint 1 (T5 v3) / brief: 4 data fields per prospect that were
missing from the previous schema. The brief specifies a 12-field
data model; the 4 new ones close the gap to 13/13 (we count
size_estimate as separate from employee_count — see prospect.py).

Revision ID: b8c2f5a3e1d2
Revises: 32f1769c14bb
Create Date: 2026-06-14 17:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8c2f5a3e1d2"
down_revision: Union[str, None] = "32f1769c14bb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "prospects",
        sa.Column("owner_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "prospects",
        sa.Column("employee_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "prospects",
        sa.Column("revenue_estimate", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "prospects",
        sa.Column("closing_probability", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("prospects", "closing_probability")
    op.drop_column("prospects", "revenue_estimate")
    op.drop_column("prospects", "employee_count")
    op.drop_column("prospects", "owner_name")
