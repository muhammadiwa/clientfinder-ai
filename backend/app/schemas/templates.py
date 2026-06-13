"""
Pydantic schemas for Templates (T6 Group 3)
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

TemplateChannel = Literal["email", "whatsapp", "threads"]


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    channel: TemplateChannel
    category: str | None = Field(None, max_length=50)
    subject: str | None = Field(None, max_length=500)
    body: str = Field(..., min_length=1, max_length=20000)
    variables: list[str] = Field(default_factory=list)
    is_active: bool = True


class TemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    category: str | None = Field(None, max_length=50)
    subject: str | None = Field(None, max_length=500)
    body: str | None = Field(None, min_length=1, max_length=20000)
    variables: list[str] | None = None
    is_active: bool | None = None


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    channel: TemplateChannel
    category: str | None
    subject: str | None
    body: str
    variables: list[str]
    is_active: bool
    usage_count: int
    created_at: datetime | None
    updated_at: datetime | None


class TemplateListResponse(BaseModel):
    items: list[TemplateOut]
    total: int
