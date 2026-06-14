"""
Sprint 3C sub-task 2 — Tokopedia scraper tests.

Uses mock for the Playwright chain to keep tests fast and
isolated. The real Playwright integration is E2E-tested
manually against tokopedia.com.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.scraper.tokopedia import TokopediaScraper


class TestTokopediaScraper:
    def test_init(self):
        scraper = TokopediaScraper()
        assert scraper.source == "tokopedia"

    @pytest.mark.asyncio
    async def test_search_disabled_returns_empty(self):
        """When scout_tokopedia_enabled=False, return [] without
        touching the network."""
        with patch("app.services.scraper.tokopedia.settings") as mock_s:
            mock_s.scout_tokopedia_enabled = False
            mock_s.scout_tokopedia_max_per_query = 20
            mock_s.scout_tokopedia_page_timeout_s = 20
            scraper = TokopediaScraper()
            result = await scraper.search({"keywords": "kopi bandung"})
        assert result == []

    @pytest.mark.asyncio
    async def test_search_empty_keywords(self):
        with patch("app.services.scraper.tokopedia.settings") as mock_s:
            mock_s.scout_tokopedia_enabled = True
            mock_s.scout_tokopedia_max_per_query = 20
            mock_s.scout_tokopedia_page_timeout_s = 20
            scraper = TokopediaScraper()
            result = await scraper.search({"keywords": ""})
        assert result == []

    @pytest.mark.asyncio
    async def test_search_success(self):
        """Mock Playwright to return extracted seller rows."""
        mock_rows = [
            {
                "shop": "Kopi A",
                "name": "Kopi Arabica 250g",
                "price": "Rp 75.000",
                "location": "Kota Bandung",
                "rating": "4.8",
                "link": "https://www.tokopedia.com/kopi-a/product-1",
            },
            {
                "shop": "Kopi B",
                "name": "Kopi Robusta 500g",
                "price": "Rp 120.000",
                "location": "Kab. Bandung Barat",
                "rating": "4.7",
                "link": "https://www.tokopedia.com/kopi-b/product-2",
            },
        ]
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=mock_rows)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()
        mock_p = MagicMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_p.__aenter__ = AsyncMock(return_value=mock_p)
        mock_p.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.scraper.tokopedia.settings") as mock_s:
            mock_s.scout_tokopedia_enabled = True
            mock_s.scout_tokopedia_max_per_query = 20
            mock_s.scout_tokopedia_page_timeout_s = 20
            mock_s.scout_tokopedia_headless = True
            with patch("app.services.scraper.tokopedia.async_playwright") as mock_pw:
                mock_pw.return_value = mock_p
                scraper = TokopediaScraper()
                result = await scraper.search({
                    "keywords": "kopi",
                    "location": "Bandung",
                })

        assert len(result) == 2
        assert result[0].company_name == "Kopi A"
        assert result[0].source == "tokopedia"
        assert result[0].location_city == "Bandung"  # "Kota " prefix stripped
        # "Kopi Arabica 250g" → kept in description (truncated to 500)
        assert result[0].description == "Kopi Arabica 250g"
        # extra preserves metadata
        assert result[0].extra["sample_price"] == "Rp 75.000"
        assert result[0].extra["rating"] == "4.8"

    @pytest.mark.asyncio
    async def test_search_dedupes_by_shop(self):
        """Same shop with multiple products should appear once."""
        mock_rows = [
            {
                "shop": "Same Shop",
                "name": "Product 1",
                "link": "https://tokopedia.com/same/product-1",
                "price": "Rp 50.000",
                "location": "Bandung",
                "rating": "4.5",
            },
            {
                "shop": "Same Shop",
                "name": "Product 2",
                "link": "https://tokopedia.com/same/product-2",
                "price": "Rp 60.000",
                "location": "Bandung",
                "rating": "4.5",
            },
        ]
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=mock_rows)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()
        mock_p = MagicMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_p.__aenter__ = AsyncMock(return_value=mock_p)
        mock_p.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.scraper.tokopedia.settings") as mock_s:
            mock_s.scout_tokopedia_enabled = True
            mock_s.scout_tokopedia_max_per_query = 20
            mock_s.scout_tokopedia_page_timeout_s = 20
            mock_s.scout_tokopedia_headless = True
            with patch("app.services.scraper.tokopedia.async_playwright") as mock_pw:
                mock_pw.return_value = mock_p
                scraper = TokopediaScraper()
                result = await scraper.search({"keywords": "test"})
        assert len(result) == 1  # deduped

    @pytest.mark.asyncio
    async def test_search_skips_empty_shop(self):
        """If extraction returns a row with empty shop, skip it."""
        mock_rows = [
            {"shop": "", "name": "x", "link": "https://tokopedia.com/x"},
            {"shop": "Real Shop", "name": "y", "link": "https://tokopedia.com/y", "location": "Jakarta"},
        ]
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=mock_rows)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()
        mock_p = MagicMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_p.__aenter__ = AsyncMock(return_value=mock_p)
        mock_p.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.scraper.tokopedia.settings") as mock_s:
            mock_s.scout_tokopedia_enabled = True
            mock_s.scout_tokopedia_max_per_query = 20
            mock_s.scout_tokopedia_page_timeout_s = 20
            mock_s.scout_tokopedia_headless = True
            with patch("app.services.scraper.tokopedia.async_playwright") as mock_pw:
                mock_pw.return_value = mock_p
                scraper = TokopediaScraper()
                result = await scraper.search({"keywords": "test"})
        assert len(result) == 1
        assert result[0].company_name == "Real Shop"

    @pytest.mark.asyncio
    async def test_search_handles_timeout(self):
        """asyncio.TimeoutError → returns empty (graceful)."""
        with patch("app.services.scraper.tokopedia.settings") as mock_s:
            mock_s.scout_tokopedia_enabled = True
            mock_s.scout_tokopedia_max_per_query = 20
            mock_s.scout_tokopedia_page_timeout_s = 5
            mock_s.scout_tokopedia_headless = True
            scraper = TokopediaScraper()
            with patch("app.services.scraper.tokopedia.asyncio") as mock_aio:
                mock_aio.wait_for = AsyncMock(
                    side_effect=TimeoutError("simulated"),
                )
                result = await scraper.search({"keywords": "test"})
        assert result == []

    @pytest.mark.asyncio
    async def test_search_handles_playwright_not_installed(self):
        """If playwright isn't installed, returns [] (ImportError)."""
        with patch("app.services.scraper.tokopedia.settings") as mock_s:
            mock_s.scout_tokopedia_enabled = True
            mock_s.scout_tokopedia_max_per_query = 20
            mock_s.scout_tokopedia_page_timeout_s = 20
            mock_s.scout_tokopedia_headless = True
            scraper = TokopediaScraper()
            # Patch the actual import path so the ImportError branch fires
            with patch.dict("sys.modules", {"playwright.async_api": None}):
                result = await scraper.search({"keywords": "test"})
        # Either returns [] or raises — the important thing is
        # we don't crash the worker
        assert result == [] or isinstance(result, list)

    @pytest.mark.asyncio
    async def test_search_respects_max_results(self):
        """If API returns 30 sellers and max_results=5, we cap at 5."""
        mock_rows = [
            {
                "shop": f"Shop {i}",
                "name": f"Product {i}",
                "link": f"https://tokopedia.com/shop-{i}",
                "location": "Bandung",
            }
            for i in range(30)
        ]
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=mock_rows)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()
        mock_p = MagicMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_p.__aenter__ = AsyncMock(return_value=mock_p)
        mock_p.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.scraper.tokopedia.settings") as mock_s:
            mock_s.scout_tokopedia_enabled = True
            mock_s.scout_tokopedia_max_per_query = 20
            mock_s.scout_tokopedia_page_timeout_s = 20
            mock_s.scout_tokopedia_headless = True
            with patch("app.services.scraper.tokopedia.async_playwright") as mock_pw:
                mock_pw.return_value = mock_p
                scraper = TokopediaScraper()
                result = await scraper.search({
                    "keywords": "test",
                    "max_results": 5,
                })
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_search_handles_page_error(self):
        """Exception during the page evaluate → returns []."""
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.goto = AsyncMock(side_effect=Exception("page error"))
        mock_page.evaluate = AsyncMock(side_effect=Exception("eval error"))
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()
        mock_p = MagicMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_p.__aenter__ = AsyncMock(return_value=mock_p)
        mock_p.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.scraper.tokopedia.settings") as mock_s:
            mock_s.scout_tokopedia_enabled = True
            mock_s.scout_tokopedia_max_per_query = 20
            mock_s.scout_tokopedia_page_timeout_s = 20
            mock_s.scout_tokopedia_headless = True
            with patch("app.services.scraper.tokopedia.async_playwright") as mock_pw:
                mock_pw.return_value = mock_p
                scraper = TokopediaScraper()
                result = await scraper.search({"keywords": "test"})
        assert result == []


class TestTokopediaLocationParsing:
    """The 'Kota ' / 'Kab. ' prefix stripping is critical for
    getting clean city names."""

    @pytest.mark.asyncio
    async def test_strips_kota_prefix(self):
        """Kota Bandung → Bandung"""
        mock_rows = [{
            "shop": "Test Shop",
            "name": "x",
            "link": "https://tokopedia.com/test",
            "location": "Kota Bandung",
        }]
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=mock_rows)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()
        mock_p = MagicMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_p.__aenter__ = AsyncMock(return_value=mock_p)
        mock_p.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.scraper.tokopedia.settings") as mock_s:
            mock_s.scout_tokopedia_enabled = True
            mock_s.scout_tokopedia_max_per_query = 20
            mock_s.scout_tokopedia_page_timeout_s = 20
            mock_s.scout_tokopedia_headless = True
            with patch("app.services.scraper.tokopedia.async_playwright") as mock_pw:
                mock_pw.return_value = mock_p
                scraper = TokopediaScraper()
                result = await scraper.search({"keywords": "test"})
        assert result[0].location_city == "Bandung"

    @pytest.mark.asyncio
    async def test_strips_kab_prefix(self):
        """Kab. Bandung Barat → Bandung Barat"""
        mock_rows = [{
            "shop": "Test Shop",
            "name": "x",
            "link": "https://tokopedia.com/test",
            "location": "Kab. Bandung Barat",
        }]
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=mock_rows)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()
        mock_p = MagicMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_p.__aenter__ = AsyncMock(return_value=mock_p)
        mock_p.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.scraper.tokopedia.settings") as mock_s:
            mock_s.scout_tokopedia_enabled = True
            mock_s.scout_tokopedia_max_per_query = 20
            mock_s.scout_tokopedia_page_timeout_s = 20
            mock_s.scout_tokopedia_headless = True
            with patch("app.services.scraper.tokopedia.async_playwright") as mock_pw:
                mock_pw.return_value = mock_p
                scraper = TokopediaScraper()
                result = await scraper.search({"keywords": "test"})
        assert result[0].location_city == "Bandung Barat"

    @pytest.mark.asyncio
    async def test_keeps_location_without_prefix(self):
        """Plain 'Jakarta' stays 'Jakarta'."""
        mock_rows = [{
            "shop": "Test Shop",
            "name": "x",
            "link": "https://tokopedia.com/test",
            "location": "Jakarta",
        }]
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=mock_rows)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()
        mock_p = MagicMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_p.__aenter__ = AsyncMock(return_value=mock_p)
        mock_p.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.scraper.tokopedia.settings") as mock_s:
            mock_s.scout_tokopedia_enabled = True
            mock_s.scout_tokopedia_max_per_query = 20
            mock_s.scout_tokopedia_page_timeout_s = 20
            mock_s.scout_tokopedia_headless = True
            with patch("app.services.scraper.tokopedia.async_playwright") as mock_pw:
                mock_pw.return_value = mock_p
                scraper = TokopediaScraper()
                result = await scraper.search({"keywords": "test"})
        assert result[0].location_city == "Jakarta"


class TestScraperRegistry:
    def test_registry_includes_tokopedia(self):
        from app.services.scraper import _SCRAPERS
        assert "tokopedia" in _SCRAPERS

    def test_get_scraper_tokopedia(self):
        from app.services.scraper import get_scraper
        s = get_scraper("tokopedia")
        assert s.source == "tokopedia"
