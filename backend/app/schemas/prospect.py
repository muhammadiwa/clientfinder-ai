"""
Prospect Pydantic schemas
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ProspectBase(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    industry: str | None = Field(None, max_length=100)
    size_estimate: str | None = Field(None, max_length=50)
    location_city: str | None = Field(None, max_length=100)
    location_province: str | None = Field(None, max_length=100)
    website: str | None = Field(None, max_length=500)
    phone: str | None = Field(None, max_length=50)
    email: EmailStr | None = None
    social_links: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None
    # Sprint 1 (T5 v3) / brief
    owner_name: str | None = Field(None, max_length=255)
    employee_count: int | None = Field(None, ge=0)
    revenue_estimate: str | None = Field(None, max_length=100)
    closing_probability: int | None = Field(None, ge=0, le=100)


class ProspectCreate(ProspectBase):
    """Schema for creating a new prospect."""
    source: str = Field(..., min_length=1, max_length=50)
    source_query: str | None = None
    source_url: str | None = Field(None, max_length=1000)
    raw_data: dict[str, Any] = Field(default_factory=dict)


class ProspectUpdate(BaseModel):
    """Schema for updating prospect fields (all optional)."""
    company_name: str | None = Field(None, min_length=1, max_length=255)
    industry: str | None = Field(None, max_length=100)
    size_estimate: str | None = Field(None, max_length=50)
    location_city: str | None = Field(None, max_length=100)
    location_province: str | None = Field(None, max_length=100)
    website: str | None = Field(None, max_length=500)
    phone: str | None = Field(None, max_length=50)
    email: EmailStr | None = None
    social_links: dict[str, Any] | None = None
    description: str | None = None
    status: str | None = None
    quality_grade: str | None = None
    score_total: int | None = None
    # Sprint 1 (T5 v3) / brief
    owner_name: str | None = Field(None, max_length=255)
    employee_count: int | None = Field(None, ge=0)
    revenue_estimate: str | None = Field(None, max_length=100)
    closing_probability: int | None = Field(None, ge=0, le=100)


class ProspectOut(ProspectBase):
    """Public prospect info."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    source_query: str | None
    source_url: str | None
    raw_data: dict[str, Any]
    status: str
    quality_grade: str | None
    score_total: int | None
    owner_id: UUID | None
    last_contacted_at: datetime | None
    discovered_at: datetime
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    # Sprint 3B
    tier: str | None
    tier_confidence: float | None
    industry_specific: str | None


class ProspectListResponse(BaseModel):
    """Paginated list response."""
    items: list[ProspectOut]
    total: int
    page: int
    per_page: int
    pages: int
