"""
Website audit — async HTTP + content checks (no LLM, no headless
browser — just httpx + regex).

Performs:
  - DNS resolution + connection check
  - HTTP GET (capped to MAX_BODY_BYTES) so we can read the body
  - Response time measurement
  - SSL detection (https:// vs http://)
  - Server / X-Powered-By header capture
  - 404 vs 200 detection
  - Mobile-friendly check: viewport meta tag (Sprint 1 / Phase 1.2)
  - Payment-gateway detection: known Indonesian/global gateways
    (Sprint 1 / Phase 1.2)

Per playbook R7: pragmatic-legal, no scraping of content. We
read up to MAX_BODY_BYTES (~100 KB) which is enough for the
viewport meta + payment gateway markers but doesn't constitute
"scraping".

Sprint 1 / Phase 1.2 design note: the heavy Playwright-based
checks (mobile RENDER, console error capture) live in a separate
module `site_features.py`. This module is intentionally
lightweight (httpx only) so the basic audit never blocks on
a slow browser.
"""
from __future__ import annotations

import asyncio
import logging
import re
import socket
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("clientfinder.analyzer.website")

TIMEOUT_S = 8.0
USER_AGENT = "Mozilla/5.0 (compatible; ClientFinder/1.0; +https://clientfinder.app)"
MAX_BODY_BYTES = 100_000  # 100 KB cap — enough for meta + gateway markers

# --- Mobile-friendly detection ---
# Standard responsive-design meta tag. Absence = not mobile-friendly
# (or the developer forgot it, which is just as bad).
VIEWPORT_META_RE = re.compile(
    r"""<meta[^>]+name=["']viewport["'][^>]+content=["']""",
    re.IGNORECASE,
)
# A common "we're mobile-aware" indicator: <meta name="HandheldFriendly">
# or <meta name="MobileOptimized">. Either is good enough.
HANDHELD_META_RE = re.compile(
    r"""<meta[^>]+name=["'](?:HandheldFriendly|MobileOptimized|theme-color)["']""",
    re.IGNORECASE,
)

# --- Payment gateway detection (Sprint 1 / Phase 1.2) ---
# Each tuple: (canonical_name, regex). Match anywhere in the page
# HTML (head, body, script src, link href). For iframe src URLs we
# include a separate regex per gateway.
PAYMENT_GATEWAYS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # Indonesian
    ("midtrans", re.compile(r"midtrans\.com|snap\.midtrans", re.IGNORECASE)),
    ("xendit", re.compile(r"xendit\.co|invoices?\.xendit", re.IGNORECASE)),
    ("doku", re.compile(r"doku\.com|doku\.id", re.IGNORECASE)),
    ("tripay", re.compile(r"tripay\.co\.id", re.IGNORECASE)),
    ("ipay", re.compile(r"ipay88\.com|ipay\.id", re.IGNORECASE)),
    # Global
    ("stripe", re.compile(r"(?:js\.stripe\.com|checkout\.stripe\.com)", re.IGNORECASE)),
    ("paypal", re.compile(r"paypal\.com|paypalobjects\.com", re.IGNORECASE)),
    ("square", re.compile(r"squareup\.com|square\.site", re.IGNORECASE)),
    ("razorpay", re.compile(r"razorpay\.com", re.IGNORECASE)),
    ("paypal_buttons", re.compile(r"paypal\.com/sdk/js|paypalobjects\.com", re.IGNORECASE)),
)


@dataclass
class WebsiteAudit:
    url: str | None
    reachable: bool
    has_ssl: bool
    response_time_ms: int | None
    status_code: int | None
    server: str | None = None
    powered_by: str | None = None
    redirect_url: str | None = None
    error: str | None = None
    # Sprint 1 / Phase 1.2 fields
    has_viewport_meta: bool = False
    payment_gateways: list[str] = field(default_factory=list)
    body_bytes_read: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


def _check_viewport_meta(html: str) -> bool:
    """True if the HTML has a <meta name="viewport" content="..."> tag
    OR a known mobile-friendly meta. Standard indicator of responsive
    design; absence strongly suggests the site is desktop-only or
    not mobile-optimized.
    """
    if VIEWPORT_META_RE.search(html):
        return True
    if HANDHELD_META_RE.search(html):
        return True
    return False


def _detect_payment_gateways(html: str) -> list[str]:
    """Return a list of payment gateway names found in the HTML.

    Checks the full HTML (script src, link href, body text, iframes).
    Empty list = no payment gateway detected = no_payment_system pain.
    """
    found: list[str] = []
    for name, pattern in PAYMENT_GATEWAYS:
        if pattern.search(html):
            found.append(name)
    # Dedup, preserve order
    return list(dict.fromkeys(found))


async def audit_website(url: str | None) -> WebsiteAudit:
    """
    Run a lightweight audit of the website.

    Returns WebsiteAudit dataclass with all findings.
    Never raises — errors are captured in the result.
    """
    if not url:
        return WebsiteAudit(
            url=None,
            reachable=False,
            has_ssl=False,
            response_time_ms=None,
            status_code=None,
            error="No URL provided",
        )

    # Normalize: add https:// if no scheme
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    has_ssl = parsed.scheme == "https"

    # Quick DNS check (sync, but fast)
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: socket.gethostbyname(parsed.netloc.split(":")[0])
        )
    except (socket.gaierror, OSError) as e:
        return WebsiteAudit(
            url=url,
            reachable=False,
            has_ssl=has_ssl,
            response_time_ms=None,
            status_code=None,
            error=f"DNS resolution failed: {e}",
        )

    # HTTP GET (cap body to MAX_BODY_BYTES for mobile + payment checks)
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT_S,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            resp = await client.get(url)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            # Read up to MAX_BODY_BYTES for the body-based checks
            body_bytes = resp.content[:MAX_BODY_BYTES]
            body_str = body_bytes.decode("utf-8", errors="ignore")
            return WebsiteAudit(
                url=url,
                reachable=True,
                has_ssl=has_ssl,
                response_time_ms=elapsed_ms,
                status_code=resp.status_code,
                server=resp.headers.get("server"),
                powered_by=resp.headers.get("x-powered-by"),
                redirect_url=str(resp.url) if str(resp.url) != url else None,
                # Sprint 1 / Phase 1.2
                has_viewport_meta=_check_viewport_meta(body_str),
                payment_gateways=_detect_payment_gateways(body_str),
                body_bytes_read=len(body_bytes),
                extra={"headers_seen": list(resp.headers.keys())[:20]},
            )
    except httpx.HTTPError as e:
        return WebsiteAudit(
            url=url,
            reachable=False,
            has_ssl=has_ssl,
            response_time_ms=int((time.monotonic() - start) * 1000),
            status_code=None,
            error=f"HTTP request failed: {e!s}",
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Website audit crashed for %s: %s", url, e)
        return WebsiteAudit(
            url=url,
            reachable=False,
            has_ssl=has_ssl,
            response_time_ms=None,
            status_code=None,
            error=f"Unexpected error: {e!s}",
        )
