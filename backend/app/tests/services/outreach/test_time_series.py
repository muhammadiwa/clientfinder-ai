"""
Sprint 3A carryover — sequence time series tests.

Covers the day-bucketing + zero-fill logic via mock DB.
"""
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestComputeSequenceTimeSeries:
    """The function takes `db` as its first arg, so the tests pass
    a mock session directly — no AsyncSessionLocal patching needed."""

    @pytest.mark.asyncio
    async def test_empty_db_returns_zero_filled_days(self):
        from app.services.outreach.analytics import (
            compute_sequence_time_series,
        )
        session = MagicMock()
        result = MagicMock()
        result.all = MagicMock(return_value=[])
        session.execute = AsyncMock(return_value=result)
        rows = await compute_sequence_time_series(
            session, "any-uuid", days=7,
        )
        assert len(rows) == 7
        for r in rows:
            assert r["sent"] == 0
            assert r["delivered"] == 0
            assert r["opened"] == 0
            assert r["clicked"] == 0
            assert r["replied"] == 0
        dates = [r["date"] for r in rows]
        assert dates == sorted(dates)

    @pytest.mark.asyncio
    async def test_bucketing_by_date(self):
        from app.services.outreach.analytics import (
            compute_sequence_time_series,
        )
        d1 = date(2026, 6, 10)
        d2 = date(2026, 6, 12)
        rows_data = [
            SimpleNamespace(
                day=d1, sent=3, delivered=3, opened=2, clicked=1, replied=1,
            ),
            SimpleNamespace(
                day=d2, sent=2, delivered=2, opened=0, clicked=0, replied=0,
            ),
        ]
        session = MagicMock()
        result = MagicMock()
        result.all = MagicMock(return_value=rows_data)
        session.execute = AsyncMock(return_value=result)
        with patch("app.services.outreach.analytics.datetime") as mock_dt:
            mock_dt.utcnow.return_value.date.return_value = d2
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            from datetime import timedelta
            mock_dt.timedelta = timedelta
        rows = await compute_sequence_time_series(
            session, "any-uuid", days=7,
        )
        assert len(rows) == 7
        by_date = {r["date"]: r for r in rows}
        # d1=06-10 is included in days=7 starting from d2=06-12
        assert by_date["2026-06-10"]["sent"] == 3
        assert by_date["2026-06-10"]["opened"] == 2
        assert by_date["2026-06-10"]["clicked"] == 1
        assert by_date["2026-06-10"]["replied"] == 1
        assert by_date["2026-06-12"]["sent"] == 2
        assert by_date["2026-06-12"]["opened"] == 0
        # Missing days zero-filled (e.g. 06-11)
        assert by_date["2026-06-11"]["sent"] == 0

    @pytest.mark.asyncio
    async def test_window_size(self):
        from app.services.outreach.analytics import (
            compute_sequence_time_series,
        )
        session = MagicMock()
        result = MagicMock()
        result.all = MagicMock(return_value=[])
        session.execute = AsyncMock(return_value=result)
        rows_14 = await compute_sequence_time_series(
            session, "any-uuid", days=14,
        )
        rows_30 = await compute_sequence_time_series(
            session, "any-uuid", days=30,
        )
        assert len(rows_14) == 14
        assert len(rows_30) == 30

    @pytest.mark.asyncio
    async def test_int_coercion_from_none(self):
        from app.services.outreach.analytics import (
            compute_sequence_time_series,
        )
        d1 = date(2026, 6, 14)
        rows_data = [
            SimpleNamespace(
                day=d1, sent=None, delivered=None,
                opened=None, clicked=None, replied=None,
            ),
        ]
        session = MagicMock()
        result = MagicMock()
        result.all = MagicMock(return_value=rows_data)
        session.execute = AsyncMock(return_value=result)
        with patch("app.services.outreach.analytics.datetime") as mock_dt:
            mock_dt.utcnow.return_value.date.return_value = d1
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            from datetime import timedelta
            mock_dt.timedelta = timedelta
            rows = await compute_sequence_time_series(
                session, "any-uuid", days=1,
            )
        assert rows[0]["sent"] == 0
        assert rows[0]["delivered"] == 0


# --- E2E live DB ---


@pytest.mark.asyncio
async def test_real_db_time_series_shape():
    """Verify the live DB returns a valid time series shape."""
    from app.core.database import AsyncSessionLocal
    from app.services.outreach.analytics import compute_sequence_time_series
    from app.models.outreach import Sequence

    async with AsyncSessionLocal() as db:
        # Pick any sequence (or None if no sequences)
        from sqlalchemy import select
        seq = (
            await db.execute(select(Sequence).limit(1))
        ).scalar_one_or_none()
        if not seq:
            return  # no sequences in DB; nothing to test
        rows = await compute_sequence_time_series(db, seq.id, days=14)
    # Always 14 entries
    assert len(rows) == 14
    for r in rows:
        assert set(r.keys()) >= {"date", "sent", "delivered", "opened", "clicked", "replied"}
        for k in ("sent", "delivered", "opened", "clicked", "replied"):
            assert isinstance(r[k], int)
            assert r[k] >= 0
