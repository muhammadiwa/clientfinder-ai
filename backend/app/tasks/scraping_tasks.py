"""
Scraping tasks — Celery tasks for Scout module (T4)

Two functions:
- run_scraping_job (Celery task, async, background)
- run_scraping_job_sync (fallback when broker unavailable)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.activity import Activity
from app.models.system import ScrapingJob
from app.services.scraper import get_scraper, persist_scraped_to_prospects
from app.services.scraper.base import ScraperError

logger = logging.getLogger("clientfinder.tasks.scraping")


async def _run_job(job_id_str: str) -> int:
    """Async implementation. Returns number of new prospects persisted."""
    jid = UUID(job_id_str)
    async with AsyncSessionLocal() as db:
        job = (
            await db.execute(select(ScrapingJob).where(ScrapingJob.id == jid))
        ).scalar_one_or_none()
        if not job:
            logger.error("Scraping job %s not found", job_id_str)
            return 0

        # Mark running
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.error_message = None
        await db.commit()

        try:
            scraper = get_scraper(job.source)
            query = dict(job.query or {})
            logger.info(
                "Running job %s source=%s query=%s",
                job_id_str,
                job.source,
                query,
            )
            results = await scraper.search(query)
            inserted = await persist_scraped_to_prospects(db, results)

            # Mark completed
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.prospects_found = inserted
            # Log activity
            db.add(
                Activity(
                    prospect_id=None,
                    user_id=job.created_by,
                    action="scraping_job_completed",
                    details={
                        "source": job.source,
                        "results": len(results),
                        "new_prospects": inserted,
                    },
                )
            )
            await db.commit()
            logger.info("Job %s completed: %d new prospects", job_id_str, inserted)

            # T5: auto-enqueue analysis for the just-inserted
            # prospects. We need their DB IDs, so re-query.
            if inserted > 0:
                try:
                    from app.models.prospect import Prospect
                    from app.tasks.analysis_tasks import enrich_prospect_task
                    from sqlalchemy import select, desc

                    # Find the N most-recent prospects whose
                    # company names match the just-inserted ones
                    # (handles the case where 0 were inserted
                    # correctly with no orphan enrichment).
                    inserted_names = [r.company_name for r in results[:inserted]]
                    q = (
                        select(Prospect)
                        .where(Prospect.company_name.in_(inserted_names))
                        .order_by(desc(Prospect.created_at))
                        .limit(inserted)
                    )
                    new_prospects = (await db.execute(q)).scalars().all()
                    for p in new_prospects:
                        try:
                            enrich_prospect_task.delay(str(p.id))
                        except Exception as e:  # noqa: BLE001
                            logger.debug(
                                "Enqueue analysis for %s failed: %s", p.id, e
                            )
                except Exception as e:  # noqa: BLE001
                    logger.debug("Auto-enqueue analysis batch failed: %s", e)

            return inserted
        except ScraperError as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.warning("Job %s failed: %s", job_id_str, e)
            return 0
        except Exception as e:  # noqa: BLE001
            job.status = "failed"
            job.error_message = f"Unexpected error: {e!s}"[:500]
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.exception("Job %s crashed: %s", job_id_str, e)
            return 0


@celery_app.task(name="app.tasks.scraping.run_scraping_job", bind=True, max_retries=0)
def run_scraping_job(self, job_id_str: str) -> int:
    """Celery task entry point. Runs the async impl in a new loop."""
    logger.info("Celery task start: job=%s", job_id_str)
    try:
        return asyncio.run(_run_job(job_id_str))
    except Exception as e:  # noqa: BLE001
        logger.exception("Celery task failed for job %s: %s", job_id_str, e)
        return 0


async def run_scraping_job_sync(job_id_str: str) -> int:
    """Synchronous (in-process) fallback when Celery broker is unavailable.

    Called from the API endpoint when .delay() fails.
    """
    logger.info("Sync fallback start: job=%s", job_id_str)
    return await _run_job(job_id_str)
