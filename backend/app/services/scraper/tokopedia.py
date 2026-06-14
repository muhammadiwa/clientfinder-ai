"""
Tokopedia seller search scraper — Sprint 3C sub-task 2.

Per the brief: Tokopedia is one of the 4 Scout data sources
(Social Media, Threads/X, Business Directory, **Search
Engine / Marketplace**). The "Search Engine" bucket in the
Indonesian context means Tokopedia (the largest marketplace).

Tokopedia has no public seller-search API. We use Playwright
to scrape the public search page, then extract seller
information via JavaScript (more robust than CSS selectors
since Tokopedia changes the DOM frequently).

Per R7 (pragmatic-legal): marketplace scraping is a grey
area. Per the brief, we only collect publicly-visible seller
data (shop name, location, product count) and skip reviews
or private information. Soft-fail by default.

Per R10: no auto-send. The Scout worker just persists the
discovered shop as a Prospect for the operator to review.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from urllib.parse import quote_plus

from app.core.config import settings
from app.services.scraper.base import BaseScraper, ScraperError, ScrapedResult

logger = logging.getLogger("clientfinder.scraper.tokopedia")

# Lazy import — playwright is an optional dep (only used by
# Maps/Threads/Tokopedia). Set to None if not installed; the
# _fetch_with_playwright method raises ScraperError in that
# case. Module-level so tests can patch it via the standard
# `with patch("...async_playwright"):` pattern.
try:
    from playwright.async_api import async_playwright  # type: ignore
except ImportError:
    async_playwright = None  # type: ignore

# Public search URL. We use the search page (not the seller-search
# sub-page) because it returns product cards with shop name +
# location — which is what we need for prospect discovery.
TOKOPEDIA_SEARCH_URL = "https://www.tokopedia.com/search?q={q}"


# JavaScript that runs inside the page to extract seller info
# from product cards. Tries multiple strategies since Tokopedia
# changes the DOM frequently. Returns a list of dicts.
_EXTRACT_SELLERS_JS = """
() => {
  const results = [];
  // Strategy 1: <div data-testid="..."> cards (most common in 2024-2026)
  const cards = document.querySelectorAll('[data-testid="divProduct"], [data-testid="master-product-card"]');
  cards.forEach(card => {
    const name = card.querySelector('[data-testid="spnProductName"], .prd_link-product-name')?.textContent?.trim() || '';
    const link = card.querySelector('a[href*="tokopedia.com/"]')?.href || '';
    const price = card.querySelector('[data-testid="spnProductPrice"]')?.textContent?.trim() || '';
    // Shop name is usually in a span with class "prd_link-shop-name"
    // or "css-..." (hashed class). We try multiple selectors.
    const shopEl = card.querySelector('.prd_link-shop-name, [data-testid*="ShopName"], .css-1kr22w3');
    const shop = shopEl ? shopEl.textContent.trim() : '';
    // Location is often in a span near the shop name
    const locEl = card.querySelector('.prd_link-shop-loc, [data-testid*="shopLocation"], .css-1k1c2pb');
    const loc = locEl ? locEl.textContent.trim() : '';
    // Sold/rating is in a separate span
    const ratingEl = card.querySelector('[data-testid*="Rating"], .prd_rating-average-text, .css-tx1e9a');
    const rating = ratingEl ? ratingEl.textContent.trim() : '';
    if (shop && link) {
      results.push({shop, name, price, location: loc, rating, link});
    }
  });
  // Fallback: any element with "shop" in class
  if (results.length === 0) {
    document.querySelectorAll('[class*="shop-name"], [class*="seller-name"]').forEach(el => {
      const shop = el.textContent.trim();
      // Walk up to find the parent card
      const card = el.closest('div[class*="css-"]');
      if (card && shop) {
        const link = card.querySelector('a[href*="tokopedia.com/"]')?.href || '';
        const loc = card.querySelector('[class*="shop-loc"], [class*="location"]')?.textContent?.trim() || '';
        if (link) {
          results.push({shop, name: '', price: '', location: loc, rating: '', link});
        }
      }
    });
  }
  return results;
}
"""


def _normalize_phone(phone: str | None) -> str | None:
    return phone or None


class TokopediaScraper(BaseScraper):
    source = "tokopedia"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    async def search(self, query: dict[str, Any]) -> list[ScrapedResult]:
        """Search Tokopedia for sellers matching the query.

        `query` schema (same as BaseScraper):
          - keywords: str (search terms, e.g. "kopi bandung")
          - location: str (optional, e.g. "Bandung")
          - max_results: int (cap; default settings.scout_tokopedia_max_per_query)

        Returns: list of ScrapedResult (deduplicated by shop name).
        Empty list on any error (no exception raised per the
        R7 graceful-degradation pattern).
        """
        if not settings.scout_tokopedia_enabled:
            logger.debug("Tokopedia scraper disabled (scout_tokopedia_enabled=False)")
            return []
        keywords = (query.get("keywords") or query.get("q") or "").strip()
        if isinstance(keywords, list):
            keywords = " ".join(keywords)
        if not keywords:
            return []
        location = (query.get("location") or "").strip()
        max_results = int(
            query.get("max_results") or settings.scout_tokopedia_max_per_query
        )
        full_query = f"{keywords} {location}".strip() if location else keywords

        url = TOKOPEDIA_SEARCH_URL.format(q=quote_plus(full_query))
        logger.info("Tokopedia search: q=%r url=%s", full_query, url)

        try:
            rows = await asyncio.wait_for(
                self._fetch_with_playwright(url),
                timeout=settings.scout_tokopedia_page_timeout_s + 5,
            )
        except TimeoutError:
            logger.warning("Tokopedia: timeout fetching %s", url)
            return []
        except ImportError:
            logger.warning("Tokopedia: playwright not installed")
            return []
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "Tokopedia: search failed (soft-fail): %s: %s",
                type(e).__name__, e,
            )
            return []

        # Dedup by shop name
        seen: set[str] = set()
        results: list[ScrapedResult] = []
        for row in rows:
            shop = (row.get("shop") or "").strip()
            if not shop or shop in seen:
                continue
            seen.add(shop)
            link = (row.get("link") or "").strip()
            location_text = (row.get("location") or "").strip()
            # Try to split "Kab. Bandung" or "Kota Bandung" into a city
            location_city = None
            if location_text:
                # Remove "Kota " / "Kab. " prefix
                cleaned = location_text
                for prefix in ("Kota ", "Kab. ", "Kabupaten "):
                    if cleaned.startswith(prefix):
                        cleaned = cleaned[len(prefix):]
                        break
                location_city = cleaned or None
            results.append(
                ScrapedResult(
                    company_name=shop,
                    website=None,  # Tokopedia seller pages don't expose external site
                    description=(row.get("name") or "")[:500] or None,
                    source=self.source,
                    source_url=link or None,
                    location_address=None,
                    location_city=location_city,
                    location_province=None,
                    phone=None,
                    extra={
                        "sample_product": (row.get("name") or "")[:200],
                        "sample_price": row.get("price") or "",
                        "rating": row.get("rating") or "",
                        "search_query": full_query,
                    },
                )
            )
            if len(results) >= max_results:
                break
        logger.info("Tokopedia: %d unique sellers for q=%r", len(results), full_query)
        return results

    async def _fetch_with_playwright(self, url: str) -> list[dict]:
        """Open the search page with Playwright + extract seller data."""
        if async_playwright is None:
            raise ScraperError(
                "Playwright not installed — install via "
                "pip install playwright && playwright install chromium"
            )

        rows: list[dict] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=settings.scout_tokopedia_headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            try:
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                    ),
                    locale="id-ID",
                )
                page = await context.new_page()
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=settings.scout_tokopedia_page_timeout_s * 1000,
                )
                # Wait a few seconds for JS-rendered content
                await asyncio.sleep(3)
                rows = await page.evaluate(_EXTRACT_SELLERS_JS)
            finally:
                await browser.close()
        return rows
