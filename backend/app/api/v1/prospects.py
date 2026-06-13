"""
Prospects router — CRUD with filtering, search, pagination
"""
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.core.database import DB
from app.core.deps import CurrentUser
from app.models.activity import Activity
from app.models.prospect import Prospect
from app.schemas.prospect import (
    ProspectCreate,
    ProspectListResponse,
    ProspectOut,
    ProspectUpdate,
)

router = APIRouter(prefix="/prospects", tags=["prospects"])


@router.get("", response_model=ProspectListResponse)
async def list_prospects(
    current_user: CurrentUser,
    db: DB,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    source: str | None = None,
    industry: str | None = None,
    grade: str | None = None,
    min_score: int | None = Query(None, ge=0, le=100),
    search: str | None = None,
    include_deleted: bool = False,
) -> ProspectListResponse:
    """List prospects with filters, search, and pagination."""
    # Base query
    query = select(Prospect)
    count_query = select(func.count(Prospect.id))

    if not include_deleted:
        query = query.where(Prospect.deleted_at.is_(None))
        count_query = count_query.where(Prospect.deleted_at.is_(None))

    # Filters
    if status_filter:
        query = query.where(Prospect.status == status_filter)
        count_query = count_query.where(Prospect.status == status_filter)
    if source:
        query = query.where(Prospect.source == source)
        count_query = count_query.where(Prospect.source == source)
    if industry:
        query = query.where(Prospect.industry == industry)
        count_query = count_query.where(Prospect.industry == industry)
    if grade:
        query = query.where(Prospect.quality_grade == grade)
        count_query = count_query.where(Prospect.quality_grade == grade)
    if min_score is not None:
        query = query.where(Prospect.score_total >= min_score)
        count_query = count_query.where(Prospect.score_total >= min_score)
    if search:
        search_filter = or_(
            Prospect.company_name.ilike(f"%{search}%"),
            Prospect.description.ilike(f"%{search}%"),
            Prospect.email.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Count total
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Pagination
    offset = (page - 1) * per_page
    query = query.order_by(Prospect.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    items = result.scalars().all()

    pages = (total + per_page - 1) // per_page if total > 0 else 0

    return ProspectListResponse(
        items=[ProspectOut.model_validate(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.post("", response_model=ProspectOut, status_code=status.HTTP_201_CREATED)
async def create_prospect(
    payload: ProspectCreate,
    current_user: CurrentUser,
    db: DB,
) -> Prospect:
    """Create a new prospect manually."""
    prospect = Prospect(
        **payload.model_dump(),
        owner_id=current_user.id,
        discovered_at=datetime.now(timezone.utc),
    )
    db.add(prospect)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Database integrity error: {e.orig}",
        )
    await db.refresh(prospect)

    # Log activity
    activity = Activity(
        prospect_id=prospect.id,
        user_id=current_user.id,
        action="prospect_created",
        details={"source": prospect.source, "manual": True},
    )
    db.add(activity)
    await db.commit()

    return prospect


@router.get("/{prospect_id}", response_model=ProspectOut)
async def get_prospect(
    prospect_id: UUID,
    current_user: CurrentUser,
    db: DB,
) -> Prospect:
    """Get a single prospect by ID."""
    result = await db.execute(
        select(Prospect).where(
            Prospect.id == prospect_id,
            Prospect.deleted_at.is_(None),
        )
    )
    prospect = result.scalar_one_or_none()

    if prospect is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prospect {prospect_id} not found",
        )

    return prospect


@router.patch("/{prospect_id}", response_model=ProspectOut)
async def update_prospect(
    prospect_id: UUID,
    payload: ProspectUpdate,
    current_user: CurrentUser,
    db: DB,
) -> Prospect:
    """Update a prospect (partial update)."""
    result = await db.execute(
        select(Prospect).where(
            Prospect.id == prospect_id,
            Prospect.deleted_at.is_(None),
        )
    )
    prospect = result.scalar_one_or_none()

    if prospect is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prospect {prospect_id} not found",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(prospect, key, value)

    await db.commit()
    await db.refresh(prospect)

    # Log activity
    activity = Activity(
        prospect_id=prospect.id,
        user_id=current_user.id,
        action="prospect_updated",
        details={"fields_updated": list(update_data.keys())},
    )
    db.add(activity)
    await db.commit()

    return prospect


@router.delete("/{prospect_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prospect(
    prospect_id: UUID,
    current_user: CurrentUser,
    db: DB,
    hard_delete: bool = Query(False, description="Permanently delete (vs soft delete)"),
) -> None:
    """Delete a prospect (soft by default)."""
    result = await db.execute(
        select(Prospect).where(
            Prospect.id == prospect_id,
            Prospect.deleted_at.is_(None),
        )
    )
    prospect = result.scalar_one_or_none()

    if prospect is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prospect {prospect_id} not found",
        )

    if hard_delete:
        await db.delete(prospect)
    else:
        prospect.deleted_at = datetime.now(timezone.utc)

    await db.commit()
