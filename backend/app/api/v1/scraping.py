"""
Scraping router — endpoints for Scout module (T4)
"""
from typing import Annotated

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError

from app.core.database import DB
from app.core.deps import CurrentUser
from app.models.activity import Activity
from app.models.prospect import Prospect
from app.models.system import ScrapingJob
from app.schemas.scraping import (
    ScrapingJobCreate,
    ScrapingJobListResponse,
    ScrapingJobOut,
)
from app.services.scraper import get_scraper, persist_scraped_to_prospects

router = APIRouter(prefix="/scraping", tags=["scouting"])


@router.post(
    "/jobs",
    response_model=ScrapingJobOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_scraping_job(
    payload: ScrapingJobCreate,
    current_user: CurrentUser,
    db: DB,
) -> ScrapingJob:
    """Create a new scraping job. Returns the job (status=pending)."""
    job = ScrapingJob(
        source=payload.source,
        query={
            "keywords": payload.keywords,
            "location": payload.location,
            "max_results": payload.max_results,
        },
        status="pending",
        prospects_found=0,
        created_by=current_user.id,
    )
    db.add(job)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not create job: {e.orig}",
        )
    await db.refresh(job)

    # Log activity
    db.add(
        Activity(
            prospect_id=None,
            user_id=current_user.id,
            action="scraping_job_created",
            details={
                "source": payload.source,
                "keywords": payload.keywords,
                "location": payload.location,
                "max_results": payload.max_results,
            },
        )
    )
    await db.commit()

    # Enqueue background execution
    try:
        from app.tasks.scraping_tasks import run_scraping_job

        run_scraping_job.delay(str(job.id))
    except Exception as e:  # noqa: BLE001
        # If Celery unavailable (e.g. eager mode or broker down),
        # run synchronously so the job still completes
        from app.tasks.scraping_tasks import run_scraping_job_sync

        await run_scraping_job_sync(str(job.id))

    return job


@router.get("/jobs", response_model=ScrapingJobListResponse)
async def list_scraping_jobs(
    current_user: CurrentUser,
    db: DB,
    page: Annotated[int, "Page"] = 1,
    per_page: Annotated[int, "Per page"] = 20,
) -> ScrapingJobListResponse:
    """List all scraping jobs, newest first."""
    per_page = min(max(per_page, 1), 100)
    offset = (max(page, 1) - 1) * per_page

    count_q = select(func.count(ScrapingJob.id))
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(ScrapingJob)
        .order_by(desc(ScrapingJob.created_at))
        .offset(offset)
        .limit(per_page)
    )
    items = (await db.execute(q)).scalars().all()

    return ScrapingJobListResponse(
        items=[ScrapingJobOut.model_validate(j) for j in items],
        total=total,
    )


@router.get("/jobs/{job_id}", response_model=ScrapingJobOut)
async def get_scraping_job(
    job_id: str,
    current_user: CurrentUser,
    db: DB,
) -> ScrapingJob:
    """Get a single scraping job by ID."""
    from uuid import UUID

    try:
        jid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID")

    job = (
        await db.execute(select(ScrapingJob).where(ScrapingJob.id == jid))
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@router.post("/jobs/{job_id}/retry", response_model=ScrapingJobOut)
async def retry_scraping_job(
    job_id: str,
    current_user: CurrentUser,
    db: DB,
) -> ScrapingJob:
    """Retry a failed (or completed) scraping job. Resets to pending."""
    from uuid import UUID

    try:
        jid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID")

    job = (
        await db.execute(select(ScrapingJob).where(ScrapingJob.id == jid))
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job.status = "pending"
    job.error_message = None
    job.started_at = None
    job.completed_at = None
    job.prospects_found = 0
    await db.commit()
    await db.refresh(job)

    # Re-enqueue
    try:
        from app.tasks.scraping_tasks import run_scraping_job

        run_scraping_job.delay(str(job.id))
    except Exception:  # noqa: BLE001
        from app.tasks.scraping_tasks import run_scraping_job_sync

        await run_scraping_job_sync(str(job.id))

    return job


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scraping_job(
    job_id: str,
    current_user: CurrentUser,
    db: DB,
) -> None:
    """Delete a scraping job (and log)."""
    from uuid import UUID

    try:
        jid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID")

    job = (
        await db.execute(select(ScrapingJob).where(ScrapingJob.id == jid))
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    await db.delete(job)
    await db.commit()


@router.get("/presets", response_model=list[dict])
async def list_scraping_presets(
    current_user: CurrentUser,
    db: DB,
) -> list[dict]:
    """List saved query presets. Stub for v1 — returns curated defaults."""
    return [
        {
            "id": "preset-klinik-jabodetabek",
            "name": "Klinik Gigi — Jabodetabek",
            "source": "google",
            "query": {
                "keywords": "klinik gigi",
                "location": "Jabodetabek",
                "max_results": 30,
            },
        },
        {
            "id": "preset-fnb-jakarta",
            "name": "Restoran & Kafe — Jakarta",
            "source": "maps",
            "query": {
                "keywords": "restoran kafe",
                "location": "Jakarta",
                "max_results": 30,
            },
        },
        {
            "id": "preset-apotek-bandung",
            "name": "Apotek — Bandung",
            "source": "maps",
            "query": {
                "keywords": "apotek",
                "location": "Bandung",
                "max_results": 25,
            },
        },
    ]
