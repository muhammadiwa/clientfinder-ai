"""
Lead scoring and hook models
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin


class LeadScore(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "lead_scores"

    prospect_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("prospects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # Component scores (0-100)
    signal_strength: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    pain_severity: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    budget_indicator: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    solution_fit: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    timing_urgency: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    # total_score computed in DB (see migration)
    total_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, index=True)
    grade: Mapped[str] = mapped_column(String(5), nullable=False, index=True)
    # A, B, C, D
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    prospect: Mapped["Prospect"] = relationship("Prospect", back_populates="lead_score")

    def __repr__(self) -> str:
        return f"<LeadScore {self.grade} ({self.total_score})>"


class Hook(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "hooks"

    prospect_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("prospects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hook_text: Mapped[str] = mapped_column(Text, nullable=False)
    audit_finding: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_service: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float] = mapped_column(
        Numeric(3, 2), default=0.5, nullable=False
    )
    is_used: Mapped[bool] = mapped_column(
        String(10), default="false", nullable=False
    )  # bool in PG is simpler; use proper Boolean in PG migration

    prospect: Mapped["Prospect"] = relationship("Prospect", back_populates="hooks")

    def __repr__(self) -> str:
        return f"<Hook confidence={self.confidence}>"
