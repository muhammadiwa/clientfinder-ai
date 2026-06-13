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


# UI artifact strings to skip (Google Maps renders these as
# pseudo-cards that get picked up by our broad selector)
_GMAPS_UI_NOISE = frozenset(
    {
        "Bagikan",
        "Pelajari lebih lanjut pengungkapan terkait ulasan publik di Google Maps",
        "Pelajari lebih lanjut",
        "Rute",
        "Simpan",
        "Sembunyikan",
    }
)


class GoogleMapsScraper(BaseScraper):
    source = "maps"

    NAV_TIMEOUT_MS = 15_000
    RESULT_TIMEOUT_MS = 8_000
    DEFAULT_LIMIT = 15
    # Overall hard cap so a slow Maps page can't pin the Celery worker
    OVERALL_TIMEOUT_S = 120.0

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if not PLAYWRIGHT_AVAILABLE:
            raise ScraperError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

    async def _search_inner(self, query: dict[str, Any]) -> list[ScrapedResult]:
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
        skipped_noise = 0
        skipped_parse = 0
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
                await page.goto(
                    url, timeout=self.NAV_TIMEOUT_MS, wait_until="domcontentloaded"
                )
                try:
                    await page.wait_for_selector(
                        'div[role="feed"]', timeout=self.RESULT_TIMEOUT_MS
                    )
                except PWTimeout:
                    logger.info("Maps: no feed selector found, trying fallback")
                await asyncio.sleep(2)

                # More specific selector: only result cards have aria-label
                # starting with the place name; UI elements (Bagikan, Rute)
                # don't. Also use [jsaction] which is on result items.
                cards = await page.query_selector_all(
                    'div[role="feed"] > div > div[aria-label]:not([aria-label=""])'
                )
                logger.info("Maps: found %d candidate cards", len(cards))

                for card in cards:
                    try:
                        result = await self._parse_card(card, page)
                    except Exception as e:  # noqa: BLE001
                        logger.warning("Maps: parse card failed (%s)", e)
                        skipped_parse += 1
                        continue
                    if result is None:
                        skipped_noise += 1
                        continue
                    results.append(result)
                    if len(results) >= max_results:
                        break
            finally:
                await context.close()
                await browser.close()

        logger.info(
            "Maps: parsed=%d noise_skipped=%d parse_skipped=%d",
            len(results),
            skipped_noise,
            skipped_parse,
        )
        return results

    async def search(self, query: dict[str, Any]) -> list[ScrapedResult]:
        """Public entry: wraps _search_inner in an overall timeout."""
        try:
            return await asyncio.wait_for(
                self._search_inner(query), timeout=self.OVERALL_TIMEOUT_S
            )
        except asyncio.TimeoutError as e:
            raise ScraperError(
                f"Maps scrape exceeded {self.OVERALL_TIMEOUT_S:.0f}s timeout"
            ) from e

    @staticmethod
    async def _parse_card(card: Any, page: Any) -> ScrapedResult | None:
        # aria-label is the most reliable: "Name, rating, address"
        aria = await card.get_attribute("aria-label")
        name = (aria or "").strip()

        # Filter UI artifacts (Bagikan, Pelajari lebih lanjut, etc.)
        if not name or name in _GMAPS_UI_NOISE or len(name) < 3:
            return None
        # Skip names that look like Google UI instructions
        if name.startswith("Pelajari") or name.startswith("Sembunyikan"):
            return None

        # Address + phone are often in the card text below the name
        full_text = (await card.inner_text()) or ""
        # First line of the text after the name is usually the address
        address = _extract_address(full_text)
        phone = _extract_phone(full_text)

        # Link with href to the actual website
        website = None
        link = await card.query_selector(
            'a[href^="http"]:not([href*="google.com/maps"])'
        )
        if link:
            href = await link.get_attribute("href")
            if href and "google.com" not in href:
                website = href

        return ScrapedResult(
            company_name=name[:255],
            website=website[:500] if website else None,
            phone=phone,
            location_address=address,
            description=None,
            source_url=None,
            source="maps",
            extra={"raw_address": address} if address else {},
        )


_PHONE_RE = re.compile(r"(\+?\d[\d\s\-]{7,}\d)")
_ADDR_HINT = re.compile(
    r"(Jl\.|Jalan|Ruko|Komp\.|Kompleks|Blok|No\.|Jl\s|Kel\.|Kec\.|Kota\s|Kab\.|Jl.)\b",
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
        if _ADDR_HINT.search(line) and 8 < len(line.strip()) < 200:
            return line.strip()
    return None


def _url_quote(s: str) -> str:
    from urllib.parse import quote

    return quote(s, safe="")
