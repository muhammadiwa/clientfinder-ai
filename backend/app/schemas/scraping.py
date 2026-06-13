"""
Pydantic schemas for Scout module (T4)
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ScrapingSource = Literal["google", "maps", "twitter", "threads"]
ScrapingStatus = Literal["pending", "running", "completed", "failed"]


class ScrapingQuery(BaseModel):
    """Schema for the JSONB `query` column on ScrapingJob.

    Each scraper reads what it needs; unknown fields are ignored.
    """

    keywords: str = Field(..., min_length=1, max_length=500)
    location: str | None = Field(None, max_length=200)
    max_results: int = Field(20, ge=1, le=100)


class ScrapingJobCreate(BaseModel):
    source: ScrapingSource
    keywords: str = Field(..., min_length=1, max_length=500)
    location: str | None = Field(None, max_length=200)
    max_results: int = Field(20, ge=1, le=100)


class ScrapingJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: ScrapingSource
    query: dict  # ScrapingQuery, but kept as dict for forward-compat
    status: ScrapingStatus
    prospects_found: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class ScrapingJobListResponse(BaseModel):
    items: list[ScrapingJobOut]
    total: int


class ScrapingPresetOut(BaseModel):
    """Saved query preset (named shortcut)."""

    id: str  # string for curated defaults (not UUIDs in v1)
    name: str
    source: ScrapingSource
    query: ScrapingQuery
