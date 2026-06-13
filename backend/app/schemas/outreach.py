"""
Pydantic schemas for Outreach module (T6)
"""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

MessageChannel = Literal["email", "whatsapp", "threads"]
MessageStatus = Literal[
    "draft",
    "pending_approval",
    "approved",
    "scheduled",
    "sending",
    "sent",
    "delivered",
    "opened",
    "clicked",
    "replied",
    "bounced",
    "failed",
    "rejected",
]
MessageDirection = Literal["outbound", "inbound"]


class MessageCreate(BaseModel):
    """Create a new message (draft or pending_approval)."""

    prospect_id: UUID
    channel: MessageChannel
    subject: str | None = Field(None, max_length=500)
    body: str = Field(..., min_length=1, max_length=20000)
    scheduled_at: datetime | None = None
    hook_id: UUID | None = None  # the hook this message was generated from
    template_id: UUID | None = None


class MessageUpdate(BaseModel):
    """Edit a draft message (only allowed in draft/pending_approval)."""

    subject: str | None = Field(None, max_length=500)
    body: str | None = Field(None, min_length=1, max_length=20000)
    scheduled_at: datetime | None = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    prospect_id: UUID
    channel: MessageChannel
    direction: MessageDirection
    subject: str | None
    body: str
    status: MessageStatus
    scheduled_at: datetime | None
    sent_at: datetime | None
    delivered_at: datetime | None
    opened_at: datetime | None
    clicked_at: datetime | None
    replied_at: datetime | None
    approved_by: UUID | None
    approved_at: datetime | None
    error_message: str | None
    external_id: str | None
    extra_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class MessageListResponse(BaseModel):
    items: list[MessageOut]
    total: int
    page: int
    per_page: int
    pages: int


class MessageApprovalRequest(BaseModel):
    """Approve or reject a message (R10 human-in-the-loop)."""

    approve: bool = True
    reason: str | None = Field(None, max_length=500)


class MessageGenerateRequest(BaseModel):
    """Generate a message body from a prospect's selected hook."""

    prospect_id: UUID
    hook_id: UUID
    channel: MessageChannel = "email"
    template_id: UUID | None = None


class OutreachStatsOut(BaseModel):
    """Counts of messages per status — drives the hero KPI cards."""

    draft: int = 0
    pending_approval: int = 0
    approved: int = 0
    scheduled: int = 0
    sending: int = 0
    sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    replied: int = 0
    bounced: int = 0
    failed: int = 0
    rejected: int = 0
