"""
Sprint 3C sub-task 1 — Google Places + Yelp scraper tests.

Uses AsyncMock + httpx mock to test the API integration without
making real network calls.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.scraper.google_places import GooglePlacesScraper
from app.services.scraper.yelp import YelpScraper


# --- GooglePlacesScraper ---


class TestGooglePlacesScraper:
    def test_init_without_api_key_logs_warning(self):
        with patch("app.services.scraper.google_places.settings") as mock_s:
            mock_s.google_places_api_key = ""
            scraper = GooglePlacesScraper()
            assert scraper.api_key == ""

    def test_init_with_api_key(self):
        with patch("app.services.scraper.google_places.settings") as mock_s:
            mock_s.google_places_api_key = "test-key-123"
            scraper = GooglePlacesScraper()
            assert scraper.api_key == "test-key-123"

    @pytest.mark.asyncio
    async def test_search_no_api_key_returns_empty(self):
        with patch("app.services.scraper.google_places.settings") as mock_s:
            mock_s.google_places_api_key = ""
            scraper = GooglePlacesScraper()
            result = await scraper.search({"keywords": "kafe bandung"})
        assert result == []

    @pytest.mark.asyncio
    async def test_search_empty_keywords_returns_empty(self):
        with patch("app.services.scraper.google_places.settings") as mock_s:
            mock_s.google_places_api_key = "test-key"
            mock_s.scout_google_places_max_per_query = 30
            scraper = GooglePlacesScraper()
            result = await scraper.search({"keywords": ""})
        assert result == []

    @pytest.mark.asyncio
    async def test_search_success(self):
        """Mock httpx to return a Google Places response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "name": "Kafe A",
                    "place_id": "place-1",
                    "formatted_address": "Jl. Asia Afrika, Bandung, West Java, Indonesia",
                    "rating": 4.5,
                    "user_ratings_total": 200,
                    "types": ["cafe", "restaurant"],
                    "business_status": "OPERATIONAL",
                    "geometry": {"location": {"lat": -6.9, "lng": 107.6}},
                },
                {
                    "name": "Kafe B",
                    "place_id": "place-2",
                    "formatted_address": "Jl. Braga, Bandung, West Java, Indonesia",
                    "rating": 4.2,
                    "user_ratings_total": 50,
                    "types": ["cafe"],
                    "business_status": "OPERATIONAL",
                },
            ],
        }
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.scraper.google_places.settings") as mock_s:
            mock_s.google_places_api_key = "test-key"
            mock_s.scout_google_places_max_per_query = 30
            with patch("app.services.scraper.google_places.httpx.AsyncClient") as mock_httpx:
                mock_httpx.return_value = mock_client
                scraper = GooglePlacesScraper()
                results = await scraper.search({
                    "keywords": "kafe",
                    "location": "Bandung",
                })

        assert len(results) == 2
        assert results[0].company_name == "Kafe A"
        assert results[0].source == "google_places"
        # Location parsed: "Jl. Asia Afrika" (street), "Bandung" (city),
        # "West Java" (province), "Indonesia" (country)
        assert results[0].location_city == "Bandung"
        assert results[0].location_province == "West Java"
        # extra metadata preserved
        assert results[0].extra["place_id"] == "place-1"
        assert results[0].extra["rating"] == 4.5
        assert "cafe" in results[0].extra["types"]

    @pytest.mark.asyncio
    async def test_search_zero_results(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ZERO_RESULTS", "results": []}
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.scraper.google_places.settings") as mock_s:
            mock_s.google_places_api_key = "test-key"
            mock_s.scout_google_places_max_per_query = 30
            with patch("app.services.scraper.google_places.httpx.AsyncClient") as mock_httpx:
                mock_httpx.return_value = mock_client
                scraper = GooglePlacesScraper()
                results = await scraper.search({"keywords": "anything"})
        assert results == []

    @pytest.mark.asyncio
    async def test_search_api_error(self):
        """Non-OK API status returns empty (graceful degradation)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "REQUEST_DENIED",
            "error_message": "API key invalid",
        }
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.scraper.google_places.settings") as mock_s:
            mock_s.google_places_api_key = "invalid-key"
            mock_s.scout_google_places_max_per_query = 30
            with patch("app.services.scraper.google_places.httpx.AsyncClient") as mock_httpx:
                mock_httpx.return_value = mock_client
                scraper = GooglePlacesScraper()
                results = await scraper.search({"keywords": "test"})
        assert results == []

    @pytest.mark.asyncio
    async def test_search_http_error(self):
        """HTTP 500 returns empty (graceful degradation)."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.scraper.google_places.settings") as mock_s:
            mock_s.google_places_api_key = "test-key"
            mock_s.scout_google_places_max_per_query = 30
            with patch("app.services.scraper.google_places.httpx.AsyncClient") as mock_httpx:
                mock_httpx.return_value = mock_client
                scraper = GooglePlacesScraper()
                results = await scraper.search({"keywords": "test"})
        assert results == []

    @pytest.mark.asyncio
    async def test_search_respects_max_results(self):
        """If API returns 50 and max_results=10, we cap at 10."""
        results_list = [
            {
                "name": f"Place {i}",
                "place_id": f"p-{i}",
                "formatted_address": "Bandung, Indonesia",
                "rating": 4.0,
            }
            for i in range(20)
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "OK", "results": results_list}
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.scraper.google_places.settings") as mock_s:
            mock_s.google_places_api_key = "test-key"
            mock_s.scout_google_places_max_per_query = 30
            with patch("app.services.scraper.google_places.httpx.AsyncClient") as mock_httpx:
                mock_httpx.return_value = mock_client
                scraper = GooglePlacesScraper()
                results = await scraper.search({
                    "keywords": "test",
                    "max_results": 10,
                })
        assert len(results) == 10


# --- YelpScraper ---


class TestYelpScraper:
    def test_init_without_api_key(self):
        with patch("app.services.scraper.yelp.settings") as mock_s:
            mock_s.yelp_api_key = ""
            scraper = YelpScraper()
            assert scraper.api_key == ""

    @pytest.mark.asyncio
    async def test_search_no_api_key_returns_empty(self):
        with patch("app.services.scraper.yelp.settings") as mock_s:
            mock_s.yelp_api_key = ""
            scraper = YelpScraper()
            result = await scraper.search({"keywords": "kafe", "location": "Bandung"})
        assert result == []

    @pytest.mark.asyncio
    async def test_search_no_location_uses_indonesia_fallback(self):
        """Yelp REQUIRES a location — fall back to 'Indonesia'."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "businesses": [
                {
                    "id": "yelp-1",
                    "name": "Kafe Mantap",
                    "alias": "kafe-mantap-bandung",
                    "url": "https://www.yelp.com/biz/kafe-mantap-bandung",
                    "phone": "+6222123456",
                    "rating": 4.5,
                    "review_count": 100,
                    "categories": [{"title": "Cafes"}, {"title": "Restaurants"}],
                    "price": "$$",
                    "is_closed": False,
                    "location": {
                        "display_address": ["Jl. Braga 99", "Bandung 40111", "Indonesia"],
                        "city": "Bandung",
                        "state": "JB",
                        "country": "ID",
                    },
                    "coordinates": {"latitude": -6.9, "longitude": 107.6},
                }
            ]
        }
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.scraper.yelp.settings") as mock_s:
            mock_s.yelp_api_key = "test-key"
            mock_s.scout_yelp_max_per_query = 30
            with patch("app.services.scraper.yelp.httpx.AsyncClient") as mock_httpx:
                mock_httpx.return_value = mock_client
                scraper = YelpScraper()
                results = await scraper.search({"keywords": "kafe"})
        assert len(results) == 1
        # The URL was used to extract domain
        assert results[0].website == "yelp.com"
        assert results[0].location_city == "Bandung"
        assert results[0].extra["yelp_id"] == "yelp-1"
        assert "Cafes" in results[0].extra["categories"]

    @pytest.mark.asyncio
    async def test_search_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "businesses": [
                {
                    "id": "biz-1",
                    "name": "Warung A",
                    "url": "https://www.yelp.com/biz/warung-a",
                    "phone": "+62 22 123",
                    "rating": 4.0,
                    "review_count": 50,
                    "categories": [{"title": "Indonesian"}],
                    "is_closed": False,
                    "location": {
                        "display_address": ["Jl. Asia Afrika 1", "Bandung"],
                        "city": "Bandung",
                        "state": "Jawa Barat",
                        "country": "ID",
                    },
                }
            ]
        }
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.scraper.yelp.settings") as mock_s:
            mock_s.yelp_api_key = "test-key"
            mock_s.scout_yelp_max_per_query = 30
            with patch("app.services.scraper.yelp.httpx.AsyncClient") as mock_httpx:
                mock_httpx.return_value = mock_client
                scraper = YelpScraper()
                results = await scraper.search({
                    "keywords": "warung",
                    "location": "Bandung",
                })
        assert len(results) == 1
        assert results[0].company_name == "Warung A"
        assert results[0].source == "yelp"
        assert results[0].location_address == "Jl. Asia Afrika 1, Bandung"

    @pytest.mark.asyncio
    async def test_search_http_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.scraper.yelp.settings") as mock_s:
            mock_s.yelp_api_key = "bad-key"
            mock_s.scout_yelp_max_per_query = 30
            with patch("app.services.scraper.yelp.httpx.AsyncClient") as mock_httpx:
                mock_httpx.return_value = mock_client
                scraper = YelpScraper()
                results = await scraper.search({"keywords": "test"})
        assert results == []

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"businesses": []}
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.scraper.yelp.settings") as mock_s:
            mock_s.yelp_api_key = "test-key"
            mock_s.scout_yelp_max_per_query = 30
            with patch("app.services.scraper.yelp.httpx.AsyncClient") as mock_httpx:
                mock_httpx.return_value = mock_client
                scraper = YelpScraper()
                results = await scraper.search({"keywords": "nothing"})
        assert results == []


# --- Registry ---


class TestScraperRegistry:
    def test_registry_includes_3c_sources(self):
        from app.services.scraper import _SCRAPERS
        assert "google_places" in _SCRAPERS
        assert "yelp" in _SCRAPERS

    def test_get_scraper_google_places(self):
        from app.services.scraper import get_scraper
        with patch("app.services.scraper.settings") as mock_s:
            mock_s.google_places_api_key = "test-key"
            s = get_scraper("google_places")
        assert s.source == "google_places"
        assert s.api_key == "test-key"

    def test_get_scraper_yelp(self):
        from app.services.scraper import get_scraper
        with patch("app.services.scraper.settings") as mock_s:
            mock_s.yelp_api_key = "test-key"
            s = get_scraper("yelp")
        assert s.source == "yelp"
        assert s.api_key == "test-key"
