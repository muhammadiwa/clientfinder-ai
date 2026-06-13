"""
Outreach service — main orchestrator for message sending.

R10 (human-in-the-loop): every outbound message must pass
human approval before send.

State machine:
  draft → pending_approval → approved → sending → sent → delivered
                                                    → opened
                                                    → clicked
                                                    → replied
                                                    → bounced
                                                    → failed
  pending_approval → rejected
  draft → deleted
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.activity import Activity
from app.models.outreach import Message
from app.services.outreach.email import send_email
from app.services.outreach.whatsapp import send_whatsapp

logger = logging.getLogger("clientfinder.outreach")


async def get_recipient_for_prospect(
    db: AsyncSession,
    prospect_id: UUID,
    channel: str,
) -> str | None:
    """Pick the right contact field based on channel."""
    from app.models.prospect import Prospect

    prospect = (
        await db.execute(select(Prospect).where(Prospect.id == prospect_id))
    ).scalar_one_or_none()
    if not prospect:
        return None
    if channel == "email":
        return prospect.email
    if channel in ("whatsapp", "threads"):
        return prospect.phone
    return None


async def approve_message(
    message_id: UUID,
    *,
    approver_id: UUID,
    approve: bool = True,
    reason: str | None = None,
) -> dict[str, Any]:
    """
    Approve or reject a message (R10 human-in-the-loop).

    On approve → status='approved' (ready to send).
    On reject → status='rejected' (won't send).
    """
    async with AsyncSessionLocal() as db:
        msg = (
            await db.execute(select(Message).where(Message.id == message_id))
        ).scalar_one_or_none()
        if not msg:
            return {"ok": False, "error": "not_found"}
        if msg.status not in ("draft", "pending_approval", "rejected"):
            return {
                "ok": False,
                "error": f"Cannot approve from status '{msg.status}'",
            }
        if approve:
            msg.status = "approved"
            msg.approved_by = approver_id
            msg.approved_at = datetime.now(timezone.utc)
            # Log activity
            db.add(
                Activity(
                    prospect_id=msg.prospect_id,
                    user_id=approver_id,
                    action="message_approved",
                    details={
                        "message_id": str(message_id),
                        "channel": msg.channel,
                    },
                )
            )
        else:
            msg.status = "rejected"
            db.add(
                Activity(
                    prospect_id=msg.prospect_id,
                    user_id=approver_id,
                    action="message_rejected",
                    details={
                        "message_id": str(message_id),
                        "reason": reason,
                    },
                )
            )
        await db.commit()
        await db.refresh(msg)
        return {"ok": True, "status": msg.status, "id": str(msg.id)}


async def submit_for_approval(message_id: UUID) -> dict[str, Any]:
    """Move draft → pending_approval (ready for human review)."""
    async with AsyncSessionLocal() as db:
        msg = (
            await db.execute(select(Message).where(Message.id == message_id))
        ).scalar_one_or_none()
        if not msg:
            return {"ok": False, "error": "not_found"}
        if msg.status != "draft":
            return {"ok": False, "error": f"Not in draft (status={msg.status})"}
        msg.status = "pending_approval"
        await db.commit()
        return {"ok": True, "status": msg.status, "id": str(msg.id)}


async def send_message_now(message_id: UUID) -> dict[str, Any]:
    """
    Send an approved message. Called by Celery task or directly.

    Sets status='sending' → 'sent' (or 'failed').
    Captures external_id + sent_at + error_message.
    """
    async with AsyncSessionLocal() as db:
        msg = (
            await db.execute(select(Message).where(Message.id == message_id))
        ).scalar_one_or_none()
        if not msg:
            return {"ok": False, "error": "not_found"}
        if msg.status not in ("approved", "scheduled"):
            return {
                "ok": False,
                "error": f"Cannot send from status '{msg.status}'",
            }

        # Resolve recipient
        recipient = await get_recipient_for_prospect(
            db, msg.prospect_id, msg.channel
        )
        if not recipient:
            msg.status = "failed"
            msg.error_message = f"No {msg.channel} contact for prospect"
            await db.commit()
            return {
                "ok": False,
                "error": f"No {msg.channel} contact for prospect",
            }

        # Mark sending
        msg.status = "sending"
        await db.commit()
        await db.refresh(msg)

        # Dispatch by channel
        result: dict[str, Any] = {"ok": False, "error": "unknown channel"}
        if msg.channel == "email":
            result = await send_email(
                to_email=recipient,
                subject=msg.subject or "(no subject)",
                body=msg.body,
            )
        elif msg.channel == "whatsapp":
            result = await send_whatsapp(
                to_phone=recipient,
                body=msg.body,
            )
        # threads: TODO in T6.2 with Playwright

        # Update status
        if result.get("ok"):
            msg.status = "sent"
            msg.sent_at = datetime.now(timezone.utc)
            msg.external_id = result.get("external_id")
            # Email only: mark delivered (no delivery receipt for WhatsApp)
            if msg.channel == "email":
                msg.delivered_at = datetime.now(timezone.utc)
            db.add(
                Activity(
                    prospect_id=msg.prospect_id,
                    action="message_sent",
                    details={
                        "message_id": str(message_id),
                        "channel": msg.channel,
                        "transport": result.get("transport"),
                    },
                )
            )
        else:
            msg.status = "failed"
            msg.error_message = result.get("error", "unknown")[:500]
            db.add(
                Activity(
                    prospect_id=msg.prospect_id,
                    action="message_failed",
                    details={
                        "message_id": str(message_id),
                        "channel": msg.channel,
                        "error": msg.error_message,
                    },
                )
            )
        await db.commit()
        return result
