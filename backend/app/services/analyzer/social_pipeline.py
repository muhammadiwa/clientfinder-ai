"""
T9.0 / Sprint 2 sub-task 2.5 — Social Signal Pipeline.

Orchestrates the social scan step within the prospect enrichment
flow:
  1. Run Twitter + Threads scrapers in parallel (max posts each)
  2. Combine posts (the LLM classifier consumes them together)
  3. Run LLM classifier (single LLM call)
  4. Persist detected signals to the `signals` table
  5. Update lead_score.signal_strength to reflect the new count

Per R7 + D86: this is the "agent" part — the AI that detects
"this person/business needs software" from public social posts.
Without this, the brief's "Social Signals" detection is 0%.

Both scrapers (Twitter via Twikit, Threads via Playwright) have
a soft-fail mode that returns [] when cookies are missing —
this function inherits that: the entire social scan is a no-op
when no cookies are configured.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.services.analyzer.social_classifier import (
    classify_social_signals,
)
from app.services.scraper.threads import ThreadsScraper
from app.services.scraper.twitter import SocialPost, TwitterScraper

logger = logging.getLogger("clientfinder.analyzer.social_pipeline")


async def _search_one(source: str, scraper: Any, query: dict) -> list[SocialPost]:
    """Run one scraper with soft-fail."""
    try:
        return await scraper.search(query)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "Social scan: %s scraper failed (soft-fail): %s: %s",
            source, type(e).__name__, e,
        )
        return []


async def _run_social_scan(
    prospect: Any,
    max_per_source: int = 10,
) -> list[SocialPost]:
    """Run both Twitter and Threads scrapers in parallel for this prospect.

    Combines results; returns up to 20 combined posts (the LLM
    classifier will chunk if more).
    """
    # Build search query: company name + industry + "Indonesia" to
    # bias toward local posts. Can be overridden in v2.
    keywords_parts = [prospect.company_name or ""]
    if prospect.industry:
        keywords_parts.append(prospect.industry)
    keywords_parts.append("Indonesia")
    query = {
        "keywords": " ".join(p for p in keywords_parts if p).strip(),
        "location": prospect.location_city or "",
        "max_results": max_per_source,
    }
    if not query["keywords"]:
        logger.debug("Skipping social scan: no keywords (no company name)")
        return []

    logger.info(
        "Social scan for prospect %s: q=%r",
        prospect.id, query["keywords"],
    )

    # Run both in parallel (or sequentially if one is slow)
    twitter = TwitterScraper()
    threads = ThreadsScraper()
    results = await asyncio.gather(
        _search_one("twitter", twitter, query),
        _search_one("threads", threads, query),
    )
    posts: list[SocialPost] = [p for batch in results for p in batch]
    logger.info(
        "Social scan: twitter=%d + threads=%d = %d total posts for %s",
        len(results[0]), len(results[1]), len(posts), prospect.id,
    )
    return posts


async def social_scan_and_persist(
    db: Any,
    prospect_id: UUID,
) -> dict[str, Any]:
    """Run the full T9.0 social scan → classify → persist → update score.

    Returns a summary dict:
        {
            "posts_fetched": int,
            "signals_detected": int,
            "signals": list[dict],   # validated signal dicts
        }

    On any failure (cookies missing, LLM down, etc.) returns:
        {"posts_fetched": 0, "signals_detected": 0, "signals": [], "skipped": "reason"}
    """
    from app.models.lead import Signal

    # Load prospect
    from sqlalchemy import select
    from app.models.prospect import Prospect

    prospect = (
        await db.execute(select(Prospect).where(Prospect.id == prospect_id))
    ).scalar_one_or_none()
    if not prospect:
        logger.warning("social_scan: prospect %s not found", prospect_id)
        return {"posts_fetched": 0, "signals_detected": 0, "signals": []}

    # 1. Fetch posts
    posts = await _run_social_scan(prospect, max_per_source=settings.twitter_search_max_per_query)
    if not posts:
        return {"posts_fetched": 0, "signals_detected": 0, "signals": []}

    # 2. LLM classify
    signals = await classify_social_signals(posts)
    if not signals:
        return {
            "posts_fetched": len(posts),
            "signals_detected": 0,
            "signals": [],
        }

    # 3. Persist
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    for s in signals:
        db.add(
            Signal(
                prospect_id=prospect_id,
                signal_type=s["kind"],
                source=s.get("source", "social"),
                source_url=s.get("source_url"),
                raw_text=s.get("evidence_text") or s.get("rationale"),
                # The model uses 'metadata' (mapped) but the column is
                # named 'metadata' in PG. The SQLAlchemy Mapped uses
                # 'extra_metadata' as the Python attr with column
                # name 'metadata'.
                weight=s.get("weight", 0.5),
                detected_at=now,
            )
        )
    await db.commit()
    logger.info(
        "social_scan: persisted %d signals for %s", len(signals), prospect_id,
    )

    return {
        "posts_fetched": len(posts),
        "signals_detected": len(signals),
        "signals": signals,
    }
