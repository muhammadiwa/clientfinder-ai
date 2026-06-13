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

    steps = seq.steps or []
    first_step = steps[0] if steps else None
    next_action_at = datetime.now(timezone.utc) + timedelta(
        days=first_step.get("day_offset", 0) if first_step else 0
    )

    enrollment = SequenceEnrollment(
        prospect_id=payload.prospect_id,
        sequence_id=payload.sequence_id,
        current_step=0,
        status="active",
        next_action_at=next_action_at,
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
