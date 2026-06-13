"""
Twitter / Threads scraper — STUB for v1.

Per memory: Nitter is dying, twint/snscrape deprecated, twikit exists
but unstable. Threads DM requires logged-in cookies.

For T4 v1, we return a "coming soon" error so the UI can show
a proper placeholder. Full impl needs:
  1. User provides session cookies (X_AUTH_TOKEN for Twitter,
     X-Session-ID for Threads)
  2. Cookie file mounted into the backend container
  3. Twikit (Twitter) or custom Playwright (Threads)
  4. Rate limiting + rotation logic

Per playbook R7: pragmatic-legal is OK with Playwright+cookies for
Twitter/Threads, but we don't have cookies available yet.
"""
from __future__ import annotations

import logging
from typing import Any

from app.services.scraper.base import BaseScraper, ScraperError

logger = logging.getLogger("clientfinder.scraper.social")


class TwitterScraper(BaseScraper):
    source = "twitter"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    async def search(self, query: dict[str, Any]) -> list:
        raise ScraperError(
            "Twitter scraping coming in T4.5 — needs session cookies. "
            "See docs/scouting.md (TBD) for setup."
        )


class ThreadsScraper(BaseScraper):
    source = "threads"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    async def search(self, query: dict[str, Any]) -> list:
        raise ScraperError(
            "Threads scraping coming in T4.5 — needs logged-in cookies. "
            "See docs/scouting.md (TBD) for setup."
        )
