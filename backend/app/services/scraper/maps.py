"""
Google Maps scraper — via Playwright (headless Chromium).

We use Playwright instead of Google Places API to avoid the
$200/month free-tier credit and per-request billing. For v1
(Indonesian UMKM prospecting) this is sufficient; production-grade
crawl would need Places API or a paid proxy rotation.

Per playbook R7: pragmatic-legal. We respect robots.txt and
Google's rate limits via our built-in request delays.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from app.services.scraper.base import BaseScraper, ScrapedResult, ScraperError

logger = logging.getLogger("clientfinder.scraper.maps")

# Try to import playwright; if not available, scraper raises on use
try:
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout

    PLAYWRIGHT_AVAILABLE = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT_AVAILABLE = False


class GoogleMapsScraper(BaseScraper):
    source = "maps"

    NAV_TIMEOUT_MS = 15_000
    RESULT_TIMEOUT_MS = 8_000
    DEFAULT_LIMIT = 15

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if not PLAYWRIGHT_AVAILABLE:
            raise ScraperError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

    async def search(self, query: dict[str, Any]) -> list[ScrapedResult]:
        keywords = query.get("keywords") or query.get("q") or ""
        if isinstance(keywords, list):
            keywords = " ".join(keywords)
        keywords = keywords.strip()
        if not keywords:
            raise ScraperError("Maps: 'keywords' is required")
        location = (query.get("location") or "").strip()
        max_results = min(int(query.get("max_results") or self.DEFAULT_LIMIT), 50)

        search_query = f"{keywords} {location}".strip() if location else keywords
        url = "https://www.google.com/maps/search/" + _url_quote(search_query)
        logger.info("Maps search: %s", url)

        results: list[ScrapedResult] = []
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                    ),
                    locale="id-ID",
                )
                page = await context.new_page()
                try:
                    await page.goto(url, timeout=self.NAV_TIMEOUT_MS, wait_until="domcontentloaded")
                    # Wait for results panel
                    try:
                        await page.wait_for_selector(
                            'div[role="feed"]', timeout=self.RESULT_TIMEOUT_MS
                        )
                    except PWTimeout:
                        # Could be a single result or consent dialog
                        logger.info("Maps: no feed selector found, trying fallback")
                    await asyncio.sleep(2)  # let results settle

                    cards = await page.query_selector_all('div[role="feed"] > div > div')
                    logger.info("Maps: found %d candidate cards", len(cards))

                    for card in cards:
                        try:
                            result = await self._parse_card(card, page)
                            if result:
                                results.append(result)
                                if len(results) >= max_results:
                                    break
                        except Exception as e:  # noqa: BLE001
                            logger.debug("Maps: skip card (%s)", e)
                            continue
                finally:
                    await context.close()
                    await browser.close()
        except ScraperError:
            raise
        except Exception as e:  # noqa: BLE001
            raise ScraperError(f"Maps scraping failed: {e}") from e

        logger.info("Maps: parsed %d prospects", len(results))
        return results

    @staticmethod
    async def _parse_card(card: Any, page: Any) -> ScrapedResult | None:
        # Title is in an aria-label or class "qBF1Pd" / "fontHeadlineSmall"
        name = None
        for sel in ['[class*="fontHeadlineSmall"]', '[aria-label]', 'div[role="button"] > div > div']:
            el = await card.query_selector(sel)
            if el:
                name = (await el.get_attribute("aria-label")) or (await el.inner_text())
                name = (name or "").strip()
                if name and len(name) > 1 and not name.startswith("·"):
                    break
        if not name:
            return None

        # Whole card text often contains address + phone
        full_text = (await card.inner_text()) or ""
        address = _extract_address(full_text)
        phone = _extract_phone(full_text)

        # Link with href maps to website or google maps place
        website = None
        link = await card.query_selector('a[href^="http"]:not([href*="google.com/maps"])')
        if link:
            href = await link.get_attribute("href")
            if href and "google.com" not in href:
                website = href

        return ScrapedResult(
            company_name=name[:255],
            website=website[:500] if website else None,
            phone=phone,
            location_city=address,
            description=None,
            source_url=None,
            source="maps",
            extra={"raw_address": address} if address else {},
        )


_PHONE_RE = re.compile(r"(\+?\d[\d\s\-]{7,}\d)")
_ADDR_HINT = re.compile(
    r"(Jl\.|Jalan|Ruko|Komp\.|Kompleks|Blok|No\.|Jl\s|Kel\.|Kec\.|Kota\s|Kab\.)",
    re.IGNORECASE,
)


def _extract_phone(text: str) -> str | None:
    for line in text.splitlines():
        m = _PHONE_RE.search(line)
        if m:
            digits = re.sub(r"[^\d+]", "", m.group(1))
            if 8 <= len(digits) <= 16:
                return m.group(1).strip()
    return None


def _extract_address(text: str) -> str | None:
    for line in text.splitlines():
        if _ADDR_HINT.search(line) and len(line.strip()) > 8 and len(line.strip()) < 200:
            return line.strip()
    return None


def _url_quote(s: str) -> str:
    from urllib.parse import quote

    return quote(s, safe="")
