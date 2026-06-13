"""
Pydantic schemas for Sequences (T6 Group 3)
"""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SequenceChannel = Literal["email", "whatsapp", "threads"]


class SequenceStepSchema(BaseModel):
    order: int
    channel: SequenceChannel
    template_id: UUID | None = None
    day_offset: int = 0
    conditions: dict[str, Any] = Field(default_factory=dict)


class SequenceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    steps: list[SequenceStepSchema] = Field(..., min_length=1)
    is_active: bool = True
    target_grade: list[str] | None = None
    target_source: list[str] | None = None
    target_industry: list[str] | None = None
    daily_send_cap: int = Field(50, ge=1, le=1000)


class SequenceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    steps: list[SequenceStepSchema] | None = None
    is_active: bool | None = None
    target_grade: list[str] | None = None
    target_source: list[str] | None = None
    target_industry: list[str] | None = None
    daily_send_cap: int | None = Field(None, ge=1, le=1000)


class SequenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    steps: list[dict[str, Any]]
    is_active: bool
    target_grade: list[str] | None
    target_source: list[str] | None
    target_industry: list[str] | None
    daily_send_cap: int
    created_by: UUID | None
    # Step counts computed on the fly
    step_count: int = 0


class SequenceListResponse(BaseModel):
    items: list[SequenceOut]
    total: int


class SequenceEnrollRequest(BaseModel):
    prospect_id: UUID
    sequence_id: UUID


class SequenceEnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    prospect_id: UUID
    sequence_id: UUID
    current_step: int
    status: str
    next_action_at: datetime | None
    started_at: datetime
    completed_at: datetime | None
    stopped_reason: str | None
