"""
System models — settings, scraping jobs
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Setting(Base, TimestampMixin):
    """Key-value configuration. Key is the primary key (string)."""
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Setting {self.key}>"


class ScrapingJob(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "scraping_jobs"

    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # google, maps, twitter, threads
    query: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # {keywords: [], location: '', max_results: 50}
    status: Mapped[str] = mapped_column(
        String(30), default="pending", nullable=False, index=True
    )
    # pending, running, completed, failed
    prospects_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<ScrapingJob {self.source} {self.status}>"
