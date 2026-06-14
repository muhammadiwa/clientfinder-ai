"""
Twitter (X) scraper — T9.0 Social Signal Agent.

Per playbook R7: pragmatic-legal. Twitter/X doesn't have a public
search API anymore (paid plans start at $100/mo + enterprise
gating), so we use Twikit — a community-maintained library
that talks to Twitter's internal GraphQL endpoints with cookie
auth (same approach as the original twint/snscrape before they
broke).

Cookie requirement:
  - File: <settings.twitter_cookies_path> (default .sessions/twitter_cookies.json)
  - Format: JSON with keys auth_token, ct0, twid, guest_id, etc.
    (whatever Twikit's CookieSession needs)
  - How to get: log into x.com in a browser, export cookies via
    a browser extension (e.g. "Cookie Editor"), save as the JSON
    shape above. See scripts/setup_social_cookies.py for a
    validator.

Soft-fail behavior:
  - If settings.twitter_soft_fail=True (default) and cookies are
    missing/stale/invalid, the scraper returns [] with a warning
    log. The pipeline stays healthy — Signal Agent just produces
    no signals this run. Operator can flip the env var to False
    to fail loud during setup.

Output: list of SocialPost dataclasses (text, author, url, ts,
engagement, language). These get fed into the LLM signal
classifier (T9.0 sub-task 4) which decides which posts are
genuine "needs software" signals vs noise.

Per memory D86 / T9.0 design: this scraper is the foundation
of the Social Signal Agent. The other 9 brief signals
("post cari developer", "post butuh automation", "post launching
produk", etc.) all flow from this same data path.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.services.scraper.base import BaseScraper, ScraperError

logger = logging.getLogger("clientfinder.scraper.twitter")

# --- Public dataclass for the LLM signal classifier (T9.0) ---

@dataclass
class SocialPost:
    """A single post from a social source (Twitter / Threads / etc.).

    The Social Signal Agent (T9.0 sub-task 4) consumes a list of
    these and asks the LLM to detect "needs software" intent.
    """
    post_id: str
    text: str
    author_handle: str
    url: str
    timestamp: datetime
    engagement: dict[str, int] = field(default_factory=dict)
    # e.g. {"likes": 12, "retweets": 3, "views": 1500}
    language: str = "id"  # "id" / "en" / "in" — Twikit reports

    def to_dict(self) -> dict[str, Any]:
        """Serialise for the LLM prompt + storage."""
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


# --- Cookie validation ---

def _validate_cookies_file(path: str) -> dict | None:
    """Load and minimally validate the cookies JSON file.

    Returns the dict on success, None on any error (logs warning).
    The Twikit lib needs specific keys; we only check the file
    parses as JSON and is non-empty.
    """
    if not os.path.exists(path):
        logger.warning(
            "Twitter cookies file not found at %s — "
            "skipping Twitter scan. See scripts/setup_social_cookies.py.",
            path,
        )
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Twitter cookies file unreadable at %s: %s", path, e)
        return None
    if not isinstance(data, dict) or not data:
        logger.warning("Twitter cookies file empty or invalid format: %s", path)
        return None
    # Twikit expects specific keys; warn (don't fail) if missing
    expected = {"auth_token", "ct0"}
    missing = expected - set(data.keys())
    if missing:
        logger.warning(
            "Twitter cookies file at %s missing expected keys %s — "
            "scraper will likely fail. Re-export cookies from x.com.",
            path, sorted(missing),
        )
    return data


# --- Twikit client wrapper (async) ---

async def _search_twikit(
    cookies: dict,
    query: str,
    max_results: int,
    max_age_days: int,
) -> list[SocialPost]:
    """Run the Twikit search in a thread (it's a sync lib)."""
    def _do_search() -> list[SocialPost]:
        # Twikit's API surface changes between versions. This pattern
        # works for twikit==2.0.0 (current dep).
        from twikit.client.client import Client

        client = Client(
            language="id-ID",
            user_agent=(
                "Mozilla/5.0 (compatible; ClientFinder/1.0; "
                "+https://clientfinder.app)"
            ),
        )
        # set_cookies: Twikit's auth helper for cookie-based session
        # login. Reads auth_token + ct0 from the cookies dict.
        client.set_cookies(
            cookies=cookies,
            proxy=None,
        )

        posts: list[SocialPost] = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

        for tweet in client.search_tweet(query, product="Latest", count=max_results):
            # Skip retweets (they're noise for our use case)
            if getattr(tweet, "retweeted_tweet", None):
                continue
            text = (getattr(tweet, "text", "") or "").strip()
            if not text:
                continue
            ts_raw = getattr(tweet, "created_at", None)
            if isinstance(ts_raw, str):
                try:
                    ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                except ValueError:
                    ts = datetime.now(timezone.utc)
            elif isinstance(ts_raw, datetime):
                ts = ts_raw if ts_raw.tzinfo else ts_raw.replace(tzinfo=timezone.utc)
            else:
                ts = datetime.now(timezone.utc)
            if ts < cutoff:
                continue
            user = getattr(tweet, "user", None)
            handle = (
                getattr(user, "screen_name", None)
                or getattr(user, "name", "unknown")
            )
            post_id = str(getattr(tweet, "id", ""))
            url = f"https://x.com/{handle}/status/{post_id}" if post_id else ""
            posts.append(
                SocialPost(
                    post_id=post_id,
                    text=text,
                    author_handle=str(handle),
                    url=url,
                    timestamp=ts,
                    engagement={
                        "likes": int(getattr(tweet, "favorite_count", 0) or 0),
                        "retweets": int(getattr(tweet, "retweet_count", 0) or 0),
                        "replies": int(getattr(tweet, "reply_count", 0) or 0),
                        "views": int(getattr(tweet, "view_count", 0) or 0),
                    },
                    language=str(getattr(tweet, "lang", "id") or "id"),
                )
            )
            if len(posts) >= max_results:
                break
        return posts

    return await asyncio.get_event_loop().run_in_executor(
        None, _do_search,
    )


class TwitterScraper(BaseScraper):
    source = "twitter"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    async def search(self, query: dict[str, Any]) -> list[SocialPost]:
        """Search Twitter/X for posts matching the query.

        `query` schema (T9.0 Social Signal Agent):
          - keywords: list[str] | str  (search terms)
          - location: str | None
          - max_results: int  (cap, default settings.twitter_search_max_per_query)
          - max_age_days: int  (filter by recency, default settings.twitter_max_age_days)

        Returns: list of SocialPost. Never raises when
        settings.twitter_soft_fail=True (the default); the empty
        list is the signal that "no posts this run".
        """
        keywords = query.get("keywords") or query.get("q") or ""
        if isinstance(keywords, list):
            keywords = " ".join(keywords)
        keywords = keywords.strip()
        if not keywords:
            if settings.twitter_soft_fail:
                logger.warning("Twitter search: empty keywords, skipping")
                return []
            raise ScraperError("Twitter: 'keywords' is required")

        location = (query.get("location") or "").strip()
        max_results = int(
            query.get("max_results") or settings.twitter_search_max_per_query
        )
        max_age_days = int(
            query.get("max_age_days") or settings.twitter_max_age_days
        )
        # Append location to search query (X doesn't have a separate
        # location param for the cookie API path).
        full_query = f"{keywords} {location}".strip() if location else keywords

        cookies = _validate_cookies_file(settings.twitter_cookies_path)
        if not cookies:
            if settings.twitter_soft_fail:
                return []
            raise ScraperError(
                f"Twitter cookies not available at "
                f"{settings.twitter_cookies_path}. "
                f"Run scripts/setup_social_cookies.py to install."
            )

        logger.info(
            "Twitter search: q=%r max=%d age=%dd",
            full_query, max_results, max_age_days,
        )

        try:
            posts = await _search_twikit(
                cookies, full_query, max_results, max_age_days,
            )
        except ImportError:
            logger.warning(
                "twikit not importable — Twitter scan skipped. "
                "pip install twikit==2.0.0 to enable."
            )
            return [] if settings.twitter_soft_fail else _raise("twikit missing")
        except Exception as e:  # noqa: BLE001
            # Twikit raises various exceptions (auth fail, rate limit,
            # network). Soft-fail: log and return empty.
            if settings.twitter_soft_fail:
                logger.warning(
                    "Twitter search failed (soft-fail): %s: %s",
                    type(e).__name__, e,
                )
                return []
            raise ScraperError(f"Twitter search failed: {e}") from e

        logger.info("Twitter returned %d posts for q=%r", len(posts), full_query)
        return posts


# Helper for the soft_fail=False path (avoiding long line in search)
def _raise(msg: str) -> None:
    raise ScraperError(msg)


__all__ = ["TwitterScraper", "SocialPost", "_validate_cookies_file"]
