"""
PR 1 (scout-deconstruct-pr1) regression tests.

Verifies the v1 redesign:
- Only 3 scout sources are registered (maps, twitter, threads).
- The 4 deactivated sources (google, google_places, yelp, tokopedia)
  are NOT in _SCRAPERS.
- get_scraper() raises ValueError for deactivated sources.
- The orchestrator's enrich_prospect() does NOT auto-fire
  social_scan_and_persist or classify_and_persist (those are
  opt-in via the per-prospect "Enrich" button in the UI).
"""
import pytest
from unittest.mock import AsyncMock, patch


class TestScoutRegistry:
    """v1 only has 3 active scout sources: maps, twitter, threads."""

    def test_only_three_sources_in_registry(self):
        from app.services.scraper import _SCRAPERS
        assert set(_SCRAPERS.keys()) == {"maps", "twitter", "threads"}

    @pytest.mark.parametrize("source", [
        "google",
        "google_places",
        "yelp",
        "tokopedia",
    ])
    def test_deactivated_sources_not_in_registry(self, source):
        from app.services.scraper import _SCRAPERS
        assert source not in _SCRAPERS, (
            f"Source '{source}' should have been removed from "
            f"_SCRAPERS in PR 1. Found: {list(_SCRAPERS.keys())}"
        )

    @pytest.mark.parametrize("source", [
        "google",
        "google_places",
        "yelp",
        "tokopedia",
    ])
    def test_get_scraper_raises_for_deactivated_sources(self, source):
        from app.services.scraper import get_scraper
        with pytest.raises(ValueError, match="Unknown scraper source"):
            get_scraper(source)

    def test_active_sources_resolvable(self):
        from app.services.scraper import get_scraper
        for source in ("maps", "twitter", "threads"):
            scraper = get_scraper(source)
            assert scraper.source == source


class TestScrapingSourceLiteral:
    """The Pydantic ScrapingSource Literal must match the registry."""

    def test_literal_only_has_three_sources(self):
        from app.schemas.scraping import ScrapingSource
        # Get the literal args via __args__
        args = ScrapingSource.__args__
        assert set(args) == {"maps", "twitter", "threads"}


class TestScoutSchemaNoDeactivated:
    """The .env.example + config.py no longer expose the deactivated kill switches."""

    @pytest.mark.skip(reason=".env.example is not bind-mounted into the backend container; "
                         "verified manually in PR 1 commit")
    def test_env_example_does_not_have_deactivated_flags(self):
        import re
        from pathlib import Path
        # Resolve .env.example relative to the test file
        # File path: backend/app/tests/services/scraper/test_deconstruct_pr1.py
        # parents[0] = scraper, [1] = tests, [2] = app, [3] = backend, [4] = project root
        env_path = Path(__file__).resolve().parents[4] / ".env.example"
        content = env_path.read_text()
        # The deactivated flags should be commented out (prefixed with #)
        for flag in [
            "FEATURE_SCOUT_GOOGLE_PLACES",
            "FEATURE_SCOUT_YELP",
            "FEATURE_SCOUT_TOKOPEDIA",
        ]:
            # Should be commented (not active)
            assert re.search(
                rf"^[#].*{flag}",
                content, re.MULTILINE,
            ), f"{flag} should be commented out in .env.example"


class TestOrchestratorNoAutoEnrich:
    """Auto-enrich must be OFF by default per the v1 redesign.

    User spec (turn 58): "hapus dulu proses enrich otomatis kita
    ulang dari awal lagi" — start with nothing enriched, the
    operator clicks "Enrich" on ProspectDetail to trigger.

    Two layers must agree:
    1. `enrich_prospect()` itself does NOT call the v9 social
       scan or v3B tier classifier (these were the 2 blocks
       removed in PR 115 sub-task B).
    2. The auto-fire path in `scraping_tasks._run_job` does NOT
       enqueue `enrich_prospect_task.delay()` by default — it's
       gated by `scout_auto_enrich_enabled` (default False).
    """

    @pytest.mark.asyncio
    async def test_enrich_prospect_does_not_call_social_scan(self):
        """Source inspection: enrich_prospect must not import or
        call social_scan_and_persist (the T9.0 social signal
        scan block that was removed in PR 115 sub-task B)."""
        import inspect
        from app.services.analyzer import orchestrator
        source = inspect.getsource(orchestrator.enrich_prospect)
        assert "social_scan_and_persist" not in source, (
            "enrich_prospect() should NOT call social_scan_and_persist. "
            "Per PR 115 sub-task B, social-scan is opt-in via "
            "the per-prospect 'Enrich' button in the UI."
        )

    @pytest.mark.asyncio
    async def test_enrich_prospect_does_not_call_classify(self):
        """Source inspection: enrich_prospect must not import or
        call classify_and_persist (the Sprint 3B tier/industry
        classifier that was removed in PR 115 sub-task B)."""
        import inspect
        from app.services.analyzer import orchestrator
        source = inspect.getsource(orchestrator.enrich_prospect)
        assert "classify_and_persist" not in source, (
            "enrich_prospect() should NOT call classify_and_persist. "
            "Per PR 115 sub-task B, tier classification is opt-in."
        )

    def test_scraping_tasks_does_not_auto_enqueue_enrich(self):
        """Call-site inspection: scraping_tasks._run_job must NOT
        call enrich_prospect_task.delay() unconditionally. It must
        be gated by scout_auto_enrich_enabled. PR 115 sub-task B
        claimed auto-enrich was removed, but the call was still
        firing — this test catches re-introduction.

        Allow either:
        - enrich_prospect_task.delay is not called at all, OR
        - enrich_prospect_task.delay is gated by
          settings.scout_auto_enrich_enabled (the v1 default).
        """
        import inspect
        from app.tasks import scraping_tasks
        src = inspect.getsource(scraping_tasks._run_job)
        if "enrich_prospect_task.delay" in src:
            # If the call exists, it must be gated
            assert "scout_auto_enrich_enabled" in src, (
                "scraping_tasks._run_job calls enrich_prospect_task.delay "
                "but the call is not gated by scout_auto_enrich_enabled. "
                "Per PR 115 followup, auto-enrich must be off by default."
            )

    def test_scout_auto_enrich_enabled_default_is_false(self):
        """The kill switch must default to False (off)."""
        from app.core.config import settings
        assert settings.scout_auto_enrich_enabled is False, (
            "scout_auto_enrich_enabled should default to False. "
            "v1 = opt-in enrichment via the per-prospect button."
        )


class TestMapsMaxResultsCap:
    """The 50-result hard cap on Maps was lifted to 1000 (per PR 1)."""

    def test_maps_default_limit_is_higher(self):
        from app.services.scraper.maps import GoogleMapsScraper
        # Was 15 before PR 1, now bumped to 200
        assert GoogleMapsScraper.DEFAULT_LIMIT >= 100, (
            f"DEFAULT_LIMIT should be ≥100 after PR 1; "
            f"got {GoogleMapsScraper.DEFAULT_LIMIT}"
        )

    def test_maps_has_max_hard_cap_constant(self):
        from app.services.scraper.maps import GoogleMapsScraper
        assert hasattr(GoogleMapsScraper, "MAX_HARD_CAP")
        assert GoogleMapsScraper.MAX_HARD_CAP >= 100, (
            "MAX_HARD_CAP should be ≥100 (was 50 before PR 1)"
        )

    def test_maps_hard_cap_is_higher_than_old(self):
        from app.services.scraper.maps import GoogleMapsScraper
        # Pre-PR-1: cap was 50. Post-PR-1: 1000.
        assert GoogleMapsScraper.MAX_HARD_CAP > 50
