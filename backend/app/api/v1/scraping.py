"""
Scraping router — endpoints for Scout module (T4)
"""
from typing import Annotated

from celery.exceptions import OperationalError
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
    ScrapingPresetOut,
)
from app.services.scraper import get_scraper, persist_scraped_to_prospects
# Import at module level so we can fall back to sync without
# wrapping the import in a try/except (P1-B1 fix).
from app.tasks.scraping_tasks import run_scraping_job, run_scraping_job_sync

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

    # Enqueue background execution.
    # Catch only broker-connection errors (not broad Exception) so
    # we don't silently swallow real bugs (P0-B1 fix). Sync
    # fallback still blocks the event loop for ~30-50s on Maps
    # — acceptable as last-resort; T8 should add circuit breaker.
    try:
        run_scraping_job.delay(str(job.id))
    except (OperationalError, ConnectionError, TimeoutError) as e:
        # Broker down: log warning, run sync as last resort
        import logging
        logging.getLogger("clientfinder.scraping.api").warning(
            "Celery broker unavailable, running sync: %s", e
        )
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
        run_scraping_job.delay(str(job.id))
    except (OperationalError, ConnectionError, TimeoutError):
        await run_scraping_job_sync(str(job.id))

    return job


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scraping_job(
    job_id: str,
    current_user: CurrentUser,
    db: DB,
) -> None:
    """Delete a scraping job. Logs the deletion to activity (P1-B11 fix)."""
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

    # Log the deletion BEFORE removing the job (so we still have
    # the source for the activity record).
    db.add(
        Activity(
            prospect_id=None,
            user_id=current_user.id,
            action="scraping_job_deleted",
            details={
                "source": job.source,
                "query": job.query,
                "prospects_found": job.prospects_found,
            },
        )
    )
    await db.delete(job)
    await db.commit()


@router.get("/presets", response_model=list[ScrapingPresetOut])
async def list_scraping_presets(
    current_user: CurrentUser,
    db: DB,
) -> list[ScrapingPresetOut]:
    """List saved query presets (P1-B9 fix: use proper schema)."""
    from app.schemas.scraping import ScrapingQuery

    return [
        ScrapingPresetOut(
            id="preset-klinik-jabodetabek",
            name="Klinik Gigi — Jabodetabek",
            source="google",
            query=ScrapingQuery(
                keywords="klinik gigi", location="Jabodetabek", max_results=30
            ),
        ),
        ScrapingPresetOut(
            id="preset-fnb-jakarta",
            name="Restoran & Kafe — Jakarta",
            source="maps",
            query=ScrapingQuery(
                keywords="restoran kafe", location="Jakarta", max_results=30
            ),
        ),
        ScrapingPresetOut(
            id="preset-apotek-bandung",
            name="Apotek — Bandung",
            source="maps",
            query=ScrapingQuery(
                keywords="apotek", location="Bandung", max_results=25
            ),
        ),
    ]
