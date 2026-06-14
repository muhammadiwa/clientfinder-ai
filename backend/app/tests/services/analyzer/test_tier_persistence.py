"""
Sprint 3B sub-task 3 — classify_and_persist unit tests.

Covers the auto-classify helper called from the orchestrator's
enrich step. Uses mock DB session + mock LLM to keep tests
fast and isolated from external services.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_prospect(id="p-1", name="Test Klinik", **kwargs):
    """Build a SimpleNamespace with the fields classify_and_persist
    reads from the prospect."""
    ns = SimpleNamespace(
        id=id,
        company_name=name,
        industry=kwargs.get("industry", "klinik"),
        location_city=kwargs.get("location_city", "Bandung"),
        description=kwargs.get("description", "klinik gigi 2 cabang"),
        owner_name=kwargs.get("owner_name", "Dr. Test"),
        employee_count=kwargs.get("employee_count", None),
        revenue_estimate=kwargs.get("revenue_estimate", None),
        tier=None,
        tier_confidence=None,
        industry_specific=kwargs.get("industry_specific", None),
    )
    return ns


def _make_db_session(tech=None):
    """Build a mock AsyncSession that returns the given TechStack
    (or None) on select(TechStack)."""
    session = MagicMock()
    # Make session.execute(...) return an object whose
    # .scalars().all() returns a list (for Signal/PainPoint counts)
    # and .scalar_one_or_none() returns tech (or None).
    exec_result = MagicMock()
    exec_result.scalars.return_value.all.return_value = []
    exec_result.scalar_one_or_none.return_value = tech
    session.execute = AsyncMock(return_value=exec_result)
    session.commit = AsyncMock()
    return session


class TestClassifyAndPersist:
    """classify_and_persist runs tier (heuristic) + industry (LLM)
    and persists both to the prospect row."""

    @pytest.mark.asyncio
    async def test_tier_persisted_even_when_industry_fails(self):
        """LLM fails → tier still set, industry stays None."""
        from app.services.analyzer.lead_classifier import (
            classify_and_persist,
        )
        p = _make_prospect()
        db = _make_db_session()

        with patch(
            "app.services.analyzer.lead_classifier.classify_industry_deep",
            AsyncMock(side_effect=Exception("LLM down")),
        ):
            result = await classify_and_persist(db, p)

        # Tier was set
        assert p.tier in ("smb", "mid", "enterprise", "unknown")
        assert p.tier_confidence is not None
        # Industry is None (LLM failed)
        assert p.industry_specific is None
        # Result dict has both keys
        assert "tier" in result
        assert "industry" in result
        # DB commit was called
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_industry_persisted_when_confident(self):
        from app.services.analyzer.lead_classifier import (
            classify_and_persist,
        )
        p = _make_prospect()
        db = _make_db_session()

        with patch(
            "app.services.analyzer.lead_classifier.classify_industry_deep",
            AsyncMock(return_value={
                "industry_specific": "klinik gigi",
                "industry_category": "klinik",
                "confidence": 90,
                "rationale": "explicit signal in name",
            }),
        ):
            await classify_and_persist(db, p)

        assert p.industry_specific == "klinik gigi"

    @pytest.mark.asyncio
    async def test_industry_not_persisted_when_low_confidence(self):
        from app.services.analyzer.lead_classifier import (
            classify_and_persist,
        )
        p = _make_prospect()
        db = _make_db_session()

        with patch(
            "app.services.analyzer.lead_classifier.classify_industry_deep",
            AsyncMock(return_value={
                "industry_specific": "maybe something",
                "industry_category": "umum",
                "confidence": 30,  # below 50 threshold
                "rationale": "guessing",
            }),
        ):
            await classify_and_persist(db, p)

        assert p.industry_specific is None

    @pytest.mark.asyncio
    async def test_industry_truncated_to_255_chars(self):
        from app.services.analyzer.lead_classifier import (
            classify_and_persist,
        )
        p = _make_prospect()
        db = _make_db_session()

        long_name = "x" * 500
        with patch(
            "app.services.analyzer.lead_classifier.classify_industry_deep",
            AsyncMock(return_value={
                "industry_specific": long_name,
                "industry_category": "umum",
                "confidence": 80,
                "rationale": "test",
            }),
        ):
            await classify_and_persist(db, p)

        assert len(p.industry_specific) <= 255

    @pytest.mark.asyncio
    async def test_unknown_industry_not_persisted(self):
        """If LLM returns 'unknown', don't overwrite existing industry_specific."""
        from app.services.analyzer.lead_classifier import (
            classify_and_persist,
        )
        p = _make_prospect(industry_specific="klinik gigi")
        db = _make_db_session()

        with patch(
            "app.services.analyzer.lead_classifier.classify_industry_deep",
            AsyncMock(return_value={
                "industry_specific": "unknown",
                "industry_category": "umum",
                "confidence": 80,
                "rationale": "test",
            }),
        ):
            await classify_and_persist(db, p)

        # The previous "klinik gigi" is preserved
        assert p.industry_specific == "klinik gigi"

    @pytest.mark.asyncio
    async def test_tier_uses_revenue_when_provided(self):
        """A prospect with revenue should classify into a tier."""
        from app.services.analyzer.lead_classifier import (
            classify_and_persist,
        )
        p = _make_prospect(revenue_estimate="Rp 600jt/bulan")
        db = _make_db_session()

        with patch(
            "app.services.analyzer.lead_classifier.classify_industry_deep",
            AsyncMock(return_value={
                "industry_specific": "unknown",
                "industry_category": "umum",
                "confidence": 0,
                "rationale": "",
            }),
        ):
            await classify_and_persist(db, p)

        # High revenue → enterprise
        assert p.tier == "enterprise"
        assert p.tier_confidence > 0.5

    @pytest.mark.asyncio
    async def test_tier_uses_employees_when_provided(self):
        from app.services.analyzer.lead_classifier import (
            classify_and_persist,
        )
        p = _make_prospect(employee_count=60)
        db = _make_db_session()

        with patch(
            "app.services.analyzer.lead_classifier.classify_industry_deep",
            AsyncMock(return_value={
                "industry_specific": "unknown",
                "industry_category": "umum",
                "confidence": 0,
                "rationale": "",
            }),
        ):
            await classify_and_persist(db, p)

        assert p.tier == "enterprise"


class TestMigrationColumns:
    """Verify the migration added the columns correctly by
    inspecting the live DB (which is what the test suite uses)."""

    @pytest.mark.asyncio
    async def test_columns_exist(self):
        from sqlalchemy import text
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'prospects'
                  AND column_name IN ('tier', 'tier_confidence', 'industry_specific')
            """))
            names = {row[0] for row in result}
        assert {"tier", "tier_confidence", "industry_specific"} <= names

    @pytest.mark.asyncio
    async def test_tier_index_exists(self):
        from sqlalchemy import text
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'prospects' AND indexname = 'ix_prospects_tier'
            """))
        assert result.first() is not None
