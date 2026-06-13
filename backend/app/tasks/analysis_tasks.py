"""
Analysis tasks — Celery tasks for T5 (Analyst module).

Two functions:
- enrich_prospect_task (Celery task, async, background)
- enrich_prospect_task_sync (fallback when broker unavailable)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.activity import Activity
from app.models.prospect import Prospect

logger = logging.getLogger("clientfinder.tasks.analysis")


async def _enrich_job(prospect_id_str: str, **kwargs: Any) -> dict[str, Any]:
    """Async implementation. Returns enrichment summary dict."""
    from app.services.analyzer.orchestrator import enrich_prospect

    pid = UUID(prospect_id_str)

    # Update prospect status to 'enriching' (transient state)
    async with AsyncSessionLocal() as db:
        prospect = (
            await db.execute(select(Prospect).where(Prospect.id == pid))
        ).scalar_one_or_none()
        if not prospect:
            return {"ok": False, "error": "not_found"}
        # Mark as enriching for the duration
        previous_status = prospect.status
        if prospect.status == "new":
            prospect.status = "enriching"
            await db.commit()

    # Run the enrichment
    summary = await enrich_prospect(pid, **kwargs)

    # Mark as 'scored' if successful
    if summary.get("ok"):
        async with AsyncSessionLocal() as db:
            prospect = (
                await db.execute(select(Prospect).where(Prospect.id == pid))
            ).scalar_one_or_none()
            if prospect:
                prospect.status = "scored"
                await db.commit()
            db.add(
                Activity(
                    prospect_id=pid,
                    user_id=prospect.owner_id if prospect else None,
                    action="analysis_completed",
                    details={
                        "grade": summary.get("grade"),
                        "total_score": summary.get("total_score"),
                    },
                )
            )
            await db.commit()
    return summary


@celery_app.task(name="app.tasks.analysis.enrich_prospect", bind=True, max_retries=2)
def enrich_prospect_task(self, prospect_id_str: str, **kwargs: Any) -> dict[str, Any]:
    """Celery task entry point. Runs the async impl in a new loop."""
    logger.info("Celery task start: enrich_prospect=%s", prospect_id_str)
    try:
        return asyncio.run(_enrich_job(prospect_id_str, **kwargs))
    except Exception as e:  # noqa: BLE001
        logger.exception("Celery task failed for %s: %s", prospect_id_str, e)
        return {"ok": False, "error": f"task_crashed: {e!s}"}


async def enrich_prospect_task_sync(
    prospect_id_str: str, **kwargs: Any
) -> dict[str, Any]:
    """Synchronous (in-process) fallback when Celery broker is unavailable."""
    logger.info("Sync fallback start: enrich_prospect=%s", prospect_id_str)
    return await _enrich_job(prospect_id_str, **kwargs)


async def enrich_batch(prospect_ids: list[str], **kwargs: Any) -> list[dict]:
    """
    Enrich a batch of prospects sequentially (for now).

    Returns a list of summary dicts.
    """
    results = []
    for pid in prospect_ids:
        try:
            r = await enrich_prospect_task_sync(pid, **kwargs)
            results.append(r)
        except Exception as e:  # noqa: BLE001
            logger.exception("Batch enrich failed for %s: %s", pid, e)
            results.append({"ok": False, "error": str(e), "prospect_id": pid})
    return results
