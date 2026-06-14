"""
Threads scraper — STUB for v1.

T9.0 sub-task 2.2 will replace this with a Playwright-based
implementation (or twikit-style GraphQL scraper; both are
fragile and need cookie-based auth).

For now we keep the stub so the ScraperSource union still
validates and the UI doesn't break.
"""
from __future__ import annotations

import logging
from typing import Any

from app.services.scraper.base import BaseScraper, ScraperError

logger = logging.getLogger("clientfinder.scraper.threads")


class ThreadsScraper(BaseScraper):
    source = "threads"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    async def search(self, query: dict[str, Any]) -> list:
        raise ScraperError(
            "Threads scraping coming in T9.0 / sub-task 2.2 — "
            "needs logged-in cookies + Playwright. "
            "See docs/SCOUT_ENRICHMENT_SPEC.md and "
            "scripts/setup_social_cookies.py."
        )
