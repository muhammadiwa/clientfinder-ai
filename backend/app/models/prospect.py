"""
Prospect models — main business entities and their associated signals
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Prospect(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "prospects"

    # Basic info
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    size_estimate: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # 1-10, 11-50, 51-200, 201-500, 500+

    location_city: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    location_province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    social_links: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Source tracking
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # google, maps, twitter, threads, manual, import
    source_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    raw_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Pipeline status
    status: Mapped[str] = mapped_column(
        String(50), default="new", nullable=False, index=True
    )
    # new → enriching → scored → approved → contacted → replied →
    # won | lost | archived

    quality_grade: Mapped[str | None] = mapped_column(String(5), nullable=True, index=True)
    # A, B, C, D

    score_total: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    owner_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    last_contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    signals: Mapped[list["Signal"]] = relationship(
        "Signal", back_populates="prospect", cascade="all, delete-orphan"
    )
    tech_stack: Mapped["TechStack | None"] = relationship(
        "TechStack", back_populates="prospect", uselist=False, cascade="all, delete-orphan"
    )
    pain_points: Mapped[list["PainPoint"]] = relationship(
        "PainPoint", back_populates="prospect", cascade="all, delete-orphan"
    )
    lead_score: Mapped["LeadScore | None"] = relationship(
        "LeadScore", back_populates="prospect", uselist=False, cascade="all, delete-orphan"
    )
    hooks: Mapped[list["Hook"]] = relationship(
        "Hook", back_populates="prospect", cascade="all, delete-orphan"
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="prospect", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_prospects_status_score", "status", "score_total"),
    )

    def __repr__(self) -> str:
        return f"<Prospect {self.company_name} ({self.status})>"


class Signal(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "signals"

    prospect_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("prospects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    signal_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # job_posting, funding, complaint, tech_audit, hiring, expansion
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight: Mapped[float] = mapped_column(Numeric(3, 2), default=0.5, nullable=False)
    extra_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    prospect: Mapped["Prospect"] = relationship("Prospect", back_populates="signals")

    def __repr__(self) -> str:
        return f"<Signal {self.signal_type} weight={self.weight}>"


class TechStack(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "tech_stacks"

    prospect_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("prospects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    cms: Mapped[str | None] = mapped_column(String(100), nullable=True)
    framework: Mapped[str | None] = mapped_column(String(100), nullable=True)
    programming_languages: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    hosting_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    has_ssl: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ssl_issuer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mobile_friendly: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    page_speed_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    technologies: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    security_headers: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    issues: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    raw_html_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    prospect: Mapped["Prospect"] = relationship("Prospect", back_populates="tech_stack")

    def __repr__(self) -> str:
        return f"<TechStack {self.cms}/{self.framework}>"


class PainPoint(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "pain_points"

    prospect_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("prospects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # operational, customer, growth, technical
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # low, medium, high
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    evidence_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    prospect: Mapped["Prospect"] = relationship("Prospect", back_populates="pain_points")

    def __repr__(self) -> str:
        return f"<PainPoint {self.category}/{self.severity}>"
