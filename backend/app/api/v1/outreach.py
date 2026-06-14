"""
Outreach router — message CRUD + approval workflow (T6)

Endpoints:
  POST   /messages                  — create draft
  GET    /messages                  — list messages
  GET    /messages/{id}             — get one
  PATCH  /messages/{id}             — edit draft
  DELETE /messages/{id}             — delete draft
  POST   /messages/{id}/submit      — draft → pending_approval
  POST   /messages/{id}/approve     — pending_approval → approved (R10)
  POST   /messages/{id}/reject      — pending_approval → rejected
  POST   /messages/{id}/send        — send now (approved → sent)
  POST   /messages/generate         — generate body from hook (T5 → T6)
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import desc, func, select

from app.core.config import settings
from app.core.database import DB
from app.core.deps import CurrentUser
from app.core.security import (
    rate_limit_ai,
    rate_limit_create,
    rate_limit_delete,
    rate_limit_send,
    rate_limit_update,
)
from app.models.outreach import Message
from app.models.prospect import Prospect
from app.schemas.outreach import (
    MessageApprovalRequest,
    MessageCreate,
    MessageGenerateRequest,
    MessageListResponse,
    MessageOut,
    MessageUpdate,
    OutreachStatsOut,
)
from app.services.outreach import (
    approve_message,
    get_recipient_for_prospect,
    send_message_now,
    submit_for_approval,
)
from app.services.llm import LLMError, complete
from app.services.prompts import build_outreach_email_prompt

router = APIRouter(prefix="/outreach", tags=["outreach"])


@router.get("/stats", response_model=OutreachStatsOut)
async def get_outreach_stats(
    current_user: CurrentUser,
    db: DB,
) -> OutreachStatsOut:
    """Counts of messages per status (for the hero KPI cards).

    Cheap GROUP BY query — no joins, no prospect lookups.
    """
    q = select(Message.status, func.count(Message.id)).group_by(
        Message.status
    )
    rows = (await db.execute(q)).all()
    counts = {row[0]: int(row[1]) for row in rows}
    # Normalize all 13 statuses (default 0)
    all_statuses = [
        "draft", "pending_approval", "approved", "scheduled",
        "sending", "sent", "delivered", "opened", "clicked",
        "replied", "bounced", "failed", "rejected",
    ]
    return OutreachStatsOut(
        **{s: counts.get(s, 0) for s in all_statuses},
    )


@router.post(
    "/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
@rate_limit_create()
async def create_message(
    request: Request,
    payload: MessageCreate,
    current_user: CurrentUser,
    db: DB,
) -> Message:
    """Create a new message in 'draft' status.

    Caller can submit for approval (POST /messages/{id}/submit)
    once ready.
    """
    from app.core.config import settings

    # Auto-approve mode (configurable, default off per R10)
    initial_status = "pending_approval" if settings.outreach_auto_approve else "draft"

    msg = Message(
        prospect_id=payload.prospect_id,
        channel=payload.channel,
        direction="outbound",
        subject=payload.subject,
        body=payload.body,
        status=initial_status,
        scheduled_at=payload.scheduled_at,
        extra_metadata={
            "hook_id": str(payload.hook_id) if payload.hook_id else None,
            "template_id": str(payload.template_id) if payload.template_id else None,
        },
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


@router.get("/messages", response_model=MessageListResponse)
async def list_messages(
    current_user: CurrentUser,
    db: DB,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: str | None = Query(None, alias="status"),
    channel: str | None = None,
    prospect_id: UUID | None = None,
    prospect_grade: str | None = Query(None, description="Filter by prospect's quality_grade (A/B/C/D)"),
    needs_approval: bool = False,
) -> MessageListResponse:
    """List messages with filters.

    `needs_approval=true` returns only messages in
    pending_approval status (the R10 review queue).
    `prospect_grade=A|B|C|D` filters by the linked prospect's grade.
    """
    q = select(Message)
    count_q = select(func.count(Message.id))

    if status_filter:
        q = q.where(Message.status == status_filter)
        count_q = count_q.where(Message.status == status_filter)
    if needs_approval:
        q = q.where(Message.status == "pending_approval")
        count_q = count_q.where(Message.status == "pending_approval")
    if channel:
        q = q.where(Message.channel == channel)
        count_q = count_q.where(Message.channel == channel)
    if prospect_id:
        q = q.where(Message.prospect_id == prospect_id)
        count_q = count_q.where(Message.prospect_id == prospect_id)
    if prospect_grade:
        q = q.join(Prospect, Prospect.id == Message.prospect_id).where(
            Prospect.quality_grade == prospect_grade
        )
        count_q = count_q.join(
            Prospect, Prospect.id == Message.prospect_id
        ).where(Prospect.quality_grade == prospect_grade)

    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * per_page
    q = q.order_by(desc(Message.created_at)).offset(offset).limit(per_page)
    items = (await db.execute(q)).scalars().all()
    pages = (total + per_page - 1) // per_page if total > 0 else 0
    return MessageListResponse(
        items=[MessageOut.model_validate(m) for m in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/messages/{message_id}", response_model=MessageOut)
async def get_message(
    message_id: UUID,
    current_user: CurrentUser,
    db: DB,
) -> Message:
    msg = (
        await db.execute(select(Message).where(Message.id == message_id))
    ).scalar_one_or_none()
    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message {message_id} not found",
        )
    return msg


@router.patch("/messages/{message_id}", response_model=MessageOut)
@rate_limit_update()
async def update_message(
    request: Request,
    message_id: UUID,
    payload: MessageUpdate,
    current_user: CurrentUser,
    db: DB,
) -> Message:
    """Edit a draft (only allowed in draft/pending_approval/rejected)."""
    msg = (
        await db.execute(select(Message).where(Message.id == message_id))
    ).scalar_one_or_none()
    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message {message_id} not found",
        )
    if msg.status not in ("draft", "pending_approval", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit in status '{msg.status}'",
        )
    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(msg, k, v)
    await db.commit()
    await db.refresh(msg)
    return msg


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit_delete()
async def delete_message(
    request: Request,
    message_id: UUID,
    current_user: CurrentUser,
    db: DB,
) -> None:
    msg = (
        await db.execute(select(Message).where(Message.id == message_id))
    ).scalar_one_or_none()
    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message {message_id} not found",
        )
    if msg.status in ("sending", "sent", "delivered"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete sent message (status={msg.status})",
        )
    await db.delete(msg)
    await db.commit()


@router.post("/messages/{message_id}/submit", response_model=MessageOut)
async def submit_for_approval_endpoint(
    message_id: UUID,
    current_user: CurrentUser,
    db: DB,
) -> Message:
    """draft → pending_approval (ready for human review)."""
    result = await submit_for_approval(message_id)
    if not result.get("ok"):
        code = 404 if result.get("error") == "not_found" else 400
        raise HTTPException(status_code=code, detail=result.get("error"))
    msg = (
        await db.execute(select(Message).where(Message.id == message_id))
    ).scalar_one_or_none()
    return msg  # type: ignore


@router.post("/messages/{message_id}/approve", response_model=MessageOut)
async def approve_endpoint(
    message_id: UUID,
    payload: MessageApprovalRequest,
    current_user: CurrentUser,
    db: DB,
) -> Message:
    """
    R10 human-in-the-loop: approve or reject a message.

    Only works for messages in pending_approval status.
    Approve → status='approved' (ready to send).
    Reject → status='rejected'.
    """
    result = await approve_message(
        message_id,
        approver_id=current_user.id,
        approve=payload.approve,
        reason=payload.reason,
    )
    if not result.get("ok"):
        code = 404 if result.get("error") == "not_found" else 400
        raise HTTPException(status_code=code, detail=result.get("error"))
    msg = (
        await db.execute(select(Message).where(Message.id == message_id))
    ).scalar_one_or_none()
    return msg  # type: ignore


@router.post("/messages/{message_id}/send", response_model=MessageOut)
@rate_limit_send()
async def send_message_endpoint(
    request: Request,
    message_id: UUID,
    current_user: CurrentUser,
    db: DB,
) -> Message:
    """
    Send an approved message immediately.

    For v1, runs synchronously. T6.2 will move to Celery.
    """
    result = await send_message_now(message_id)
    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "send failed"),
        )
    msg = (
        await db.execute(select(Message).where(Message.id == message_id))
    ).scalar_one_or_none()
    return msg  # type: ignore


@router.post("/messages/generate", response_model=MessageOut)
@rate_limit_ai()
async def generate_message(
    request: Request,
    payload: MessageGenerateRequest,
    current_user: CurrentUser,
    db: DB,
    create: bool = Query(True, description="Create draft after generation"),
) -> Message:
    """
    Generate an outreach message body from a prospect's hook.

    Uses the LLM (with template fallback) to expand the hook
    into a full email subject+body. Optionally creates the draft.
    """
    from app.models.lead import Hook
    from app.models.prospect import PainPoint, Prospect, TechStack

    # Load hook + prospect + pains
    hook = (
        await db.execute(select(Hook).where(Hook.id == payload.hook_id))
    ).scalar_one_or_none()
    if not hook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hook {payload.hook_id} not found",
        )
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
    pains = (
        (
            await db.execute(
                select(PainPoint)
                .where(PainPoint.prospect_id == payload.prospect_id)
                .order_by(PainPoint.severity.desc())
            )
        )
        .scalars()
        .all()
    )
    tech = (
        await db.execute(
            select(TechStack).where(TechStack.prospect_id == payload.prospect_id)
        )
    ).scalar_one_or_none()

    pains_dict = [
        {
            "kind": p.category,
            "severity": p.severity,
            "title": (p.evidence_quote or "").split("\n")[0][:100],
            "description": p.description,
        }
        for p in pains
    ]
    tech_dict = (
        {
            "cms": tech.cms,
            "framework": tech.framework,
            "hosting_provider": tech.hosting_provider,
            "has_ssl": tech.has_ssl,
            "issues": tech.issues,
        }
        if tech
        else None
    )

    # Generate via LLM
    if payload.channel == "email":
        from app.services.prompts import build_outreach_email_prompt

        system, user = build_outreach_email_prompt(
            company_name=prospect.company_name,
            industry=prospect.industry,
            location=prospect.location_city,
            hook_text=hook.hook_text,
            pains=pains_dict,
        )
        try:
            result = await complete(
                system=system,
                user=user,
                temperature=0.5,
                max_tokens=800,
                json_mode=True,
            )
            import json as _json

            parsed = _json.loads(result.content) if result.content else {}
            subject = parsed.get("subject", f"Re: {prospect.company_name}")
            body = parsed.get(
                "body", f"Halo tim {prospect.company_name},\n\n{hook.hook_text}"
            )
        except (LLMError, Exception):
            subject = f"Ide untuk {prospect.company_name}"
            body = f"Halo tim {prospect.company_name},\n\n{hook.hook_text}\n\nMau diskusi 15 menit?\n\nSalam,\nTim ClientFinder"
    else:  # whatsapp/threads
        subject = None
        body = hook.hook_text  # for WA, the hook IS the message

    if not create:
        return Message(
            prospect_id=payload.prospect_id,
            channel=payload.channel,
            subject=subject,
            body=body,
            status="draft",
        )

    # Create draft
    from app.core.config import settings as _settings

    initial_status = "pending_approval" if _settings.outreach_auto_approve else "draft"
    msg = Message(
        prospect_id=payload.prospect_id,
        channel=payload.channel,
        subject=subject,
        body=body,
        status=initial_status,
        extra_metadata={
            "hook_id": str(payload.hook_id),
            "template_id": str(payload.template_id) if payload.template_id else None,
            "generated": True,
        },
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg
