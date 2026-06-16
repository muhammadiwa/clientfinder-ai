"""
PR 2 (scout-run-fk-maps-full-data) regression tests.

Verifies:
1. The Maps `_parse_card` extracts the FULL Places data
   (rating, review_count, hours, price_range, service_options)
   and stuffs it into `extra` so it lands in `prospects.raw_data`.

2. The `scout_run_id` FK is in place + `persist_scraped_to_prospects`
   accepts a `scout_run_id` kwarg and stamps it on new prospects.

3. The `Prospect` model has the `scout_run_id` field with the
   correct FK to `scraping_jobs.id`.
"""
from importlib import resources
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestMapsFullDataExtraction:
    """Maps _parse_card extracts the full Places data, not just address."""

    @staticmethod
    def _make_card(name: str, full_text: str, href: str | None = None):
        """Construct a mock Playwright ElementHandle with the
        given aria-label + inner_text + optional website link.
        """
        card = MagicMock()
        card.get_attribute = AsyncMock(
            side_effect=lambda attr: name if attr == "aria-label" else None
        )
        card.inner_text = AsyncMock(return_value=full_text)
        if href:
            link = MagicMock()
            link.get_attribute = AsyncMock(return_value=href)
            card.query_selector = AsyncMock(return_value=link)
        else:
            card.query_selector = AsyncMock(return_value=None)
        return card

    @pytest.mark.asyncio
    async def test_full_places_data_extracted(self):
        """Realistic Maps card: name, rating, review count, hours,
        address, phone, service options, price range."""
        from app.services.scraper.maps import GoogleMapsScraper

        card = self._make_card(
            "Klinik Gigi Senyum, 4,5 bintang, 123 ulasan, Buka",
            (
                "Klinik Gigi Senyum\n"
                "4,5 ★ (123 ulasan)\n"
                "Klinik gigi · Buka ⋅ Tutup pukul 21.00\n"
                "Jl. Sudirman No. 45, Jakarta Pusat\n"
                "0812-3456-7890\n"
                "Makan di tempat · Bawa pulang\n"
                "$$"
            ),
            href="https://klinikgigi-senyum.example.com",
        )
        result = await GoogleMapsScraper._parse_card(card, page=None)
        assert result is not None
        assert result.company_name.startswith("Klinik Gigi Senyum")
        # The full Places data must be in extra → raw_data
        assert result.extra.get("rating") == 4.5
        assert result.extra.get("review_count") == 123
        assert result.extra.get("hours") is not None
        assert "Buka" in result.extra.get("hours", "")
        assert result.extra.get("price_range") == "$$"
        assert "Makan di tempat" in (result.extra.get("service_options") or [])
        # Address + website are also in extra
        assert result.extra.get("raw_address") is not None
        # Phone is in the structured field, not extra
        assert result.phone is not None

    @pytest.mark.asyncio
    async def test_review_count_handles_id_thousands_separator(self):
        """Indonesian number format: '10.000 ulasan' = 10000, NOT 10.

        This is the bug the code review caught: the original
        float('.', '.') replacement treated '.' as decimal,
        conflating ID thousands separator with decimal point.
        """
        from app.services.scraper.maps import _extract_review_count
        # ID thousands (the "10.000" trap)
        assert _extract_review_count("10.000 ulasan") == 10000
        assert _extract_review_count("1.234 ulasan") == 1234
        # English thousands
        assert _extract_review_count("1,500 reviews") is None  # we look for "ulasan"
        assert _extract_review_count("1.500 ulasan") == 1500
        # No separator
        assert _extract_review_count("500 ulasan") == 500
        # Decimal + rb suffix
        assert _extract_review_count("1,2 rb ulasan") == 1200
        assert _extract_review_count("1.2 ribu ulasan") == 1200
        assert _extract_review_count("2 k ulasan") == 2000
        # No match
        assert _extract_review_count("no review count here") is None
        # Edge: zero
        assert _extract_review_count("0 ulasan") == 0

    @pytest.mark.asyncio
    async def test_rating_is_float_and_bounded(self):
        """Rating is float (not str) and bounded to [1.0, 5.0].

        Code review caught: original regex accepted any digit
        (so "10 ★" was parsed as rating 10.0). Tightened to
        [1-5] with word boundary. Returns float for downstream
        filtering consistency.
        """
        from app.services.scraper.maps import _extract_rating
        # ID decimal
        assert _extract_rating("4,5 ★ (123 ulasan)") == 4.5
        # English decimal
        assert _extract_rating("4.5 ★ (123 ulasan)") == 4.5
        # Boundary values
        assert _extract_rating("1 ★ (10 ulasan)") == 1.0
        assert _extract_rating("5 ★ (10 ulasan)") == 5.0
        # No match
        assert _extract_rating("no rating here") is None
        # Out-of-range (Maps max is 5) — must NOT match
        assert _extract_rating("10 ★ (50 ulasan)") is None
        assert _extract_rating("0 ★ (10 ulasan)") is None

    @pytest.mark.asyncio
    async def test_hours_extraction(self):
        """Extract opening hours from various Maps patterns."""
        from app.services.scraper.maps import _extract_hours
        assert _extract_hours("Buka ⋅ Tutup pukul 21.00") is not None
        assert "21.00" in _extract_hours("Buka ⋅ Tutup pukul 21.00")
        assert _extract_hours("Buka 24 jam") is not None
        assert _extract_hours("Tutup permanen") is not None
        assert _extract_hours("no hours here") is None

    @pytest.mark.asyncio
    async def test_service_options_deduped(self):
        """Maps sometimes shows the same option twice; dedup."""
        from app.services.scraper.maps import _extract_service_options
        result = _extract_service_options(
            "Makan di tempat · Bawa pulang · Makan di tempat"
        )
        assert result is not None
        assert result.count("Makan di tempat") == 1
        assert "Bawa pulang" in result

    @pytest.mark.asyncio
    async def test_extra_drops_none_values(self):
        """The extra dict must not contain None values (tight raw_data)
        AND must have at least one known-good field (the test must
        not be vacuous)."""
        from app.services.scraper.maps import GoogleMapsScraper

        card = self._make_card(
            "Toko ABC",
            "Toko ABC\nJl. Merdeka No. 1",
            href=None,
        )
        result = await GoogleMapsScraper._parse_card(card, page=None)
        assert result is not None
        # The test is not vacuous only if the parser actually
        # extracted at least one field.
        assert len(result.extra) > 0, (
            "test_extra_drops_none_values is vacuous — the parser "
            "extracted nothing. Either the regex is too strict or "
            "the test text is missing real data."
        )
        for k, v in result.extra.items():
            assert v is not None, f"key {k} has None value"


class TestScoutRunFK:
    """scout_run_id FK is in place + persist accepts the kwarg."""

    def test_prospect_model_has_scout_run_id(self):
        from app.models.prospect import Prospect
        cols = {c.name for c in Prospect.__table__.columns}
        assert "scout_run_id" in cols, (
            "Prospect must have scout_run_id column (PR 2)"
        )

    def test_scout_run_id_is_fk_to_scraping_jobs(self):
        from app.models.prospect import Prospect
        scout_run_col = Prospect.__table__.columns["scout_run_id"]
        fks = list(scout_run_col.foreign_keys)
        assert len(fks) == 1, f"scout_run_id should have 1 FK, got {len(fks)}"
        assert fks[0].column.table.name == "scraping_jobs"

    def test_persist_scraped_to_prospects_accepts_scout_run_id(self):
        import inspect
        from app.services.scraper import persist_scraped_to_prospects
        sig = inspect.signature(persist_scraped_to_prospects)
        assert "scout_run_id" in sig.parameters
        # The kwarg must default to None (backward compat for legacy callers)
        assert sig.parameters["scout_run_id"].default is None

    def test_scraping_tasks_passes_scout_run_id(self):
        """scraping_tasks._run_job must call persist_scraped_to_prospects
        with scout_run_id=jid. This is the v1 contract: every new
        prospect is linked to the ScoutRun that found it.

        Source-inspection approach: scoped narrowly to avoid coupling
        to the call site. Asserts the kwarg NAME appears in the
        function body — refactoring the call into a helper or
        renaming the local variable would still pass.
        """
        import inspect
        from app.tasks import scraping_tasks
        src = inspect.getsource(scraping_tasks._run_job)
        assert "scout_run_id=" in src, (
            "scraping_tasks._run_job must call persist_scraped_to_prospects "
            "with scout_run_id=<value>. Per PR 2, every prospect is "
            "linked to its ScoutRun."
        )


class TestRawDataGINIndex:
    """The GIN index on raw_data enables future JSONB queries.

    Verified by the migration being applied (alembic upgrade head
    fails if the index creation fails). The test asserts the
    migration source declares the index — a stronger check would
    be a real DB query, but that couples the test to docker
    compose and the test DB harness. The migration is the
    source of truth for the schema; if it succeeds, the index
    exists.
    """

    def test_migration_declares_gin_index(self):
        import os
        from pathlib import Path
        # Use a glob via pathlib (robust to file moves within
        # the alembic/versions/ directory — the reviewer's
        # concern about hard-coded parents[N] is mitigated by
        # the glob).
        migration_files = list(
            Path(__file__).resolve().parents[4].glob(
                "alembic/versions/9b8f3c4e2a1d_*.py"
            )
        )
        assert len(migration_files) == 1, (
            f"Expected 1 migration matching 9b8f3c4e2a1d, found "
            f"{len(migration_files)}: {migration_files}"
        )
        content = migration_files[0].read_text()
        assert "ix_prospects_raw_data_gin" in content
        assert "USING gin (raw_data)" in content
        # IF NOT EXISTS is the post-review hardening (idempotent
        # re-runs). If the assertion below fails, the migration
        # would break on a re-deploy after a partial failure.
        assert "IF NOT EXISTS" in content
