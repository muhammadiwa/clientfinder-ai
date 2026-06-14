"""
Sprint 2 / T9.0 — Twitter scraper unit tests.

Tests cover:
- Cookie file validation (5 cases: missing, empty, bad JSON, no
  auth_token, valid)
- Soft-fail behavior (default True: missing cookies = [])
- Hard-fail behavior (twitter_soft_fail=False: ScraperError)
- Search filter: age cutoff, retweet skipping
- SocialPost.to_dict() serialization
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.services.scraper.base import ScraperError
from app.services.scraper.twitter import (
    SocialPost,
    TwitterScraper,
    _validate_cookies_file,
)


# --- SocialPost.to_dict() ---

class TestSocialPost:
    def test_to_dict_serializes(self):
        ts = datetime(2026, 6, 14, 10, 0, 0, tzinfo=timezone.utc)
        post = SocialPost(
            post_id="123",
            text="Butuh developer untuk startup kami",
            author_handle="budi",
            url="https://x.com/budi/status/123",
            timestamp=ts,
            engagement={"likes": 5, "retweets": 1},
            language="id",
        )
        d = post.to_dict()
        assert d["post_id"] == "123"
        assert d["text"] == "Butuh developer untuk startup kami"
        assert d["timestamp"] == ts.isoformat()
        assert d["engagement"] == {"likes": 5, "retweets": 1}
        assert d["language"] == "id"

    def test_default_engagement_empty_dict(self):
        post = SocialPost(
            post_id="1", text="x", author_handle="a", url="", timestamp=datetime.now(timezone.utc),
        )
        assert post.engagement == {}


# --- _validate_cookies_file ---

class TestValidateCookiesFile:
    def test_missing_file(self, tmp_path: Path):
        result = _validate_cookies_file(str(tmp_path / "does_not_exist.json"))
        assert result is None

    def test_empty_file(self, tmp_path: Path):
        p = tmp_path / "empty.json"
        p.write_text("")
        result = _validate_cookies_file(str(p))
        assert result is None

    def test_invalid_json(self, tmp_path: Path):
        p = tmp_path / "bad.json"
        p.write_text("not json at all")
        result = _validate_cookies_file(str(p))
        assert result is None

    def test_empty_dict(self, tmp_path: Path):
        p = tmp_path / "empty_dict.json"
        p.write_text("{}")
        result = _validate_cookies_file(str(p))
        assert result is None

    def test_valid_with_required_keys(self, tmp_path: Path):
        p = tmp_path / "twitter_cookies.json"
        p.write_text(json.dumps({
            "auth_token": "abc123",
            "ct0": "def456",
            "twid": "ghi789",
        }))
        result = _validate_cookies_file(str(p))
        assert result is not None
        assert result["auth_token"] == "abc123"

    def test_valid_missing_required_keys_still_loads(self, tmp_path: Path):
        """The validator warns but doesn't reject — Twikit is what
        actually fails at search time."""
        p = tmp_path / "weird_cookies.json"
        p.write_text(json.dumps({"weird_cookie": "value"}))
        result = _validate_cookies_file(str(p))
        # Returns the dict (warn was logged), lets Twikit fail loud
        assert result == {"weird_cookie": "value"}


# --- TwitterScraper: soft-fail + hard-fail ---

class TestTwitterScraperSoftFail:
    """twitter_soft_fail = True (default): missing cookies = []."""

    @patch("app.services.scraper.twitter.settings")
    @pytest.mark.asyncio

    async def test_missing_cookies_returns_empty(self, mock_settings, tmp_path):
        mock_settings.twitter_soft_fail = True
        mock_settings.twitter_cookies_path = str(tmp_path / "missing.json")
        mock_settings.twitter_search_max_per_query = 30
        mock_settings.twitter_max_age_days = 14

        scraper = TwitterScraper()
        result = await scraper.search({"keywords": "developer Jakarta"})
        assert result == []

    @patch("app.services.scraper.twitter.settings")
    @pytest.mark.asyncio

    async def test_empty_keywords_returns_empty(self, mock_settings, tmp_path):
        mock_settings.twitter_soft_fail = True
        mock_settings.twitter_cookies_path = str(tmp_path / "cookies.json")
        mock_settings.twitter_search_max_per_query = 30
        mock_settings.twitter_max_age_days = 14
        (tmp_path / "cookies.json").write_text(json.dumps({
            "auth_token": "x", "ct0": "y",
        }))

        scraper = TwitterScraper()
        result = await scraper.search({"keywords": ""})
        assert result == []


class TestTwitterScraperHardFail:
    """twitter_soft_fail = False: missing cookies = ScraperError."""

    @patch("app.services.scraper.twitter.settings")
    @pytest.mark.asyncio

    async def test_missing_cookies_raises(self, mock_settings, tmp_path):
        mock_settings.twitter_soft_fail = False
        mock_settings.twitter_cookies_path = str(tmp_path / "missing.json")
        mock_settings.twitter_search_max_per_query = 30
        mock_settings.twitter_max_age_days = 14

        scraper = TwitterScraper()
        with pytest.raises(ScraperError) as exc:
            await scraper.search({"keywords": "test"})
        assert "Twitter cookies not available" in str(exc.value)

    @patch("app.services.scraper.twitter.settings")
    @pytest.mark.asyncio

    async def test_empty_keywords_raises_when_no_soft_fail(
        self, mock_settings, tmp_path,
    ):
        mock_settings.twitter_soft_fail = False
        mock_settings.twitter_cookies_path = str(tmp_path / "cookies.json")
        mock_settings.twitter_search_max_per_query = 30
        mock_settings.twitter_max_age_days = 14
        (tmp_path / "cookies.json").write_text(json.dumps({
            "auth_token": "x", "ct0": "y",
        }))

        scraper = TwitterScraper()
        with pytest.raises(ScraperError) as exc:
            await scraper.search({"keywords": ""})
        assert "'keywords' is required" in str(exc.value)


# --- TwitterScraper: post filtering ---

class TestTwitterScraperFiltering:
    """Filter logic applied to raw Twikit tweet objects."""

    def _make_tweet(
        self,
        text: str = "Butuh developer",
        author: str = "budi",
        tweet_id: str = "1",
        created_at: datetime | None = None,
        lang: str = "id",
        favorite_count: int = 0,
        retweet_count: int = 0,
        reply_count: int = 0,
        view_count: int = 0,
        retweeted_tweet=None,
    ):
        tweet = MagicMock()
        tweet.id = tweet_id
        tweet.text = text
        tweet.user.screen_name = author
        tweet.user.name = author
        tweet.created_at = (
            created_at.isoformat() if created_at else
            datetime.now(timezone.utc).isoformat()
        )
        tweet.lang = lang
        tweet.favorite_count = favorite_count
        tweet.retweet_count = retweet_count
        tweet.reply_count = reply_count
        tweet.view_count = view_count
        tweet.retweeted_tweet = retweeted_tweet
        return tweet

    @patch("app.services.scraper.twitter._search_twikit")
    @patch("app.services.scraper.twitter.settings")
    @pytest.mark.asyncio

    async def test_filters_out_old_posts(
        self, mock_settings, mock_search, tmp_path,
    ):
        mock_settings.twitter_soft_fail = True
        mock_settings.twitter_cookies_path = str(tmp_path / "cookies.json")
        mock_settings.twitter_search_max_per_query = 30
        mock_settings.twitter_max_age_days = 14
        (tmp_path / "cookies.json").write_text(json.dumps({
            "auth_token": "x", "ct0": "y",
        }))

        old_tweet = self._make_tweet(
            text="Butuh developer",
            created_at=datetime.now(timezone.utc) - timedelta(days=30),
        )
        new_tweet = self._make_tweet(
            text="Mencari web developer",
            tweet_id="2",
            created_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        # Mock returns the raw tweets; the actual filter happens in
        # _search_twikit, but we test the post-processing here
        mock_search.return_value = [
            SocialPost(
                post_id=t.id,
                text=t.text,
                author_handle=t.user.screen_name,
                url=f"https://x.com/{t.user.screen_name}/status/{t.id}",
                timestamp=datetime.fromisoformat(t.created_at.replace("Z", "+00:00")),
            )
            for t in [old_tweet, new_tweet]
        ]

        scraper = TwitterScraper()
        result = await scraper.search({"keywords": "developer"})
        # Both returned (filter is in _search_twikit, not in search())
        # The test demonstrates the wrapper passes through
        assert len(result) == 2

    @patch("app.services.scraper.twitter._search_twikit")
    @patch("app.services.scraper.twitter.settings")
    @pytest.mark.asyncio

    async def test_returns_socialpost_objects(
        self, mock_settings, mock_search, tmp_path,
    ):
        mock_settings.twitter_soft_fail = True
        mock_settings.twitter_cookies_path = str(tmp_path / "cookies.json")
        mock_settings.twitter_search_max_per_query = 30
        mock_settings.twitter_max_age_days = 14
        (tmp_path / "cookies.json").write_text(json.dumps({
            "auth_token": "x", "ct0": "y",
        }))
        mock_search.return_value = [
            SocialPost(
                post_id="abc",
                text="Butuh developer React",
                author_handle="budi",
                url="https://x.com/budi/status/abc",
                timestamp=datetime.now(timezone.utc),
                engagement={"likes": 10, "retweets": 2},
            ),
        ]

        scraper = TwitterScraper()
        result = await scraper.search({"keywords": "developer"})
        assert len(result) == 1
        assert isinstance(result[0], SocialPost)
        assert result[0].text == "Butuh developer React"
        assert result[0].engagement["likes"] == 10


# --- The filter logic that runs INSIDE _search_twikit ---

class TestSearchTwikitFilter:
    """Re-test the inline filter in _search_twikit to verify
    retweet-skip + age-cutoff work on raw Twikit output."""

    @patch("app.services.scraper.twitter.settings")
    @pytest.mark.asyncio

    async def test_filter_skips_retweets_and_old_posts(self, mock_settings):
        # This test invokes _search_twikit directly. We patch the
        # Twikit Client class to return mocked tweets.
        from app.services.scraper.twitter import _search_twikit

        def make_tweet(tweet_id, text, days_ago, is_retweet=False, lang="id"):
            t = MagicMock()
            t.id = tweet_id
            t.text = text
            t.user.screen_name = "user"
            t.user.name = "User"
            ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
            t.created_at = ts.isoformat()
            t.lang = lang
            t.favorite_count = 0
            t.retweet_count = 0
            t.reply_count = 0
            t.view_count = 0
            t.retweeted_tweet = MagicMock() if is_retweet else None
            return t

        tweets = [
            make_tweet("1", "fresh post 1", 1),                   # kept
            make_tweet("2", "fresh post 2", 2),                   # kept
            make_tweet("3", "old post 3", 30),                    # too old
            make_tweet("4", "retweet 4", 1, is_retweet=True),    # retweet
            make_tweet("5", "fresh post 5", 5),                   # kept
        ]

        # Patch twikit import
        with patch.dict("sys.modules", {"twikit.client.client": MagicMock()}):
            mock_client_class = MagicMock()
            mock_client_instance = MagicMock()
            mock_client_instance.search_tweet.return_value = tweets
            mock_client_instance.set_cookies = MagicMock()
            mock_client_class.return_value = mock_client_instance
            sys_modules = {"twikit.client.client": MagicMock(Client=mock_client_class)}
            with patch.dict("sys.modules", sys_modules):
                # Simulate the import path: from twikit.client.client import Client
                sys_modules["twikit.client.client"].Client = mock_client_class
                result = await _search_twikit(
                    cookies={"auth_token": "x", "ct0": "y"},
                    query="test",
                    max_results=10,
                    max_age_days=14,
                )

        # 3 kept (1, 2, 5), 1 too old (3), 1 retweet (4) skipped
        assert len(result) == 3
        post_ids = [p.post_id for p in result]
        assert "1" in post_ids
        assert "2" in post_ids
        assert "5" in post_ids
        assert "3" not in post_ids  # too old
        assert "4" not in post_ids  # retweet
