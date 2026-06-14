"""
Yelp Fusion API scraper — Sprint 3C.

Per the brief, Yelp is a structured source for business
discovery (F&B, retail, klinik, salon — the industries
where Yelp has good coverage). The Fusion API is free
with 5000 daily calls.

Per R7: Yelp's terms require displaying attribution
when showing reviews. For the v1 scraper, we just
ingest the business data (name, address, phone,
rating) and the attribution requirement kicks in
only when the UI shows reviews.
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.services.scraper.base import BaseScraper, ScrapedResult

logger = logging.getLogger("clientfinder.scraper.yelp")

YELP_SEARCH_URL = "https://api.yelp.com/v3/businesses/search"


def _extract_domain(url: str | None) -> str | None:
    if not url:
        return None
    try:
        p = urlparse(url)
        return p.netloc.replace("www.", "") or None
    except Exception:  # noqa: BLE001
        return None


def _normalize_phone(phone: str | None) -> str | None:
    """Yelp returns phones in '+1xxx' (US) or local format
    depending on region. We keep as-is and let downstream
    channel_selector handle it."""
    return phone or None


class YelpScraper(BaseScraper):
    source = "yelp"

    def __init__(self, api_key: str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.api_key = api_key or settings.yelp_api_key
        if not self.api_key:
            logger.warning(
                "YelpScraper initialized without API key — "
                "calls will fail until YELP_API_KEY is set",
            )

    async def search(self, query: dict[str, Any]) -> list[ScrapedResult]:
        """Search Yelp for businesses matching the query.

        `query` schema (same as BaseScraper):
          - keywords: str (e.g. "kafe")
          - location: str (REQUIRED by Yelp — e.g. "Bandung, ID")
          - max_results: int (Yelp hard cap is 50, default 30)

        Returns: list of ScrapedResult. Empty list on any error.
        """
        if not self.api_key:
            logger.warning(
                "YelpScraper.search: no API key, returning []"
            )
            return []

        keywords = (query.get("keywords") or query.get("q") or "").strip()
        if isinstance(keywords, list):
            keywords = " ".join(keywords)
        location = (query.get("location") or "").strip()
        if not location:
            # Yelp REQUIRES a location. If missing, fall back to
            # "Indonesia" (broad but legal per Yelp terms).
            location = "Indonesia"
        max_results = min(
            int(query.get("max_results") or settings.scout_yelp_max_per_query),
            50,  # Yelp hard cap
        )

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                resp = await client.get(
                    YELP_SEARCH_URL,
                    params={
                        "term": keywords,
                        "location": location,
                        "limit": max_results,
                        "locale": "id_ID",  # Indonesian locale
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                    },
                )
            except httpx.HTTPError as e:
                logger.warning("Yelp search failed: %s", e)
                return []
            if resp.status_code != 200:
                logger.warning(
                    "Yelp HTTP %d: %s",
                    resp.status_code, resp.text[:200],
                )
                return []
            data = resp.json()
            results: list[ScrapedResult] = []
            for biz in (data.get("businesses") or []):
                scraped = self._to_scraped_result(biz)
                if scraped:
                    results.append(scraped)
            logger.info(
                "Yelp: %d results for q=%r loc=%r",
                len(results), keywords, location,
            )
            return results

    def _to_scraped_result(self, biz: dict) -> ScrapedResult | None:
        name = (biz.get("name") or "").strip()
        if not name:
            return None
        loc = biz.get("location") or {}
        address_parts = loc.get("display_address") or []
        address = ", ".join(address_parts) if address_parts else None
        city = loc.get("city")
        state = loc.get("state")
        country = loc.get("country")
        website = _extract_domain(biz.get("url"))
        return ScrapedResult(
            company_name=name,
            website=website,
            description=None,
            source=self.source,
            source_url=biz.get("url"),
            location_address=address,
            location_city=city,
            location_province=state,
            phone=_normalize_phone(biz.get("phone")),
            extra={
                "yelp_id": biz.get("id"),
                "alias": biz.get("alias"),
                "rating": biz.get("rating"),
                "review_count": biz.get("review_count"),
                "categories": [
                    c.get("title") for c in biz.get("categories") or []
                ],
                "price": biz.get("price"),
                "coordinates": biz.get("coordinates"),
                "is_closed": biz.get("is_closed"),
                "country": country,
            },
        )
