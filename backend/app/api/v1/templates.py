"""
Templates router — CRUD for outreach templates (T6 Group 3)
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import desc, func, select

from app.core.database import DB
from app.core.deps import CurrentUser
from app.models.outreach import Template
from app.schemas.templates import (
    TemplateCreate,
    TemplateListResponse,
    TemplateOut,
    TemplateUpdate,
)

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    current_user: CurrentUser,
    db: DB,
    channel: str | None = Query(None),
    active_only: bool = Query(False),
) -> TemplateListResponse:
    """List outreach templates (email/whatsapp/threads)."""
    q = select(Template)
    count_q = select(func.count(Template.id))

    if channel:
        q = q.where(Template.channel == channel)
        count_q = count_q.where(Template.channel == channel)
    if active_only:
        q = q.where(Template.is_active.is_(True))
        count_q = count_q.where(Template.is_active.is_(True))

    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(desc(Template.usage_count), Template.name).limit(200)
    items = (await db.execute(q)).scalars().all()
    return TemplateListResponse(
        items=[TemplateOut.model_validate(t) for t in items],
        total=total,
    )


@router.post(
    "",
    response_model=TemplateOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    payload: TemplateCreate,
    current_user: CurrentUser,
    db: DB,
) -> Template:
    template = Template(**payload.model_dump())
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(
    template_id: UUID,
    current_user: CurrentUser,
    db: DB,
) -> Template:
    template = (
        await db.execute(select(Template).where(Template.id == template_id))
    ).scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found",
        )
    return template


@router.patch("/{template_id}", response_model=TemplateOut)
async def update_template(
    template_id: UUID,
    payload: TemplateUpdate,
    current_user: CurrentUser,
    db: DB,
) -> Template:
    template = (
        await db.execute(select(Template).where(Template.id == template_id))
    ).scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found",
        )
    update = payload.model_dump(exclude_unset=True)
    for k, v in update.items():
        setattr(template, k, v)
    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    current_user: CurrentUser,
    db: DB,
) -> None:
    template = (
        await db.execute(select(Template).where(Template.id == template_id))
    ).scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found",
        )
    await db.delete(template)
    await db.commit()
