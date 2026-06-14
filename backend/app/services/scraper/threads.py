"""
Threads (Meta) scraper — T9.0 Social Signal Agent sub-task 2.2.

Per R7 (pragmatic-legal): Threads doesn't have an official search
API, and no good community library exists. We use Playwright with
stored session cookies — same approach as the maps scraper.

Per the brief, Threads is one of 4 Scout data sources
(Social Media, Threads/X, Business Directory, Search Engine).
With Twitter covered by the previous PR, this PR adds Threads.

The result of this scraper is a list of SocialPost objects (same
schema as Twitter) that the LLM signal classifier (T9.0 sub-task
2.4) consumes to detect 'needs software' intent.

Design:
  - Cookie-based auth (different from Twitter — Threads is
    threads.net, not x.com)
  - Playwright browser launch (headless Chromium, same pattern
    as maps.py:121-133)
  - DOM extraction via page.evaluate() — more robust than CSS
    selectors since Meta changes them frequently
  - Soft-fail by default — missing cookies = [] with warning,
    pipeline stays healthy
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.core.config import settings
from app.services.scraper.base import BaseScraper, ScraperError
from app.services.scraper.twitter import SocialPost

logger = logging.getLogger("clientfinder.scraper.threads")

# --- Cookie validation (Threads uses the same JSON-file approach
# as Twitter but a different schema) ---

# Threads cookies: sessionid, csrftoken, ds_user_id, mid, etc.
# (Meta's naming convention). At minimum sessionid is required.
def _validate_threads_cookies(path: str) -> dict | None:
    """Load and validate the Threads cookies JSON file.

    Returns the dict on success, None on any error (logs warning).
    """
    if not os.path.exists(path):
        logger.warning(
            "Threads cookies file not found at %s — "
            "skipping Threads scan. See scripts/setup_social_cookies.py.",
            path,
        )
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Threads cookies file unreadable at %s: %s", path, e)
        return None
    if not isinstance(data, dict) or not data:
        logger.warning("Threads cookies file empty or invalid: %s", path)
        return None
    # Threads needs at least sessionid for auth
    if "sessionid" not in data:
        logger.warning(
            "Threads cookies file at %s missing 'sessionid' — "
            "scraper will likely fail. Re-export from threads.net.",
            path,
        )
    return data


# --- DOM extraction via page.evaluate ---

# JavaScript that runs inside the page to extract post data.
# Tries multiple selector strategies since Meta changes the DOM
# frequently. Returns a list of {text, url, time, author} dicts.
_EXTRACT_POSTS_JS = """
() => {
  const results = [];
  // Strategy 1: <article> elements (Threads uses these for posts)
  const articles = document.querySelectorAll('article');
  articles.forEach(el => {
    const text = el.innerText ? el.innerText.split('\\n')[0] : '';
    // Find the post URL — Threads links are like /@user/post/POSTID
    const linkEl = el.querySelector('a[href*="/post/"]');
    const href = linkEl ? linkEl.href : '';
    // Time element
    const timeEl = el.querySelector('time');
    const dt = timeEl ? (timeEl.getAttribute('datetime') || timeEl.dateTime) : null;
    // Author from URL or aria-label
    let author = '';
    if (href) {
      const m = href.match(/@([^/]+)/);
      if (m) author = m[1];
    }
    if (!author) {
      // Fallback: try the avatar alt or user link
      const userLink = el.querySelector('a[href*="/@"]');
      if (userLink) {
        const m = userLink.href.match(/@([^/]+)/);
        if (m) author = m[1];
      }
    }
    if (text && href) {
      results.push({ text, url: href, time: dt, author });
    }
  });
  return results;
}
"""


async def _search_threads_playwright(
    cookies: dict,
    query: str,
    max_results: int,
    max_age_days: int,
) -> list[SocialPost]:
    """Run Playwright in a thread executor (Playwright is sync-friendly
    but we're in an async context)."""
    from playwright.async_api import async_playwright

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    posts: list[SocialPost] = []

    async def _do_search() -> list[SocialPost]:
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
                # Inject cookies. Threads uses 'threads.net' as domain.
                await context.add_cookies([
                    {
                        "name": name,
                        "value": value,
                        "domain": ".threads.net",
                        "path": "/",
                    }
                    for name, value in cookies.items()
                    if isinstance(value, str)
                ])
                page = await context.new_page()
                url = f"https://www.threads.net/search?q={query}&serp_type=default"
                logger.info("Threads search: %s", url)
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                # Let JS render for a few seconds
                await asyncio.sleep(3)
                # Extract via JS — more robust than CSS selectors
                raw = await page.evaluate(_EXTRACT_POSTS_JS)

                for r in raw:
                    text = (r.get("text") or "").strip()
                    url = r.get("url") or ""
                    if not text or not url:
                        continue
                    # Parse post_id from URL: /post/POST_ID
                    post_id = ""
                    m = re.search(r"/post/([^/?]+)", url)
                    if m:
                        post_id = m.group(1)
                    # Parse timestamp
                    ts_str = r.get("time")
                    ts = datetime.now(timezone.utc)
                    if ts_str:
                        try:
                            ts = datetime.fromisoformat(
                                ts_str.replace("Z", "+00:00")
                            )
                        except (ValueError, AttributeError):
                            pass
                    if ts < cutoff:
                        continue
                    author = r.get("author") or "unknown"
                    posts.append(
                        SocialPost(
                            post_id=post_id or url,
                            text=text,
                            author_handle=str(author),
                            url=url,
                            timestamp=ts,
                            engagement={},
                            language="id",
                        )
                    )
                    if len(posts) >= max_results:
                        break
            finally:
                await browser.close()
        return posts

    return await _do_search()


class ThreadsScraper(BaseScraper):
    source = "threads"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    async def search(self, query: dict[str, Any]) -> list[SocialPost]:
        """Search Threads for posts matching the query.

        `query` schema: same as Twitter (T9.0 sub-task 2.1).
          - keywords, location, max_results, max_age_days

        Returns: list of SocialPost. Soft-fail by default when
        cookies are missing — the pipeline stays healthy.
        """
        keywords = query.get("keywords") or query.get("q") or ""
        if isinstance(keywords, list):
            keywords = " ".join(keywords)
        keywords = keywords.strip()
        if not keywords:
            if settings.twitter_soft_fail:
                logger.warning("Threads search: empty keywords, skipping")
                return []
            raise ScraperError("Threads: 'keywords' is required")

        location = (query.get("location") or "").strip()
        max_results = int(
            query.get("max_results") or settings.twitter_search_max_per_query
        )
        max_age_days = int(
            query.get("max_age_days") or settings.twitter_max_age_days
        )
        full_query = f"{keywords} {location}".strip() if location else keywords

        cookies = _validate_threads_cookies(settings.threads_cookies_path)
        if not cookies:
            if settings.twitter_soft_fail:  # reuse the twitter soft-fail flag
                return []
            raise ScraperError(
                f"Threads cookies not available at "
                f"{settings.threads_cookies_path}. "
                f"Run scripts/setup_social_cookies.py threads."
            )

        logger.info(
            "Threads search: q=%r max=%d age=%dd",
            full_query, max_results, max_age_days,
        )

        try:
            posts = await _search_threads_playwright(
                cookies, full_query, max_results, max_age_days,
            )
        except ImportError:
            logger.warning("playwright not importable — Threads scan skipped")
            return [] if settings.twitter_soft_fail else _raise("playwright missing")
        except Exception as e:  # noqa: BLE001
            if settings.twitter_soft_fail:
                logger.warning(
                    "Threads search failed (soft-fail): %s: %s",
                    type(e).__name__, e,
                )
                return []
            raise ScraperError(f"Threads search failed: {e}") from e

        logger.info("Threads returned %d posts for q=%r", len(posts), full_query)
        return posts


def _raise(msg: str) -> None:
    raise ScraperError(msg)


__all__ = ["ThreadsScraper", "SocialPost", "_validate_threads_cookies"]
