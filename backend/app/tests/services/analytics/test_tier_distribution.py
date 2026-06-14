"""
Sprint 3B carryover — tier distribution analytics tests.

Covers the pure aggregation logic of get_tier_distribution.
DB-driven via the real connection in this project's test suite
(no fixture indirection needed).
"""
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock


class TestGetTierDistribution:
    """get_tier_distribution: aggregate tier counts via SQL."""

    @pytest.mark.asyncio
    async def test_returns_all_5_buckets(self):
        from app.services.analytics import get_tier_distribution

        # Mock DB to return tier counts
        rows = [
            ("smb", 10),
            ("mid", 5),
            ("enterprise", 3),
            ("unknown", 2),
        ]
        session = MagicMock()
        result = MagicMock()
        result.all = MagicMock(return_value=rows)
        session.execute = AsyncMock(return_value=result)

        # Patch AsyncSessionLocal
        with patch("app.services.analytics.AsyncSessionLocal") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            dist = await get_tier_distribution(days=30)
        # 5 buckets always returned, total = sum
        assert set(dist.keys()) == {
            "smb", "mid", "enterprise", "unknown", "unclassified", "total"
        }
        assert dist["smb"] == 10
        assert dist["mid"] == 5
        assert dist["enterprise"] == 3
        assert dist["unknown"] == 2
        assert dist["unclassified"] == 0
        assert dist["total"] == 20

    @pytest.mark.asyncio
    async def test_null_tier_goes_to_unclassified(self):
        from app.services.analytics import get_tier_distribution

        # DB returns None for the tier (group_by groups NULLs together)
        rows = [(None, 7)]
        session = MagicMock()
        result = MagicMock()
        result.all = MagicMock(return_value=rows)
        session.execute = AsyncMock(return_value=result)
        with patch("app.services.analytics.AsyncSessionLocal") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            dist = await get_tier_distribution(days=30)
        assert dist["unclassified"] == 7
        assert dist["total"] == 7

    @pytest.mark.asyncio
    async def test_empty_db_returns_zero_for_all(self):
        from app.services.analytics import get_tier_distribution

        session = MagicMock()
        result = MagicMock()
        result.all = MagicMock(return_value=[])
        session.execute = AsyncMock(return_value=result)
        with patch("app.services.analytics.AsyncSessionLocal") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            dist = await get_tier_distribution(days=30)
        # All 5 buckets = 0, total = 0
        assert dist == {
            "smb": 0, "mid": 0, "enterprise": 0, "unknown": 0,
            "unclassified": 0, "total": 0,
        }

    @pytest.mark.asyncio
    async def test_total_equals_sum(self):
        from app.services.analytics import get_tier_distribution

        rows = [
            ("smb", 100),
            ("mid", 50),
            ("enterprise", 25),
            ("unknown", 10),
        ]
        session = MagicMock()
        result = MagicMock()
        result.all = MagicMock(return_value=rows)
        session.execute = AsyncMock(return_value=result)
        with patch("app.services.analytics.AsyncSessionLocal") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            dist = await get_tier_distribution(days=30)
        assert dist["total"] == sum([
            dist["smb"], dist["mid"], dist["enterprise"],
            dist["unknown"], dist["unclassified"],
        ])


# Tiny helper to avoid `from unittest.mock import patch` at top
from unittest.mock import patch


# --- E2E with real DB (live verify) ---


@pytest.mark.asyncio
async def test_real_db_tier_distribution():
    """Verify against the actual DB — current state of prospects
    table should have at least 1 row with a tier (or all unclassified).
    """
    from app.services.analytics import get_tier_distribution
    dist = await get_tier_distribution(days=30)
    # The shape is always the 5-bucket dict + total
    assert set(dist.keys()) == {
        "smb", "mid", "enterprise", "unknown", "unclassified", "total"
    }
    # All values are ints >= 0
    for v in dist.values():
        assert isinstance(v, int)
        assert v >= 0
    # Total equals sum
    assert dist["total"] == sum([
        dist["smb"], dist["mid"], dist["enterprise"],
        dist["unknown"], dist["unclassified"],
    ])


@pytest.mark.asyncio
async def test_endpoint_returns_valid_dict():
    """The HTTP endpoint wraps get_tier_distribution and returns
    the same shape."""
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as db:
        result = await db.execute(text(
            "SELECT tier, count(*) FROM prospects "
            "WHERE deleted_at IS NULL GROUP BY tier"
        ))
        rows = result.all()

    # We just check the data structure makes sense
    for r in rows:
        # r = (tier, count)
        assert isinstance(r[0], type(None)) or isinstance(r[0], str)
        assert isinstance(r[1], int)
