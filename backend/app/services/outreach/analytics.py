"""
Sequence analytics — T6 / Sprint 3A sub-task 3.

For each sequence, return per-step stats:
  - sent: messages that have been sent (status='sent')
  - delivered: email only (status has delivered_at)
  - opened: messages that have opened_at
  - clicked: messages that have clicked_at
  - replied: messages that have replied_at
  - bounced: status='bounced'
  - failed: status='failed'
  - response_rate: replied / sent
  - open_rate: opened / sent (email only — WhatsApp doesn't track opens)

Stats are derived from the messages table by aggregating over
the JSONB extra_metadata field (which stores the sequence_id
and step_index that the drip_runner wrote).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outreach import Message, Sequence


async def compute_sequence_stats(
    db: AsyncSession,
    sequence_id: UUID,
) -> dict[str, Any]:
    """Per-step statistics for a sequence.

    Returns:
        {
            "sequence_id": str,
            "totals": {sent, delivered, opened, clicked, replied,
                       bounced, failed},
            "by_step": [
                {step_index, sent, delivered, opened, ...,
                 response_rate, open_rate}
            ],
            "by_channel": {email: {...}, whatsapp: {...}},
            "today_sent": int,  # for daily cap tracking
            "computed_at": ISO,
        }
    """
    # Get the sequence + steps
    seq = (
        await db.execute(select(Sequence).where(Sequence.id == sequence_id))
    ).scalar_one_or_none()
    if not seq:
        return {"error": f"Sequence {sequence_id} not found"}
    step_count = len(seq.steps or [])

    # Aggregate from the messages table.
    # We match messages by extra_metadata->>'sequence_id' (text).
    # The JSONB key is stored as a string; PG comparison
    # is case-sensitive.
    base_filter = [
        func.coalesce(
            Message.extra_metadata["sequence_id"].astext, ""
        ) == str(sequence_id)
    ]

    # Pull all messages for this sequence in one query, then
    # bucket by step_index + channel. Avoids a per-step query.
    rows = (
        await db.execute(
            select(
                Message.extra_metadata["step_index"].astext.label("step_index"),
                Message.channel,
                Message.status,
                Message.sent_at,
                Message.delivered_at,
                Message.opened_at,
                Message.clicked_at,
                Message.replied_at,
            ).where(*base_filter)
        )
    ).all()

    # Bucket
    by_step: dict[str, dict[str, int]] = {}
    by_channel: dict[str, dict[str, int]] = {}
    totals = {
        "sent": 0, "delivered": 0, "opened": 0, "clicked": 0,
        "replied": 0, "bounced": 0, "failed": 0,
    }
    today = datetime.utcnow().date()
    today_sent = 0
    for row in rows:
        sent = row.sent_at is not None
        delivered = row.delivered_at is not None
        opened = row.opened_at is not None
        clicked = row.clicked_at is not None
        replied = row.replied_at is not None
        bounced = row.status == "bounced"
        failed = row.status == "failed"

        # Per-step
        step_key = row.step_index or "-1"
        s = by_step.setdefault(step_key, {
            "sent": 0, "delivered": 0, "opened": 0, "clicked": 0,
            "replied": 0, "bounced": 0, "failed": 0,
        })
        if sent: s["sent"] += 1
        if delivered: s["delivered"] += 1
        if opened: s["opened"] += 1
        if clicked: s["clicked"] += 1
        if replied: s["replied"] += 1
        if bounced: s["bounced"] += 1
        if failed: s["failed"] += 1

        # Per-channel
        ch = by_channel.setdefault(row.channel or "unknown", {
            "sent": 0, "delivered": 0, "opened": 0, "clicked": 0,
            "replied": 0, "bounced": 0, "failed": 0,
        })
        if sent: ch["sent"] += 1
        if delivered: ch["delivered"] += 1
        if opened: ch["opened"] += 1
        if clicked: ch["clicked"] += 1
        if replied: ch["replied"] += 1
        if bounced: ch["bounced"] += 1
        if failed: ch["failed"] += 1

        # Totals
        if sent: totals["sent"] += 1
        if delivered: totals["delivered"] += 1
        if opened: totals["opened"] += 1
        if clicked: totals["clicked"] += 1
        if replied: totals["replied"] += 1
        if bounced: totals["bounced"] += 1
        if failed: totals["failed"] += 1

        # Today's sent (for daily cap)
        if sent and row.sent_at and row.sent_at.date() == today:
            today_sent += 1

    # Enrich per-step with rates
    by_step_out: list[dict[str, Any]] = []
    for i in range(step_count):
        s = by_step.get(str(i), {
            "sent": 0, "delivered": 0, "opened": 0, "clicked": 0,
            "replied": 0, "bounced": 0, "failed": 0,
        })
        s2 = dict(s)
        s2["step_index"] = i
        s2["response_rate"] = (
            round(s["replied"] / s["sent"], 3) if s["sent"] else 0.0
        )
        s2["open_rate"] = (
            round(s["opened"] / s["sent"], 3) if s["sent"] else 0.0
        )
        by_step_out.append(s2)

    by_channel_out = {}
    for ch, s in by_channel.items():
        s2 = dict(s)
        s2["response_rate"] = (
            round(s["replied"] / s["sent"], 3) if s["sent"] else 0.0
        )
        s2["open_rate"] = (
            round(s["opened"] / s["sent"], 3) if s["sent"] else 0.0
        )
        by_channel_out[ch] = s2

    return {
        "sequence_id": str(sequence_id),
        "sequence_name": seq.name,
        "daily_send_cap": seq.daily_send_cap,
        "totals": totals,
        "by_step": by_step_out,
        "by_channel": by_channel_out,
        "today_sent": today_sent,
        "computed_at": datetime.utcnow().isoformat() + "Z",
    }


async def count_sent_today_for_sequence(
    db: AsyncSession,
    sequence_id: UUID,
) -> int:
    """Lightweight: just count today's sent messages for the
    sequence. Used by the drip_runner to enforce the daily cap."""
    today = datetime.utcnow().date()
    # Use DATE(sent_at AT TIME ZONE 'UTC') = today
    rows = (
        await db.execute(
            select(func.count(Message.id))
            .where(
                func.coalesce(
                    Message.extra_metadata["sequence_id"].astext, ""
                ) == str(sequence_id),
                Message.sent_at.is_not(None),
                func.date(Message.sent_at) == today,
            )
        )
    ).scalar() or 0
    return int(rows)
