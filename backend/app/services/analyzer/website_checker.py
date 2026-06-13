"""
Website audit — fast async HTTP checks (no LLM, no headless browser).

Performs:
  - DNS resolution + connection check
  - HTTP HEAD request
  - Response time measurement
  - SSL detection (https:// vs http://)
  - Server / X-Powered-By header capture
  - 404 vs 200 detection

Per playbook R7: pragmatic-legal, no scraping of content.
"""
from __future__ import annotations

import asyncio
import logging
import socket
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("clientfinder.analyzer.website")

TIMEOUT_S = 8.0
USER_AGENT = "Mozilla/5.0 (compatible; ClientFinder/1.0; +https://clientfinder.app)"


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
    extra: dict[str, Any] = field(default_factory=dict)


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

    # HTTP HEAD
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT_S,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            resp = await client.head(url)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return WebsiteAudit(
                url=url,
                reachable=True,
                has_ssl=has_ssl,
                response_time_ms=elapsed_ms,
                status_code=resp.status_code,
                server=resp.headers.get("server"),
                powered_by=resp.headers.get("x-powered-by"),
                redirect_url=str(resp.url) if str(resp.url) != url else None,
                extra={"headers_seen": list(resp.headers.keys())[:20]},
            )
    except httpx.HTTPError as e:
        # Some servers reject HEAD — try GET as fallback
        try:
            async with httpx.AsyncClient(
                timeout=TIMEOUT_S,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT},
            ) as client:
                resp = await client.get(url)
                elapsed_ms = int((time.monotonic() - start) * 1000)
                return WebsiteAudit(
                    url=url,
                    reachable=True,
                    has_ssl=has_ssl,
                    response_time_ms=elapsed_ms,
                    status_code=resp.status_code,
                    server=resp.headers.get("server"),
                    powered_by=resp.headers.get("x-powered-by"),
                    error=f"HEAD failed, GET succeeded: {e!s}",
                )
        except httpx.HTTPError as e2:
            return WebsiteAudit(
                url=url,
                reachable=False,
                has_ssl=has_ssl,
                response_time_ms=None,
                status_code=None,
                error=f"HTTP request failed: {e2!s}",
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
