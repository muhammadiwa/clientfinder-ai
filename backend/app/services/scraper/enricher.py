"""
Homepage enricher — T8.6 (Scout enrichment).

Fetches a prospect's website homepage and extracts phone, email,
address, and social links. Closes the gap where the Google Search
scraper returns only URL + company_name, leaving T6 Outreach
without the contact info needed to send messages (R9: Email +
WhatsApp only channels).

The extractors (extract_phones, extract_emails, extract_address,
extract_socials) are pure functions on page HTML — unit-testable
without a browser. The async enrich_batch() is the Playwright
orchestrator that ties them together.

Pattern mirrors app.services.scraper.maps (same launch flags, same
timeout wrapper, same `async with async_playwright()` lifecycle).

No schema migration: reuses existing ScrapedResult.phone/email/
location_address + extra.social dict (later mapped to Prospect.
social_links JSONB at persistence time).
"""
from __future__ import annotations

import asyncio
import logging
import re
import time

from selectolax.parser import HTMLParser

from app.services.scraper.base import ScrapedResult, ScraperError

logger = logging.getLogger("clientfinder.scraper.enricher")

try:
    from playwright.async_api import (
        async_playwright,
        TimeoutError as PWTimeout,
    )

    PLAYWRIGHT_AVAILABLE = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT_AVAILABLE = False


# --- Email filter (false positives) ---
_EMAIL_LOCAL_DENY = frozenset({
    "noreply", "no-reply", "admin", "webmaster", "postmaster",
    "abuse", "privacy", "hostmaster",
})
_EMAIL_DOMAIN_DENY = frozenset({
    "example.com", "example.org", "example.net",
    "yourdomain.com", "yourcompany.com",
    "sentry.io", "wixpress.com", "wordpress.com",
})

# --- Phone regex ---
_PHONE_RE = re.compile(r"(\+?\d[\d\s\-\.\(\)]{7,}\d)")
_TEL_HREF_RE = re.compile(r"""href=["']tel:([^"']+)["']""", re.IGNORECASE)
_WA_HREF_RE = re.compile(
    r"""href=["'](https?://(?:wa\.me/(\d+)|[^"']*whatsapp\.com/send\?phone=(\d+)[^"']*))["']""",
    re.IGNORECASE,
)

# --- Email regex ---
_MAILTO_HREF_RE = re.compile(r"""href=["']mailto:([^"']+)["']""", re.IGNORECASE)
_EMAIL_BODY_RE = re.compile(
    r"\b([A-Za-z0-9._%+\-]+)@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})\b"
)

# --- Address patterns ---
_ADDR_MICRODATA_RE = re.compile(
    r"""<[^>]+itemprop=["']address["'][^>]*>([^<]{8,200})</[^>]+>""",
    re.IGNORECASE,
)
_ADDR_OG_RE = re.compile(
    r"""<meta[^>]+property=["']business:contact_data:street_address["'][^>]+content=["']([^"']{8,200})["']""",
    re.IGNORECASE,
)
_ADDR_HINT_RE = re.compile(
    r"(Jl\.|Jalan|Ruko|Komp\.|Kompleks|Blok\s|No\.|Kel\.|Kec\.|Kota\s|Kab\.|"
    r"Jl\s+|Jl.|Gg\.|Gang)",
    re.IGNORECASE,
)

# --- Social platform patterns ---
# Each: (platform_key, regex). The first match per platform wins.
_SOCIAL_PATTERNS = [
    ("instagram", re.compile(
        r"""https?://(?:www\.)?instagram\.com/([A-Za-z0-9._]{2,30})/?(?:\?|$|["'])""",
        re.IGNORECASE,
    )),
    ("facebook", re.compile(
        r"""https?://(?:www\.)?facebook\.com/([A-Za-z0-9.]{2,50})/?(?:\?|$|["'])""",
        re.IGNORECASE,
    )),
    ("twitter", re.compile(
        r"""https?://(?:www\.)?(?:twitter|x)\.com/([A-Za-z0-9_]{2,30})/?(?:\?|$|["'])""",
        re.IGNORECASE,
    )),
    ("linkedin", re.compile(
        r"""https?://(?:www\.)?linkedin\.com/(?:company|in)/([A-Za-z0-9\-]{2,50})/?(?:\?|$|["'])""",
        re.IGNORECASE,
    )),
    ("tiktok", re.compile(
        r"""https?://(?:www\.)?tiktok\.com/@([A-Za-z0-9._]{2,30})/?(?:\?|$|["'])""",
        re.IGNORECASE,
    )),
    ("youtube", re.compile(
        r"""https?://(?:www\.)?youtube\.com/(?:c/|@|channel/)([A-Za-z0-9_\-]{2,50})/?(?:\?|$|["'])""",
        re.IGNORECASE,
    )),
    ("whatsapp", re.compile(
        r"""href=["'](https?://(?:wa\.me/\d+|api\.whatsapp\.com/send\?phone=\d+[^"']*))["']""",
        re.IGNORECASE,
    )),
    ("telegram", re.compile(
        r"""https?://(?:www\.)?t\.me/([A-Za-z0-9_]{2,32})/?(?:\?|$|["'])""",
        re.IGNORECASE,
    )),
]


class HomepageEnricher:
    """Fetch a prospect's homepage and extract contact info.

    Pure-function extractors (extract_phones, extract_emails,
    extract_address, extract_socials) are unit-testable without a
    browser. enrich_batch() is the async Playwright orchestrator.
    """

    PAGE_TIMEOUT_S_DEFAULT = 12
    BATCH_TIMEOUT_S_DEFAULT = 240.0
    SETTLE_MS = 1_500

    def __init__(
        self,
        page_timeout_s: int = PAGE_TIMEOUT_S_DEFAULT,
        batch_timeout_s: float = BATCH_TIMEOUT_S_DEFAULT,
    ) -> None:
        if not PLAYWRIGHT_AVAILABLE:
            raise ScraperError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )
        self.page_timeout_ms = page_timeout_s * 1000
        self.batch_timeout_s = batch_timeout_s

    async def enrich_batch(
        self, results: list[ScrapedResult]
    ) -> list[ScrapedResult]:
        """Fetch each homepage + extract fields. Mutates results in place.

        Never raises. On error, marks each result's enrichment_status
        appropriately. Returns the same list for convenience.
        """
        if not results:
            return results

        for r in results:
            if not r.website:
                r.extra.setdefault("enrichment_status", "no_data")
                r.extra.setdefault("enrichment_ms", 0)

        enrichable = [r for r in results if r.website]
        if not enrichable:
            return results

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

                    for r in enrichable:
                        try:
                            await self._enrich_one(page, r)
                        except Exception as e:
                            r.extra["enrichment_status"] = "error"
                            r.extra["enrichment_ms"] = 0
                            logger.warning(
                                "Enrich one failed for %s: %s", r.website, e
                            )
                finally:
                    await context.close()
                    await browser.close()
        except Exception as e:
            logger.warning("Enrichment batch top-level failed: %s", e)
            for r in enrichable:
                r.extra.setdefault("enrichment_status", "error")
                r.extra.setdefault("enrichment_ms", 0)

        return results

    async def _enrich_one(self, page, r: ScrapedResult) -> None:
        """Fetch r.website, extract fields, mutate r. Sets enrichment_status."""
        start = time.monotonic()
        try:
            response = await page.goto(
                r.website,
                timeout=self.page_timeout_ms,
                wait_until="domcontentloaded",
            )
            if not response:
                r.extra["enrichment_status"] = "no_data"
                r.extra["enrichment_ms"] = int((time.monotonic() - start) * 1000)
                return
            status = response.status
            if status >= 400:
                r.extra["enrichment_status"] = "no_data" if status < 500 else "error"
                r.extra["enrichment_ms"] = int((time.monotonic() - start) * 1000)
                return
            await asyncio.sleep(self.SETTLE_MS / 1000)
            html = await page.content()
            text = await page.evaluate(
                "() => document.body ? document.body.innerText : ''"
            )

            phones = self.extract_phones(html, text or "")
            emails = self.extract_emails(html)
            address = self.extract_address(html, text or "")
            socials = self.extract_socials(html)

            if phones:
                r.phone = phones[0]
            if emails:
                r.email = emails[0]
            if address:
                r.location_address = address
            if socials:
                existing_socials = r.extra.get("social") or {}
                r.extra["social"] = {**existing_socials, **socials}

            ms = int((time.monotonic() - start) * 1000)
            r.extra["enrichment_ms"] = ms
            r.extra["enrichment_status"] = (
                "ok" if (phones or emails or address or socials) else "no_data"
            )
        except PWTimeout:
            r.extra["enrichment_status"] = "timeout"
            r.extra["enrichment_ms"] = int((time.monotonic() - start) * 1000)
        except Exception as e:
            r.extra["enrichment_status"] = "error"
            r.extra["enrichment_ms"] = int((time.monotonic() - start) * 1000)
            logger.debug("Enrich one failed for %s: %s", r.website, e)

    # --- Pure-function extractors (unit-testable) ---

    @staticmethod
    def extract_phones(html: str, visible_text: str) -> list[str]:
        """Extract phone numbers. Priority: tel: > wa.me > +62 regex > generic."""
        candidates: list[tuple[int, str]] = []

        for m in _TEL_HREF_RE.finditer(html):
            raw = m.group(1).strip()
            digits = re.sub(r"[^\d+]", "", raw)
            if 8 <= len(digits) <= 16:
                candidates.append((0, raw))

        for m in _WA_HREF_RE.finditer(html):
            digits = m.group(2) or m.group(3)
            if digits and 8 <= len(digits) <= 16:
                candidates.append((1, digits))

        for m in _PHONE_RE.finditer(visible_text):
            raw = m.group(1).strip()
            digits = re.sub(r"[^\d+]", "", raw)
            if not (8 <= len(digits) <= 16):
                continue
            # Skip date-shaped matches on the ORIGINAL raw (with separators)
            if re.match(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}$", raw):
                continue
            if re.match(r"^\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}$", raw):
                continue
            # Skip compact DDMMYYYY or YYYYMMDD (8 digits, plausible day/month)
            if len(digits) == 8:
                if re.match(r"^(0[1-9]|[12]\d|3[01])(0[1-9]|1[0-2])\d{4}$", digits):
                    continue
                if re.match(r"^\d{4}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])$", digits):
                    continue
            priority = 2 if (digits.startswith("+62") or digits.startswith("0")) else 3
            candidates.append((priority, raw))

        candidates.sort(key=lambda x: x[0])
        seen: set[str] = set()
        out: list[str] = []
        for _, phone in candidates:
            if phone not in seen:
                seen.add(phone)
                out.append(phone)
            if len(out) >= 3:
                break
        return out

    @staticmethod
    def extract_emails(html: str) -> list[str]:
        """Extract emails. mailto: > body regex, with deny-list filter."""
        candidates: list[tuple[int, str]] = []

        for m in _MAILTO_HREF_RE.finditer(html):
            email = m.group(1).strip().lower()
            email = email.split("?")[0].split("#")[0]
            if "@" in email and not _is_filtered_email(email):
                candidates.append((0, email))

        for m in _EMAIL_BODY_RE.finditer(html):
            local, domain = m.group(1), m.group(2)
            email = f"{local}@{domain}".lower()
            if not _is_filtered_email(email):
                candidates.append((1, email))

        candidates.sort(key=lambda x: x[0])
        seen: set[str] = set()
        out: list[str] = []
        for _, email in candidates:
            if email not in seen:
                seen.add(email)
                out.append(email)
            if len(out) >= 3:
                break
        return out

    @staticmethod
    def extract_address(html: str, visible_text: str) -> str | None:
        """Extract address. Microdata > OG > footer regex (Indonesian)."""
        m = _ADDR_MICRODATA_RE.search(html)
        if m:
            return m.group(1).strip()

        m = _ADDR_OG_RE.search(html)
        if m:
            return m.group(1).strip()

        for line in (visible_text or "").splitlines():
            line = line.strip()
            if _ADDR_HINT_RE.search(line) and 8 < len(line) < 200:
                return line
        return None

    @staticmethod
    def extract_socials(html: str) -> dict[str, str]:
        """Extract social links. First occurrence per platform wins."""
        out: dict[str, str] = {}
        for platform, pattern in _SOCIAL_PATTERNS:
            m = pattern.search(html)
            if m:
                if platform == "whatsapp":
                    url = m.group(1)
                else:
                    url = m.group(0)
                url = url.rstrip("/").rstrip('"').rstrip("'")
                if not url.startswith("http"):
                    url = "https://" + url
                out[platform] = url
        return out


def _is_filtered_email(email: str) -> bool:
    local, _, domain = email.partition("@")
    if local in _EMAIL_LOCAL_DENY:
        return True
    if domain in _EMAIL_DOMAIN_DENY:
        return True
    return False
