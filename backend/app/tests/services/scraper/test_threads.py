"""
Sprint 2 / T9.0 — Threads scraper unit tests.

Mirrors test_twitter.py pattern but for the Playwright-based
Threads scraper. Tests cover:
- Cookie validation (5 cases)
- Soft-fail + hard-fail behavior
- Search filter (age cutoff)
- DOM extraction via page.evaluate() with mocked Playwright
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.scraper.base import ScraperError
from app.services.scraper.threads import (
    ThreadsScraper,
    _validate_threads_cookies,
)


# --- _validate_threads_cookies ---

class TestValidateThreadsCookies:
    def test_missing_file(self, tmp_path: Path):
        result = _validate_threads_cookies(str(tmp_path / "missing.json"))
        assert result is None

    def test_empty_file(self, tmp_path: Path):
        p = tmp_path / "empty.json"
        p.write_text("")
        result = _validate_threads_cookies(str(p))
        assert result is None

    def test_invalid_json(self, tmp_path: Path):
        p = tmp_path / "bad.json"
        p.write_text("not json")
        result = _validate_threads_cookies(str(p))
        assert result is None

    def test_valid_with_sessionid(self, tmp_path: Path):
        p = tmp_path / "threads_cookies.json"
        p.write_text(json.dumps({
            "sessionid": "abc123",
            "csrftoken": "def456",
            "ds_user_id": "12345",
        }))
        result = _validate_threads_cookies(str(p))
        assert result is not None
        assert result["sessionid"] == "abc123"

    def test_valid_missing_sessionid_still_loads(self, tmp_path: Path):
        """Validator warns but doesn't reject."""
        p = tmp_path / "weird.json"
        p.write_text(json.dumps({"weird_cookie": "value"}))
        result = _validate_threads_cookies(str(p))
        # Returns the dict; logs warning
        assert result == {"weird_cookie": "value"}


# --- ThreadsScraper: soft-fail + hard-fail ---

class TestThreadsScraperSoftFail:
    """twitter_soft_fail = True (default): missing cookies = []."""

    @patch("app.services.scraper.threads.settings")
    @pytest.mark.asyncio

    async def test_missing_cookies_returns_empty(self, mock_settings, tmp_path):
        mock_settings.twitter_soft_fail = True
        mock_settings.threads_cookies_path = str(tmp_path / "missing.json")
        mock_settings.twitter_search_max_per_query = 30
        mock_settings.twitter_max_age_days = 14

        scraper = ThreadsScraper()
        result = await scraper.search({"keywords": "developer"})
        assert result == []


class TestThreadsScraperHardFail:
    """twitter_soft_fail = False: missing cookies = ScraperError."""

    @patch("app.services.scraper.threads.settings")
    @pytest.mark.asyncio

    async def test_missing_cookies_raises(self, mock_settings, tmp_path):
        mock_settings.twitter_soft_fail = False
        mock_settings.threads_cookies_path = str(tmp_path / "missing.json")
        mock_settings.twitter_search_max_per_query = 30
        mock_settings.twitter_max_age_days = 14

        scraper = ThreadsScraper()
        with pytest.raises(ScraperError) as exc:
            await scraper.search({"keywords": "test"})
        assert "Threads cookies not available" in str(exc.value)


# --- DOM extraction with mocked Playwright ---

class TestThreadsPlaywrightExtraction:
    """Test the inner _search_threads_playwright with mocked browser."""

    @patch("app.services.scraper.threads._search_threads_playwright")
    @patch("app.services.scraper.threads.settings")
    @pytest.mark.asyncio

    async def test_returns_socialposts_from_raw_extraction(
        self, mock_settings, mock_search, tmp_path,
    ):
        from app.services.scraper.twitter import SocialPost

        mock_settings.twitter_soft_fail = True
        mock_settings.threads_cookies_path = str(tmp_path / "cookies.json")
        mock_settings.twitter_search_max_per_query = 30
        mock_settings.twitter_max_age_days = 14
        (tmp_path / "cookies.json").write_text(json.dumps({
            "sessionid": "x",
        }))

        mock_search.return_value = [
            SocialPost(
                post_id="Cabc123",
                text="Butuh web developer untuk startup",
                author_handle="budi",
                url="https://www.threads.net/@budi/post/Cabc123",
                timestamp=datetime.now(timezone.utc),
                engagement={},
                language="id",
            ),
            SocialPost(
                post_id="Cdef456",
                text="Mencari automation specialist",
                author_handle="sari",
                url="https://www.threads.net/@sari/post/Cdef456",
                timestamp=datetime.now(timezone.utc),
                engagement={},
                language="id",
            ),
        ]

        scraper = ThreadsScraper()
        result = await scraper.search({"keywords": "developer"})
        assert len(result) == 2
        assert all(isinstance(p, SocialPost) for p in result)
        assert result[0].text == "Butuh web developer untuk startup"
        assert result[1].author_handle == "sari"


# --- The inner filter logic (extracted) ---

class TestInnerFilter:
    """Verify the inner _search_threads_playwright correctly
    filters by age and parses URLs."""

    @patch("playwright.async_api.async_playwright")
    @patch("app.services.scraper.threads.settings")
    @pytest.mark.asyncio

    async def test_filter_drops_old_posts(self, mock_settings, mock_pw):
        """Post with time older than max_age_days is dropped."""
        from app.services.scraper.threads import _search_threads_playwright

        # The Playwright internals: mock page.evaluate to return
        # one fresh + one old post
        old_ts = datetime.now(timezone.utc) - timedelta(days=30)
        fresh_ts = datetime.now(timezone.utc) - timedelta(days=1)
        raw_extracted = [
            {
                "text": "old post",
                "url": "https://www.threads.net/@old/post/C111",
                "time": old_ts.isoformat(),
                "author": "old",
            },
            {
                "text": "fresh post",
                "url": "https://www.threads.net/@fresh/post/C222",
                "time": fresh_ts.isoformat(),
                "author": "fresh",
            },
        ]

        # Build mock Playwright chain
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=raw_extracted)
        mock_page.goto = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.add_cookies = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()
        mock_pw.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
            chromium=MagicMock(launch=AsyncMock(return_value=mock_browser))
        ))
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await _search_threads_playwright(
            cookies={"sessionid": "x"},
            query="test",
            max_results=10,
            max_age_days=14,
        )
        # Only the fresh post survives
        assert len(result) == 1
        assert result[0].text == "fresh post"
        assert result[0].author_handle == "fresh"

    @patch("playwright.async_api.async_playwright")
    @patch("app.services.scraper.threads.settings")
    @pytest.mark.asyncio

    async def test_parses_post_id_from_url(self, mock_settings, mock_pw):
        from app.services.scraper.threads import _search_threads_playwright

        raw = [{
            "text": "hello",
            "url": "https://www.threads.net/@alice/post/ABCxyz123",
            "time": datetime.now(timezone.utc).isoformat(),
            "author": "alice",
        }]
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=raw)
        mock_page.goto = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.add_cookies = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()
        mock_pw.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
            chromium=MagicMock(launch=AsyncMock(return_value=mock_browser))
        ))
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await _search_threads_playwright(
            cookies={"sessionid": "x"},
            query="test", max_results=10, max_age_days=14,
        )
        assert result[0].post_id == "ABCxyz123"
        assert result[0].author_handle == "alice"
        assert result[0].url.endswith("/post/ABCxyz123")

    @patch("playwright.async_api.async_playwright")
    @patch("app.services.scraper.threads.settings")
    @pytest.mark.asyncio

    async def test_skips_posts_with_no_text(self, mock_settings, mock_pw):
        from app.services.scraper.threads import _search_threads_playwright

        raw = [
            {"text": "", "url": "https://www.threads.net/@a/post/C1", "time": None, "author": "a"},
            {"text": "real", "url": "https://www.threads.net/@b/post/C2", "time": None, "author": "b"},
        ]
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=raw)
        mock_page.goto = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.add_cookies = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()
        mock_pw.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
            chromium=MagicMock(launch=AsyncMock(return_value=mock_browser))
        ))
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await _search_threads_playwright(
            cookies={"sessionid": "x"},
            query="test", max_results=10, max_age_days=14,
        )
        assert len(result) == 1
        assert result[0].text == "real"
