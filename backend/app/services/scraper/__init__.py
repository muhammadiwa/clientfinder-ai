"""
Scraping service — dispatcher + dedup + persist to prospects.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.prospect import Prospect
from app.services.scraper.base import BaseScraper, ScrapedResult
from app.services.scraper.google import GoogleSearchScraper
from app.services.scraper.maps import GoogleMapsScraper
from app.services.scraper.twitter import ThreadsScraper, TwitterScraper

logger = logging.getLogger("clientfinder.scraper")


# Scraper registry — source name → class
_SCRAPERS: dict[str, type[BaseScraper]] = {
    "google": GoogleSearchScraper,
    "maps": GoogleMapsScraper,
    "twitter": TwitterScraper,
    "threads": ThreadsScraper,
}


def get_scraper(source: str, **kwargs: Any) -> BaseScraper:
    """Instantiate the right scraper for a source."""
    cls = _SCRAPERS.get(source)
    if not cls:
        raise ValueError(f"Unknown scraper source: {source}")
    if source == "google":
        return cls(base_url=settings.searxng_base_url, **kwargs)
    return cls(**kwargs)


async def persist_scraped_to_prospects(
    db: AsyncSession,
    results: list[ScrapedResult],
    *,
    skip_duplicates: bool = True,
) -> int:
    """
    Insert scraped results into the prospects table.

    Dedup strategy (when skip_duplicates=True):
      - Skip if (company_name, location_city) already exists
        (case-insensitive). For v1 this is sufficient; v2 can add
        email/website-based dedup.

    Returns: number of NEW prospects inserted.
    """
    if not results:
        return 0

    inserted = 0
    for r in results:
        # Build dedup query
        if skip_duplicates and r.company_name:
            existing_q = select(Prospect.id).where(
                Prospect.company_name.ilike(r.company_name)
            )
            if r.location_city:
                existing_q = existing_q.where(
                    Prospect.location_city.ilike(r.location_city)
                )
            existing = (await db.execute(existing_q.limit(1))).scalar_one_or_none()
            if existing:
                logger.debug("Skip duplicate: %s / %s", r.company_name, r.location_city)
                continue

        data = r.to_prospect_dict()
        data["owner_id"] = None  # scout-found, no specific owner yet
        # Use ON CONFLICT DO NOTHING as belt-and-suspenders
        stmt = (
            pg_insert(Prospect)
            .values(**data)
            .on_conflict_do_nothing()
        )
        await db.execute(stmt)
        inserted += 1

    await db.commit()
    logger.info("Persisted %d new prospects from scrape", inserted)
    return inserted
