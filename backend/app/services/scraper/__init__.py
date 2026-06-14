"""
Scraping service — dispatcher + dedup + persist to prospects.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.prospect import Prospect
from app.services.scraper.base import BaseScraper, ScrapedResult
from app.services.scraper.google import GoogleSearchScraper
from app.services.scraper.google_places import GooglePlacesScraper
from app.services.scraper.maps import GoogleMapsScraper
from app.services.scraper.threads import ThreadsScraper
from app.services.scraper.tokopedia import TokopediaScraper
from app.services.scraper.twitter import TwitterScraper
from app.services.scraper.yelp import YelpScraper

logger = logging.getLogger("clientfinder.scraper")


# Scraper registry — source name → class
_SCRAPERS: dict[str, type[BaseScraper]] = {
    "google": GoogleSearchScraper,
    "google_places": GooglePlacesScraper,  # Sprint 3C
    "maps": GoogleMapsScraper,
    "twitter": TwitterScraper,
    "threads": ThreadsScraper,
    "tokopedia": TokopediaScraper,  # Sprint 3C
    "yelp": YelpScraper,  # Sprint 3C
}


def get_scraper(source: str, **kwargs: Any) -> BaseScraper:
    """Instantiate the right scraper for a source."""
    cls = _SCRAPERS.get(source)
    if not cls:
        raise ValueError(f"Unknown scraper source: {source}")
    if source == "google":
        return cls(base_url=settings.searxng_base_url, **kwargs)
    if source == "google_places":
        return cls(api_key=settings.google_places_api_key, **kwargs)
    if source == "yelp":
        return cls(api_key=settings.yelp_api_key, **kwargs)
    return cls(**kwargs)


async def persist_scraped_to_prospects(
    db: AsyncSession,
    results: list[ScrapedResult],
    *,
    skip_duplicates: bool = True,
) -> int:
    """
    Insert scraped results into the prospects table.

    Dedup strategy:
      - Pre-check via SELECT (case-insensitive on company_name + city)
      - Skip if match found
      - Also have a unique partial index
        (uq_prospects_company_city) on the table to catch any
        race-condition duplicates (defense in depth)
    Returns: number of NEW prospects actually inserted.
    """
    if not results:
        return 0

    inserted = 0
    skipped_dup = 0
    for r in results:
        if not r.company_name:
            continue
        # Pre-check for duplicate
        if skip_duplicates:
            existing_q = select(Prospect.id).where(
                Prospect.company_name.ilike(r.company_name)
            )
            if r.location_city:
                existing_q = existing_q.where(
                    Prospect.location_city.ilike(r.location_city)
                )
            existing = (
                (await db.execute(existing_q.limit(1))).scalar_one_or_none()
            )
            if existing:
                logger.debug(
                    "Skip duplicate: %s / %s",
                    r.company_name,
                    r.location_city,
                )
                skipped_dup += 1
                continue

        data = r.to_prospect_dict()
        data["owner_id"] = None
        # Plain insert (no ON CONFLICT — the partial unique index
        # would need expression-based conflict target which PG
        # doesn't support; pre-check + index is enough for v1).
        db.add(Prospect(**data))
        inserted += 1

    try:
        await db.commit()
    except IntegrityError as e:
        # Should be impossible with the pre-check + index, but log
        # if it happens (would indicate a race condition).
        await db.rollback()
        logger.warning("IntegrityError on bulk prospect insert: %s", e)
        # Re-attempt one-by-one to identify and skip the offender
        for r in results:
            if not r.company_name:
                continue
            try:
                data = r.to_prospect_dict()
                data["owner_id"] = None
                db.add(Prospect(**data))
                await db.commit()
                inserted += 1
            except IntegrityError:
                await db.rollback()
                skipped_dup += 1
                continue

    logger.info(
        "Scout persist: %d inserted, %d skipped (duplicate), %d total",
        inserted,
        skipped_dup,
        inserted + skipped_dup,
    )
    return inserted
