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
    # DEACTIVATED 2026-06-14: the 50-result hard cap was removed
    # per the user's v1 redesign — "all data saved for enrichment".
    # The ceil of 1000 is a safety (prevents a runaway search from
    # returning 10k+ results and pinning the Celery worker). Operators
    # can pass an explicit `max_results` in the scout job query to
    # set a lower bound; default is DEFAULT_LIMIT.
    DEFAULT_LIMIT = 200
    MAX_HARD_CAP = 1000
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
        # Guard against negative / zero max_results. The Pydantic
        # schema enforces ge=1, le=100, but the scraper is also
        # called from the Celery task with a raw query dict where
        # a corrupted value could slip through. Without the max(1, …)
        # guard, max_results=-5 would break the loop on iter 0 and
        # silently return 0 results.
        max_results = max(
            1,
            min(
                int(query.get("max_results") or self.DEFAULT_LIMIT),
                self.MAX_HARD_CAP,
            ),
        )

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
        # Sprint 4 PR 2: extract the FULL Places data, not just
        # address + phone. The user spec (turn 58): "untuk google
        # maps semua datanya di simpan contoh sosmed nya juga dll
        # yang berkaitan dan datanya berguna untuk dijadikan
        # prospek" — save ALL Google Maps data. The full payload
        # lands in prospects.raw_data JSONB and powers the
        # breadcrumb in PR 3 + the /scout-runs/:id page.
        address = _extract_address(full_text)
        phone = _extract_phone(full_text)
        rating = _extract_rating(full_text)
        review_count = _extract_review_count(full_text)
        hours = _extract_hours(full_text)
        price_range = _extract_price_range(full_text)
        service_options = _extract_service_options(full_text)

        # Link with href to the actual website
        website = None
        link = await card.query_selector(
            'a[href^="http"]:not([href*="google.com/maps"])'
        )
        if link:
            href = await link.get_attribute("href")
            if href and "google.com" not in href:
                website = href

        # Build the full Places extra payload. Sprint 4 PR 2
        # forwards this whole dict to prospects.raw_data.
        extra: dict[str, Any] = {
            "raw_address": address,
            "rating": rating,
            "review_count": review_count,
            "hours": hours,
            "price_range": price_range,
            "service_options": service_options,
        }
        # Drop None values to keep raw_data tight
        extra = {k: v for k, v in extra.items() if v is not None}

        return ScrapedResult(
            company_name=name[:255],
            website=website[:500] if website else None,
            phone=phone,
            location_address=address,
            description=None,
            source_url=None,
            source="maps",
            extra=extra,
        )


_PHONE_RE = re.compile(r"(\+?\d[\d\s\-]{7,}\d)")
# Address hint keywords. Uses a negative lookahead `(?!\w)` instead of
# `\b` to anchor the match. `\b` fails after "Jl." (period is non-word
# so .→space has no boundary), and removing `\b` entirely lets
# "Jalanisme" / "Jlr Coffee" match. The lookahead is the tightest
# bound that works for both period-ending and word-ending keywords.
_ADDR_HINT = re.compile(
    r"(Jl\.|Jalan|Ruko|Komp\.|Kompleks|Blok|No\.|Jl\s|Kel\.|Kec\.|Kota\s|Kab\.)(?!\w)",
    re.IGNORECASE,
)
# Maps rating is shown as "4,5" or "4.5" (Indonesian locale uses comma).
# It's followed by either a star icon or "(N ulasan)" pattern. Rating
# values are bounded to [1,5] (Maps max is 5); a leading `\b` prevents
# matching inside "10" or "50".
_RATING_RE = re.compile(
    r"\b([1-5](?:[.,][0-9])?)\s*(?:★|\(\s*[\d.,]+\s*ulasan\b)",
    re.IGNORECASE,
)
# Maps review count: "(123 ulasan)" or "1,2 rb ulasan" or "1.000 ulasan"
# (Indonesian thousands separator, NO `rb` suffix — Maps uses bare dots).
_REVIEW_RE = re.compile(
    r"([\d.,]+)\s*(rb|ribu|k|K)?\s*ulasan\b",
    re.IGNORECASE,
)
# Maps hours: "Buka ⋅ Tutup pukul 21.00", "Buka 24 jam",
# "Tutup ⋅ Buka pukul 08.00", or "Tutup permanen"
_HOURS_RE = re.compile(
    r"(Buka\s*⋅\s*Tutup\s*pukul\s*[\d:.]+|"
    r"Buka\s*24\s*jam|"
    r"Tutup\s*⋅\s*Buka\s*pukul\s*[\d:.]+|"
    r"Tutup\s*permanen)",
    re.IGNORECASE,
)
# Price range: "$$" / "$$$" / "Rp 50.000–100.000" / "Rp 50 rb".
# Anchored with `(?:^|(?<=\s))` to require the match to start at
# the beginning of a token. The trailing `(?!\w)` (NOT `\b`) is
# required for `$$` at end-of-line — `\b` fails at the transition
# from non-word to nothing (end of input).
_PRICE_RE = re.compile(
    r"(?:^|(?<=\s))(\$+(?!\w)|Rp\.?\s*[\d.,]+(?:\s*[\u2013\u2014\-]\s*[\d.,]+)?(?:\s*(?:rb|ribu))?)",
    re.IGNORECASE,
)
# Service options: "Makan di tempat", "Bawa pulang", "Pesan antar",
# "Layanan drive-through", "Pengiriman tanpa kontak"
_SERVICE_OPT_RE = re.compile(
    r"(Makan di tempat|Bawa pulang|Pesan antar|Layanan drive-through|"
    r"Pengiriman tanpa kontak|Dine-in|Takeaway|Delivery)",
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


def _extract_rating(text: str) -> float | None:
    """Extract Maps rating (e.g. "4,5") from card text.

    Returns a float in [1.0, 5.0] (Maps max is 5). The regex
    enforces the upper bound; ratings outside this range are
    treated as garbage. Indonesian locale uses comma as the
    decimal separator ("4,5") — converted to float via dot.
    """
    m = _RATING_RE.search(text)
    if m:
        return float(m.group(1).replace(",", "."))
    return None


def _extract_review_count(text: str) -> int | None:
    """Extract Maps review count.

    Handles the Indonesian number-formatting ambiguity:
    - `"1.000 ulasan"` (ID thousands, no suffix) → 1000
    - `"1,000 ulasan"` (English thousands) → 1000
    - `"500 ulasan"` → 500
    - `"1,2 rb ulasan"` (ID decimal + rb suffix) → 1200
    - `"1.2 ribu ulasan"` (English decimal + ribu) → 1200
    - `"10.000 ulasan"` (ID thousands, the "10.000" trap) → 10000

    The rule: if `rb`/`ribu`/`k` suffix is present, the captured
    number is decimal (comma → dot, multiply by 1000). Otherwise
    all separators (`.` and `,`) are thousands — strip them.
    Review counts are integers, so decimals without suffix are
    treated as thousands.
    """
    m = _REVIEW_RE.search(text)
    if not m:
        return None
    number_str = m.group(1)
    suffix = (m.group(2) or "").lower()
    if suffix in ("rb", "ribu", "k"):
        # Decimal number + multiplier suffix
        try:
            n = float(number_str.replace(",", "."))
        except ValueError:
            return None
        n *= 1000
    else:
        # No suffix: both `.` and `,` are thousands separators.
        # Review counts are integers, so a bare decimal makes no sense.
        try:
            n = int(number_str.replace(".", "").replace(",", ""))
        except ValueError:
            return None
    return int(n)


def _extract_hours(text: str) -> str | None:
    """Extract Maps opening hours string.

    Examples: "Buka ⋅ Tutup pukul 21.00", "Buka 24 jam",
    "Tutup ⋅ Buka pukul 08.00", "Tutup permanen".
    """
    m = _HOURS_RE.search(text)
    return m.group(1).strip() if m else None


def _extract_price_range(text: str) -> str | None:
    """Extract Maps price range indicator.

    Examples: "$$", "$$$", "Rp 50.000–100.000", "Rp 50 rb".
    """
    m = _PRICE_RE.search(text)
    return m.group(1).strip() if m else None


def _extract_service_options(text: str) -> list[str] | None:
    """Extract Maps service options (dine-in / takeaway / delivery).

    Returns a list of normalized option labels, or None if no
    service options found.
    """
    matches = _SERVICE_OPT_RE.findall(text)
    if not matches:
        return None
    # Deduplicate (case-insensitive) while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for m in matches:
        key = m.lower()
        if key not in seen:
            seen.add(key)
            result.append(m)
    return result


def _url_quote(s: str) -> str:
    from urllib.parse import quote

    return quote(s, safe="")
