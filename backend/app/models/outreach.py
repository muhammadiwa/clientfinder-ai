"""
Outreach models — messages, sequences, templates
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Message(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "messages"

    prospect_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("prospects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # email, whatsapp, threads
    direction: Mapped[str] = mapped_column(String(20), default="outbound", nullable=False)
    # outbound, inbound
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    # draft → pending_approval → approved → scheduled → sent → delivered →
    # opened → clicked → replied → bounced → failed

    # Timestamps for each stage
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Approval
    approved_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Error / external
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    extra_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    prospect: Mapped["Prospect"] = relationship("Prospect", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message {self.channel} {self.status}>"


class Sequence(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sequences"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    steps: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    # List of {order, channel, template_id, day_offset, conditions}
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    target_grade: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    target_source: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    target_industry: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    daily_send_cap: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    enrollments: Mapped[list["SequenceEnrollment"]] = relationship(
        "SequenceEnrollment", back_populates="sequence", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Sequence {self.name}>"


class SequenceEnrollment(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "sequence_enrollments"

    prospect_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("prospects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sequences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    # active, paused, completed, stopped
    next_action_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stopped_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    sequence: Mapped["Sequence"] = relationship("Sequence", back_populates="enrollments")

    def __repr__(self) -> str:
        return f"<SequenceEnrollment step={self.current_step} status={self.status}>"


class Template(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "templates"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # first_touch, follow_up, breakup, re_engage
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    # List of available placeholder names
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<Template {self.name} ({self.channel})>"
