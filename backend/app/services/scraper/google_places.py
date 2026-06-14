"""
Google Places API scraper — Sprint 3C.

Per the 2026-06-14 audit, ~67% of SearXNG-backed Google Search
results were noise (gibberish spam, listicles, marketplaces).
The Google Places API (Text Search + Place Details) returns
structured business data — name, address, phone, website,
rating — with much higher signal-to-noise ratio for the
UMKM use case.

This scraper is the new structured-source alternative to
the noisy `google.py` (SearXNG). The kill switch
`scout_google_enabled` still defaults to False; the new
`scout_google_places_enabled` defaults to False and
requires the operator to set `google_places_api_key` first.

Per R7 (pragmatic-legal): Google Places API is a paid
service, but has a generous $200/mo free tier (~28k calls).
Set the env var and enable the kill switch to activate.
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.services.scraper.base import BaseScraper, ScraperError, ScrapedResult

logger = logging.getLogger("clientfinder.scraper.google_places")

PLACES_TEXTSEARCH_URL = (
    "https://maps.googleapis.com/maps/api/place/textsearch/json"
)
PLACES_DETAILS_URL = (
    "https://maps.googleapis.com/maps/api/place/details/json"
)


def _normalize_phone(phone: str | None) -> str | None:
    """Google Places returns phones in international format
    already (e.g. '+62 22 1234 5678'). We strip spaces for
    consistency with the rest of the codebase."""
    if not phone:
        return None
    return phone.replace(" ", "").strip() or None


def _extract_domain(url: str | None) -> str | None:
    if not url:
        return None
    try:
        p = urlparse(url)
        return p.netloc.replace("www.", "") or None
    except Exception:  # noqa: BLE001
        return None


class GooglePlacesScraper(BaseScraper):
    source = "google_places"

    def __init__(self, api_key: str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.api_key = api_key or settings.google_places_api_key
        if not self.api_key:
            logger.warning(
                "GooglePlacesScraper initialized without API key — "
                "calls will fail until GOOGLE_PLACES_API_KEY is set",
            )

    async def search(self, query: dict[str, Any]) -> list[ScrapedResult]:
        """Search Google Places for businesses matching the query.

        `query` schema (same as BaseScraper):
          - keywords: str (search terms, e.g. "klinik gigi Bandung")
          - location: str (optional, e.g. "Bandung, Indonesia")
          - max_results: int (cap; default settings)

        Returns: list of ScrapedResult. Empty list on any error
        (no exception raised per the R7 graceful-degradation
        pattern from the social scrapers).
        """
        if not self.api_key:
            logger.warning(
                "GooglePlacesScraper.search: no API key, returning []"
            )
            return []

        keywords = (query.get("keywords") or query.get("q") or "").strip()
        if isinstance(keywords, list):
            keywords = " ".join(keywords)
        if not keywords:
            return []
        location = (query.get("location") or "").strip()
        max_results = int(
            query.get("max_results")
            or settings.scout_google_places_max_per_query
        )

        full_query = f"{keywords} {location}".strip() if location else keywords

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                resp = await client.get(
                    PLACES_TEXTSEARCH_URL,
                    params={
                        "query": full_query,
                        "key": self.api_key,
                        "region": "id",  # bias to Indonesia
                    },
                )
            except httpx.HTTPError as e:
                logger.warning("Google Places textsearch failed: %s", e)
                return []
            if resp.status_code != 200:
                logger.warning(
                    "Google Places textsearch HTTP %d: %s",
                    resp.status_code, resp.text[:200],
                )
                return []
            data = resp.json()
            if data.get("status") not in ("OK", "ZERO_RESULTS"):
                logger.warning(
                    "Google Places API error: %s — %s",
                    data.get("status"), data.get("error_message", "")[:200],
                )
                return []

            results: list[ScrapedResult] = []
            for place in (data.get("results") or [])[:max_results]:
                scraped = self._to_scraped_result(place)
                if scraped:
                    results.append(scraped)
            logger.info(
                "Google Places: %d results for q=%r",
                len(results), full_query,
            )
            return results

    def _to_scraped_result(self, place: dict) -> ScrapedResult | None:
        """Convert a Places API result to our ScrapedResult contract.

        Note: Text Search doesn't include phone/website directly.
        We'd need a follow-up Place Details call for those fields.
        For v1 we return what we have (name, address, rating)
        and let the T8.6 HomepageEnricher fill in phone/email
        if the website is present.
        """
        name = (place.get("name") or "").strip()
        if not name:
            return None
        address = (place.get("formatted_address") or "").strip() or None
        # Split address into city/province heuristically.
        # Google Places format: "street, city, state, country"
        # (e.g. "Jl. Asia Afrika, Bandung, West Java, Indonesia")
        location_city = None
        location_province = None
        if address:
            parts = [p.strip() for p in address.split(",")]
            if len(parts) >= 3:
                # City is the second segment, province is the third
                location_city = parts[1]
                location_province = (
                    parts[2] if "Indonesia" not in parts[2] else None
                )
        return ScrapedResult(
            company_name=name,
            website=None,  # Place Details (separate call) needed
            description=None,
            source=self.source,
            source_url=place.get("icon") or None,
            location_address=address,
            location_city=location_city,
            location_province=location_province,
            extra={
                "place_id": place.get("place_id"),
                "rating": place.get("rating"),
                "user_ratings_total": place.get("user_ratings_total"),
                "types": place.get("types", []),
                "business_status": place.get("business_status"),
                "geometry": place.get("geometry"),
            },
        )
