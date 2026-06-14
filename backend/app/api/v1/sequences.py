"""
Sequences router — CRUD for outreach sequences (T6 Group 3)

A sequence = an ordered set of template-driven steps (email/wa/threads)
with day offsets. Enroll a prospect and the system will send step[0] on
day 0, step[1] on day[1], etc.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import desc, func, select

from app.core.database import DB
from app.core.deps import CurrentUser
from app.models.activity import Activity
from app.models.outreach import Sequence, SequenceEnrollment
from app.models.prospect import Prospect
from app.schemas.sequences import (
    SequenceCreate,
    SequenceEnrollRequest,
    SequenceListResponse,
    SequenceOut,
    SequenceUpdate,
)

router = APIRouter(prefix="/sequences", tags=["sequences"])


def _to_out(seq: Sequence) -> SequenceOut:
    return SequenceOut(
        id=seq.id,
        name=seq.name,
        description=seq.description,
        steps=seq.steps or [],
        is_active=seq.is_active,
        target_grade=seq.target_grade,
        target_source=seq.target_source,
        target_industry=seq.target_industry,
        daily_send_cap=seq.daily_send_cap,
        created_by=seq.created_by,
        step_count=len(seq.steps or []),
    )


@router.get("", response_model=SequenceListResponse)
async def list_sequences(
    current_user: CurrentUser,
    db: DB,
    is_active: bool | None = None,
) -> SequenceListResponse:
    q = select(Sequence)
    count_q = select(func.count(Sequence.id))
    if is_active is not None:
        q = q.where(Sequence.is_active == is_active)
        count_q = count_q.where(Sequence.is_active == is_active)
    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(desc(Sequence.daily_send_cap), Sequence.name)
    items = (await db.execute(q)).scalars().all()
    return SequenceListResponse(
        items=[_to_out(s) for s in items],
        total=total,
    )


@router.post(
    "",
    response_model=SequenceOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_sequence(
    payload: SequenceCreate,
    current_user: CurrentUser,
    db: DB,
) -> Sequence:
    seq = Sequence(
        **payload.model_dump(),
        created_by=current_user.id,
    )
    db.add(seq)
    await db.commit()
    await db.refresh(seq)
    return _to_out(seq)




# --- Enrollment control (T6.2 / Sprint 3A) ---


@router.post("/enrollments/{enrollment_id}/pause")
async def pause_enrollment(
    enrollment_id: UUID,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    """Pause an active enrollment. Operator can resume later."""
    enr = (
        await db.execute(
            select(SequenceEnrollment).where(
                SequenceEnrollment.id == enrollment_id,
            )
        )
    ).scalar_one_or_none()
    if not enr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Enrollment {enrollment_id} not found",
        )
    if enr.status != "active":
        return {"ok": False, "error": f"Cannot pause from status {enr.status}"}
    enr.status = "paused"
    db.add(
        Activity(
            prospect_id=enr.prospect_id,
            user_id=current_user.id,
            action="enrollment_paused",
            details={"enrollment_id": str(enrollment_id)},
        )
    )
    await db.commit()
    return {"ok": True, "status": "paused"}


@router.post("/enrollments/{enrollment_id}/resume")
async def resume_enrollment(
    enrollment_id: UUID,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    """Resume a paused enrollment. next_action_at reset to now."""
    enr = (
        await db.execute(
            select(SequenceEnrollment).where(
                SequenceEnrollment.id == enrollment_id,
            )
        )
    ).scalar_one_or_none()
    if not enr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Enrollment {enrollment_id} not found",
        )
    if enr.status != "paused":
        return {"ok": False, "error": f"Cannot resume from status {enr.status}"}
    enr.status = "active"
    # Set next_action_at to now so the drip runner picks it up
    from datetime import datetime, timezone
    enr.next_action_at = datetime.now(timezone.utc)
    db.add(
        Activity(
            prospect_id=enr.prospect_id,
            user_id=current_user.id,
            action="enrollment_resumed",
            details={"enrollment_id": str(enrollment_id)},
        )
    )
    await db.commit()
    return {"ok": True, "status": "active"}


@router.post("/enrollments/{enrollment_id}/stop")
async def stop_enrollment(
    enrollment_id: UUID,
    current_user: CurrentUser,
    db: DB,
    reason: str = "manual_stop",
) -> dict:
    """Stop an enrollment. Cannot be resumed — must re-enroll."""
    enr = (
        await db.execute(
            select(SequenceEnrollment).where(
                SequenceEnrollment.id == enrollment_id,
            )
        )
    ).scalar_one_or_none()
    if not enr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Enrollment {enrollment_id} not found",
        )
    if enr.status in ("completed", "stopped"):
        return {"ok": False, "error": f"Already {enr.status}"}
    enr.status = "stopped"
    enr.stopped_reason = reason
    from datetime import datetime, timezone
    enr.completed_at = datetime.now(timezone.utc)
    db.add(
        Activity(
            prospect_id=enr.prospect_id,
            user_id=current_user.id,
            action="enrollment_stopped",
            details={"enrollment_id": str(enrollment_id), "reason": reason},
        )
    )
    await db.commit()
    return {"ok": True, "status": "stopped"}


@router.get("/enrollments")
async def list_enrollments(
    current_user: CurrentUser,
    db: DB,
    status_filter: str | None = None,
    sequence_id: UUID | None = None,
    prospect_id: UUID | None = None,
    limit: int = 50,
) -> dict:
    """List enrollments, optionally filtered by status / sequence / prospect."""
    q = select(SequenceEnrollment).order_by(
        SequenceEnrollment.started_at.desc()
    )
    if status_filter:
        q = q.where(SequenceEnrollment.status == status_filter)
    if sequence_id:
        q = q.where(SequenceEnrollment.sequence_id == sequence_id)
    if prospect_id:
        q = q.where(SequenceEnrollment.prospect_id == prospect_id)
    q = q.limit(min(limit, 200))
    items = (await db.execute(q)).scalars().all()
    return {
        "items": [
            {
                "id": str(e.id),
                "prospect_id": str(e.prospect_id),
                "sequence_id": str(e.sequence_id),
                "current_step": e.current_step,
                "status": e.status,
                "next_action_at": (
                    e.next_action_at.isoformat() if e.next_action_at else None
                ),
                "started_at": e.started_at.isoformat(),
                "completed_at": (
                    e.completed_at.isoformat() if e.completed_at else None
                ),
                "stopped_reason": e.stopped_reason,
            }
            for e in items
        ],
        "total": len(items),
    }


# --- Manual drip trigger (for testing) ---


@router.post("/drip-runner/run")
async def trigger_drip_runner(
    current_user: CurrentUser,
) -> dict:
    """Manually trigger the drip runner task. Useful for testing."""
    from app.tasks.drip_runner import drip_runner_task
    result = drip_runner_task.delay()
    return {
        "ok": True,
        "task_id": result.id,
        "status": "queued",
    }


# --- Analytics (Sprint 3A sub-task 3) ---


@router.get("/{sequence_id}/analytics")
async def get_sequence_analytics(
    sequence_id: UUID,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    """Per-step + per-channel analytics for a sequence.

    Returns:
        {sequence_id, sequence_name, daily_send_cap, totals,
         by_step: [{step_index, sent, delivered, opened, ...,
                    response_rate, open_rate}], by_channel,
         today_sent, computed_at}
    """
    from app.services.outreach.analytics import compute_sequence_stats
    return await compute_sequence_stats(db, sequence_id)


@router.get("/{sequence_id}", response_model=SequenceOut)
async def get_sequence(
    sequence_id: UUID,
    current_user: CurrentUser,
    db: DB,
) -> SequenceOut:
    seq = (
        await db.execute(select(Sequence).where(Sequence.id == sequence_id))
    ).scalar_one_or_none()
    if not seq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sequence {sequence_id} not found",
        )
    return _to_out(seq)


@router.patch("/{sequence_id}", response_model=SequenceOut)
async def update_sequence(
    sequence_id: UUID,
    payload: SequenceUpdate,
    current_user: CurrentUser,
    db: DB,
) -> SequenceOut:
    seq = (
        await db.execute(select(Sequence).where(Sequence.id == sequence_id))
    ).scalar_one_or_none()
    if not seq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sequence {sequence_id} not found",
        )
    update = payload.model_dump(exclude_unset=True)
    if "steps" in update and update["steps"]:
        update["steps"] = [s.model_dump() if hasattr(s, "model_dump") else s for s in update["steps"]]
    for k, v in update.items():
        setattr(seq, k, v)
    await db.commit()
    await db.refresh(seq)
    return _to_out(seq)


@router.delete("/{sequence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sequence(
    sequence_id: UUID,
    current_user: CurrentUser,
    db: DB,
) -> None:
    seq = (
        await db.execute(select(Sequence).where(Sequence.id == sequence_id))
    ).scalar_one_or_none()
    if not seq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sequence {sequence_id} not found",
        )
    await db.delete(seq)
    await db.commit()


@router.post("/enroll", status_code=status.HTTP_201_CREATED)
async def enroll_prospect(
    payload: SequenceEnrollRequest,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    """Enroll a prospect in a sequence.

    Creates a SequenceEnrollment starting at step 0.
    The T6.2 celery-beat task picks up enrollments with
    next_action_at <= now() and sends the current step.
    """
    # Validate prospect + sequence exist
    prospect = (
        await db.execute(
            select(Prospect).where(Prospect.id == payload.prospect_id)
        )
    ).scalar_one_or_none()
    if not prospect:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prospect {payload.prospect_id} not found",
        )
    seq = (
        await db.execute(
            select(Sequence).where(Sequence.id == payload.sequence_id)
        )
    ).scalar_one_or_none()
    if not seq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sequence {payload.sequence_id} not found",
        )

    # Create enrollment at step 0
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    steps = seq.steps or []
    first_step = steps[0] if steps else None
    next_action_at = now + timedelta(
        days=first_step.get("day_offset", 0) if first_step else 0
    )

    enrollment = SequenceEnrollment(
        prospect_id=payload.prospect_id,
        sequence_id=payload.sequence_id,
        current_step=0,
        status="active",
        next_action_at=next_action_at,
        started_at=now,
    )
    db.add(enrollment)
    db.add(
        Activity(
            prospect_id=payload.prospect_id,
            user_id=current_user.id,
            action="enrolled_in_sequence",
            details={
                "sequence_id": str(payload.sequence_id),
                "sequence_name": seq.name,
            },
        )
    )
    await db.commit()
    await db.refresh(enrollment)
    return {
        "ok": True,
        "enrollment_id": str(enrollment.id),
        "next_action_at": next_action_at.isoformat(),
    }
