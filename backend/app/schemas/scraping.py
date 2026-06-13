"""
Pydantic schemas for Scout module (T4)
"""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ScrapingSource = Literal["google", "maps", "twitter", "threads"]
ScrapingStatus = Literal["pending", "running", "completed", "failed"]


class ScrapingJobCreate(BaseModel):
    source: ScrapingSource
    keywords: str = Field(..., min_length=1, max_length=500)
    location: str | None = Field(None, max_length=200)
    max_results: int = Field(20, ge=1, le=100)


class ScrapingJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    query: dict[str, Any]
    status: str
    prospects_found: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class ScrapingJobListResponse(BaseModel):
    items: list[ScrapingJobOut]
    total: int


class ScrapingPresetOut(BaseModel):
    """For T4.5: saved query presets (named shortcuts)."""
    id: UUID
    name: str
    source: str
    query: dict[str, Any]
