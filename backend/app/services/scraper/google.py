"""
Google Search scraper — via local SearXNG instance.

SearXNG is a free, open-source meta-search engine. We run it
locally in docker-compose (port 8888). It aggregates Google +
DuckDuckGo + Bing + Brave + others, so we get diversity without
hitting Google directly.

Per playbook R7: pragmatic-legal, no API key, no ToS violation.
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import httpx

from app.services.scraper.base import BaseScraper, ScrapedResult, ScraperError

logger = logging.getLogger("clientfinder.scraper.google")


class GoogleSearchScraper(BaseScraper):
    source = "google"

    DEFAULT_TIMEOUT = 30.0
    SEARXNG_PATH = "/search"

    def __init__(self, base_url: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Normalize: strip trailing slash
        self.base_url = base_url.rstrip("/")

    async def search(self, query: dict[str, Any]) -> list[ScrapedResult]:
        keywords = query.get("keywords") or query.get("q") or ""
        if isinstance(keywords, list):
            keywords = " ".join(keywords)
        keywords = keywords.strip()
        if not keywords:
            raise ScraperError("Google: 'keywords' is required")

        location = (query.get("location") or "").strip()
        max_results = int(query.get("max_results") or 20)
        full_query = f"{keywords} {location}".strip() if location else keywords

        params = {
            "q": full_query,
            "format": "json",
            "language": "id",
            "safesearch": "0",
        }
        url = f"{self.base_url}{self.SEARXNG_PATH}"

        logger.info("SearXNG request: %s q=%r", url, full_query)

        try:
            async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            raise ScraperError(f"SearXNG request failed: {e}") from e
        except Exception as e:  # noqa: BLE001
            raise ScraperError(f"SearXNG parse failed: {e}") from e

        results = data.get("results") or []
        logger.info("SearXNG returned %d raw results", len(results))

        scraped: list[ScrapedResult] = []
        for r in results:
            try:
                parsed = self._parse_searxng_result(r)
            except Exception as e:  # noqa: BLE001
                logger.debug("Skipping malformed result: %s", e)
                continue
            if parsed:
                scraped.append(parsed)
            if len(scraped) >= max_results:
                break

        logger.info("Parsed %d prospects from SearXNG", len(scraped))
        return scraped

    @staticmethod
    def _extract_domain(url: str | None) -> str | None:
        if not url:
            return None
        try:
            host = urlparse(url).netloc.lower()
            # Strip www.
            if host.startswith("www."):
                host = host[4:]
            return host or None
        except Exception:  # noqa: BLE001
            return None

    @classmethod
    def _parse_searxng_result(cls, r: dict[str, Any]) -> ScrapedResult | None:
        title = (r.get("title") or "").strip()
        url = (r.get("url") or "").strip()
        content = (r.get("content") or "").strip()

        if not title or not url:
            return None

        domain = cls._extract_domain(url)
        # Use domain as company name if title is generic
        company = title
        # If title looks like "Foo - Bar", try to take the first part
        for sep in [" | ", " - ", " — ", " · "]:
            if sep in title:
                company = title.split(sep)[0].strip()
                break

        return ScrapedResult(
            company_name=company[:255],
            website=url[:500],
            description=content or None,
            source_url=url[:500],
            source="google",
            extra={
                "engine": r.get("engine"),
                "domain": domain,
                "raw_title": title,
            },
        )
