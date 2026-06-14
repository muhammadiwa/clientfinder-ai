"""
Drip runner — T6 / Sprint 3A multi-channel outreach.

Celery task that walks active SequenceEnrollments and creates
Message rows for the next step in the sequence.

Per R10 (human-in-the-loop): the drip runner NEVER auto-sends.
For each due enrollment it:
  1. Picks the channel via channel_selector (with industry bias)
  2. Picks + renders the template via template_factory
  3. Creates a Message with status='pending_approval'
  4. Advances enrollment.current_step
  5. Sets next_action_at to the next step's day_offset

A separate worker (send_message_task) picks up approved messages
and dispatches them. The operator (per R10) sees the
'pending_approval' queue in the UI and clicks Approve.

The task is idempotent: re-running it within the same window
won't double-send because it only acts on enrollments whose
next_action_at <= now AND haven't yet produced a Message for
the current step.

Edge cases:
  - No contact info (no email + no phone) → mark enrollment as
    'stopped' with reason='no_contact'
  - No template for (channel, category, industry) → skip the
    step, advance current_step, log warning
  - current_step >= len(steps) → mark 'completed'
  - Daily send cap reached → skip (next_action_at bumped to
    next day)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.activity import Activity
from app.models.outreach import (
    Message,
    Sequence,
    SequenceEnrollment,
    Template,
)
from app.models.prospect import Prospect
from app.services.outreach.channel_selector import pick_channel
from app.services.outreach.template_factory import (
    canonicalize_industry,
    render_for_prospect,
)
from app.services.outreach.template_factory import (
    seed_template_library as _seed_templates,
)

logger = logging.getLogger("clientfinder.tasks.drip_runner")


async def _build_variables(
    db: AsyncSession,
    prospect: Prospect,
) -> dict[str, str]:
    """Build the variable dict for template rendering.

    Sources: Prospect model fields + the latest LeadScore's
    pain summary (heuristic)."""
    from app.models.lead import LeadScore, PainPoint

    # Get the latest pain points for the pain_summary var
    pain_points = (
        await db.execute(
            select(PainPoint)
            .where(PainPoint.prospect_id == prospect.id)
            .order_by(PainPoint.severity.desc())
            .limit(3)
        )
    ).scalars().all()
    pain_summary = (
        "; ".join(f"{pp.category} ({pp.severity})" for pp in pain_points)
        if pain_points
        else "proses yang berulang yang bisa di-automasi"
    )
    return {
        "company_name": prospect.company_name or "",
        "owner_name": prospect.owner_name or "",
        "industry": prospect.industry or "",
        "location": ", ".join(filter(None, [
            prospect.location_city,
            prospect.location_province,
        ])) or "Indonesia",
        "pain_summary": pain_summary,
        "sender_name": "Tim ClientFinder",
    }


async def _process_one_enrollment(
    db: AsyncSession,
    enrollment: SequenceEnrollment,
) -> dict[str, Any]:
    """Process a single enrollment. Returns a small status dict."""
    seq = (
        await db.execute(
            select(Sequence).where(Sequence.id == enrollment.sequence_id)
        )
    ).scalar_one_or_none()
    if not seq or not seq.is_active:
        enrollment.status = "stopped"
        enrollment.stopped_reason = "sequence_inactive_or_missing"
        return {"ok": False, "reason": "seq_inactive"}

    # Daily send cap check (Sprint 3A sub-task 3).
    # If today's sent count for this sequence >= cap, bump the
    # enrollment's next_action_at to tomorrow midnight UTC and
    # skip. The runner will see the same enrollment as due again
    # on its next tick, so the bump is required.
    from app.services.outreach.analytics import (
        count_sent_today_for_sequence,
    )
    sent_today = await count_sent_today_for_sequence(db, seq.id)
    if sent_today >= seq.daily_send_cap:
        tomorrow = (
            datetime.now(timezone.utc)
            .replace(hour=0, minute=0, second=0, microsecond=0)
            + timedelta(days=1)
        )
        enrollment.next_action_at = tomorrow
        return {
            "ok": False,
            "reason": "daily_cap_reached",
            "sent_today": sent_today,
            "cap": seq.daily_send_cap,
        }

    steps = seq.steps or []
    if enrollment.current_step >= len(steps):
        enrollment.status = "completed"
        enrollment.completed_at = datetime.now(timezone.utc)
        return {"ok": False, "reason": "completed"}

    step = steps[enrollment.current_step]
    step_channel = step.get("channel", "auto")
    step_category = step.get("category", "first_touch")
    step_template_id = step.get("template_id")

    prospect = (
        await db.execute(
            select(Prospect).where(Prospect.id == enrollment.prospect_id)
        )
    ).scalar_one_or_none()
    if not prospect:
        enrollment.status = "stopped"
        enrollment.stopped_reason = "prospect_missing"
        return {"ok": False, "reason": "prospect_missing"}

    # 1. Channel selection
    industry_canon = canonicalize_industry(prospect.industry)
    if step_channel == "auto":
        pick = pick_channel(prospect, industry_canonical=industry_canon)
    elif step_channel in ("email", "whatsapp"):
        pick = pick_channel(
            prospect, preferred_channel=step_channel,
            industry_canonical=industry_canon,
        )
    else:
        pick = pick_channel(prospect, industry_canonical=industry_canon)
    if not pick.channel:
        enrollment.status = "stopped"
        enrollment.stopped_reason = f"no_contact:{pick.reason}"
        return {"ok": False, "reason": "no_contact"}

    # 2. Template render
    variables = await _build_variables(db, prospect)
    if step_template_id:
        # Specific template forced by the step
        tmpl = (
            await db.execute(
                select(Template).where(Template.id == UUID(step_template_id))
            )
        ).scalar_one_or_none()
        if tmpl:
            from app.services.outreach.template_factory import render_template
            body = render_template(tmpl.body, variables)
            subject = (
                render_template(tmpl.subject, variables)
                if tmpl.subject
                else None
            )
        else:
            # Fallback to auto-pick
            rendered = await render_for_prospect(
                db,
                channel=pick.channel,
                category=step_category,
                industry=prospect.industry,
                variables=variables,
            )
            body = rendered["body"] or ""
            subject = rendered["subject"]
    else:
        rendered = await render_for_prospect(
            db,
            channel=pick.channel,
            category=step_category,
            industry=prospect.industry,
            variables=variables,
        )
        body = rendered["body"] or ""
        subject = rendered["subject"]
    if not body:
        # No template available — log + skip this step
        logger.warning(
            "drip_runner: no template for step %d of enrollment %s "
            "(channel=%s category=%s industry=%s)",
            enrollment.current_step, enrollment.id,
            pick.channel, step_category, industry_canon,
        )
        enrollment.current_step += 1
        # Move to next step
        if enrollment.current_step < len(steps):
            next_step = steps[enrollment.current_step]
            enrollment.next_action_at = (
                datetime.now(timezone.utc)
                + timedelta(days=next_step.get("day_offset", 0))
            )
        return {"ok": False, "reason": "no_template"}

    # 3. Create the Message (always pending_approval per R10)
    msg = Message(
        prospect_id=prospect.id,
        channel=pick.channel,
        direction="outbound",
        subject=subject,
        body=body,
        status="pending_approval",
        scheduled_at=datetime.now(timezone.utc),
        extra_metadata={
            "enrollment_id": str(enrollment.id),
            "sequence_id": str(seq.id),
            "sequence_name": seq.name,
            "step_index": enrollment.current_step,
            "step_category": step_category,
            "recipient": pick.recipient,
            "channel_reason": pick.reason,
        },
    )
    db.add(msg)

    # Log activity
    db.add(
        Activity(
            prospect_id=prospect.id,
            action="drip_step_generated",
            details={
                "sequence_id": str(seq.id),
                "step_index": enrollment.current_step,
                "channel": pick.channel,
                "message_id": str(msg.id),
            },
        )
    )

    # 4. Advance the enrollment
    enrollment.current_step += 1
    if enrollment.current_step >= len(steps):
        enrollment.status = "completed"
        enrollment.completed_at = datetime.now(timezone.utc)
        enrollment.next_action_at = None
    else:
        next_step = steps[enrollment.current_step]
        enrollment.next_action_at = (
            datetime.now(timezone.utc)
            + timedelta(days=next_step.get("day_offset", 0))
        )

    return {
        "ok": True,
        "message_id": str(msg.id),
        "channel": pick.channel,
        "step": enrollment.current_step - 1,
    }


@celery_app.task(name="app.tasks.outreach.drip_runner", bind=True, max_retries=1)
def drip_runner_task(self) -> dict[str, int]:
    """Periodic Celery task: walk due enrollments + generate messages.

    Idempotent within the run window. Returns a summary dict:
        {processed: int, generated: int, skipped: int, errors: int}
    """
    logger.info("drip_runner: starting")

    async def _run() -> dict[str, int]:
        summary = {"processed": 0, "generated": 0, "skipped": 0, "errors": 0}
        async with AsyncSessionLocal() as db:
            # Seed templates on first run (idempotent — does nothing if already seeded)
            try:
                await _seed_templates(db)
            except Exception as e:  # noqa: BLE001
                logger.warning("drip_runner: template seed failed: %s", e)

            # Find due enrollments
            now = datetime.now(timezone.utc)
            due = (
                await db.execute(
                    select(SequenceEnrollment).where(
                        SequenceEnrollment.status == "active",
                        SequenceEnrollment.next_action_at <= now,
                    ).limit(100)
                )
            ).scalars().all()
            logger.info("drip_runner: %d due enrollments", len(due))

            for enr in due:
                try:
                    result = await _process_one_enrollment(db, enr)
                    summary["processed"] += 1
                    if result.get("ok"):
                        summary["generated"] += 1
                    else:
                        summary["skipped"] += 1
                except Exception as e:  # noqa: BLE001
                    logger.exception(
                        "drip_runner: error on enrollment %s: %s",
                        enr.id, e,
                    )
                    summary["errors"] += 1
            await db.commit()
        return summary

    try:
        return asyncio.run(_run())
    except Exception as e:  # noqa: BLE001
        logger.exception("drip_runner: task crashed: %s", e)
        return {"processed": 0, "generated": 0, "skipped": 0, "errors": 1}
