"""
Scraper service base — abstract scraper interface.

Per playbook R7 (pragmatic-legal stance) and R8 (scraping scope v1):
- Google Search (via SearXNG meta-search)
- Google Maps (via Playwright, no API key needed)
- Twitter (stub: requires logged-in cookies, T4.5)
- Threads (stub: requires logged-in cookies, T4.5)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScrapedResult:
    """Normalized prospect data from any scraper source."""

    company_name: str
    website: str | None = None
    phone: str | None = None
    email: str | None = None
    location_city: str | None = None
    location_province: str | None = None
    location_address: str | None = None
    description: str | None = None
    source_url: str | None = None
    source: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_prospect_dict(self) -> dict[str, Any]:
        """Convert to dict matching the Prospect ORM model fields."""
        return {
            "company_name": self.company_name,
            "website": self.website,
            "phone": self.phone,
            "email": self.email,
            "location_city": self.location_city,
            "location_province": self.location_province,
            # location_address is a T4.5+ field; not yet on Prospect model,
            # so we stash it in raw_data for v1.
            "description": self.description,
            "source_url": self.source_url,
            "source": self.source,
            "raw_data": {**self.extra, "location_address": self.location_address}
            if self.location_address
            else self.extra,
            "status": "new",
        }


class ScraperError(Exception):
    """Raised when a scraper fails. Stored in ScrapingJob.error_message."""


class BaseScraper(ABC):
    """Abstract base class for all scout scrapers."""

    source: str  # e.g. "google", "maps", "twitter", "threads"

    def __init__(self, **kwargs: Any) -> None:
        self.options = kwargs

    @abstractmethod
    async def search(self, query: dict[str, Any]) -> list[ScrapedResult]:
        """
        Execute the search and return normalized results.

        `query` schema (varies per source, common fields):
          - keywords: list[str] | str  (search terms)
          - location: str | None  (e.g. "Jakarta", "Bandung")
          - max_results: int  (cap, default 20)
        """
        raise NotImplementedError
