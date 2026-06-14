"""
Sprint 3A sub-task 3 — analytics + daily cap unit tests.

Covers the pure-function parts of the analytics module
(bucketing, rate calculation) via the public API. The DB
queries are tested in test_analytics_db.py (integration).
"""
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services.outreach.analytics import compute_sequence_stats
from app.services.outreach.analytics import (
    count_sent_today_for_sequence,
)


# --- Pure-function tests via mock DB ---


class _MockScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._rows[0] if self._rows else None


class _TwoQueryDB:
    """Mock DB: first call returns the sequence, second returns messages."""

    def __init__(self, seq, rows):
        self._seq = seq
        self._rows = rows
        self._call_count = 0

    async def execute(self, _stmt):
        self._call_count += 1
        if self._call_count == 1:
            return _MockScalarResult([self._seq])
        return _MockScalarResult(self._rows)


def _build_message_row(
    step_index="0",
    channel="email",
    status="sent",
    sent_at=None,
    delivered_at=None,
    opened_at=None,
    clicked_at=None,
    replied_at=None,
    sequence_id="00000000-0000-0000-0000-000000000000",
):
    """Build a mock row that matches what the analytics SQL returns.

    Note: extra_metadata isn't a field on the row object — the
    analytics module pulls it from extra_metadata[key].astext.
    For these pure-function tests we bypass the SQL and feed
    pre-bucketed SimpleNamespace rows directly. The actual
    bucketing logic is the part being tested.
    """
    return SimpleNamespace(
        step_index=step_index,
        channel=channel,
        status=status,
        sent_at=sent_at,
        delivered_at=delivered_at,
        opened_at=opened_at,
        clicked_at=clicked_at,
        replied_at=replied_at,
        sequence_id=sequence_id,
    )


class TestBucketingLogic:
    """Test the bucketing logic by exercising the public function
    with a stub DB that returns pre-built rows."""

    @pytest.mark.asyncio
    async def test_empty_sequence(self):
        # Sequence with 3 steps but no messages
        seq = SimpleNamespace(
            id="00000000-0000-0000-0000-000000000000",
            name="Test",
            steps=[{}, {}, {}],
            daily_send_cap=50,
        )
        db = _TwoQueryDB(seq, [])
        stats = await compute_sequence_stats(db, seq.id)
        assert stats["totals"]["sent"] == 0
        assert len(stats["by_step"]) == 3
        for s in stats["by_step"]:
            assert s["sent"] == 0
            assert s["response_rate"] == 0.0
            assert s["open_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_bucketing_by_step_and_channel(self):
        now = datetime(2026, 6, 14, 10, 0, 0)
        seq = SimpleNamespace(
            id="seq-1", name="Test",
            steps=[{}, {}, {}], daily_send_cap=50,
        )
        rows = [
            # step 0, email, sent
            _build_message_row("0", "email", "sent", sent_at=now),
            _build_message_row("0", "email", "sent", sent_at=now, opened_at=now),
            # step 1, whatsapp, sent + replied
            _build_message_row("1", "whatsapp", "sent", sent_at=now, replied_at=now),
            # step 1, email, bounced
            _build_message_row("1", "email", "bounced", sent_at=now),
            # step 2, email, failed (no sent_at)
            _build_message_row("2", "email", "failed", sent_at=None),
        ]
        db = _TwoQueryDB(seq, rows)
        stats = await compute_sequence_stats(db, seq.id)
        # Totals
        assert stats["totals"]["sent"] == 4   # 2 step-0 + 1 step-1-WhatsApp + 1 step-1-email-bounced
        assert stats["totals"]["opened"] == 1
        assert stats["totals"]["replied"] == 1
        assert stats["totals"]["bounced"] == 1
        assert stats["totals"]["failed"] == 1
        # Per-step
        assert stats["by_step"][0]["sent"] == 2
        assert stats["by_step"][0]["opened"] == 1
        assert stats["by_step"][0]["response_rate"] == 0.0
        assert stats["by_step"][0]["open_rate"] == 0.5
        assert stats["by_step"][1]["sent"] == 2
        assert stats["by_step"][1]["replied"] == 1
        assert stats["by_step"][1]["response_rate"] == 0.5
        assert stats["by_step"][2]["sent"] == 0
        # Per-channel
        assert stats["by_channel"]["email"]["sent"] == 3
        assert stats["by_channel"]["whatsapp"]["sent"] == 1
        assert stats["by_channel"]["whatsapp"]["replied"] == 1

    @pytest.mark.asyncio
    async def test_response_rate_zero_when_no_sends(self):
        seq = SimpleNamespace(
            id="seq-1", name="T", steps=[{}], daily_send_cap=10,
        )
        db = _TwoQueryDB(seq, [])
        stats = await compute_sequence_stats(db, seq.id)
        assert stats["by_step"][0]["response_rate"] == 0.0
        assert stats["by_step"][0]["open_rate"] == 0.0
        # No division-by-zero
        assert "ZeroDivisionError" not in repr(stats)

    @pytest.mark.asyncio
    async def test_missing_sequence_returns_error(self):
        class _DB:
            async def execute(self, _stmt):
                return _MockScalarResult([])
        stats = await compute_sequence_stats(_DB(), "nonexistent-uuid")
        assert "error" in stats

    @pytest.mark.asyncio
    async def test_today_sent_only_counts_today(self):
        """The cap is per-day UTC. Yesterday's sends don't count."""
        today = datetime(2026, 6, 14, 10, 0, 0)
        yesterday = datetime(2026, 6, 13, 10, 0, 0)
        seq = SimpleNamespace(
            id="seq-1", name="T", steps=[{}, {}], daily_send_cap=10,
        )
        rows = [
            _build_message_row("0", "email", "sent", sent_at=today),
            _build_message_row("0", "email", "sent", sent_at=today),
            _build_message_row("1", "email", "sent", sent_at=yesterday),
        ]
        from unittest.mock import patch as _patch
        with _patch("app.services.outreach.analytics.datetime") as mock_dt:
            mock_dt.utcnow.return_value.date.return_value = today.date()
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            db = _TwoQueryDB(seq, rows)
            stats = await compute_sequence_stats(db, seq.id)
        assert stats["today_sent"] == 2


class TestCountSentToday:
    """count_sent_today_for_sequence is called frequently by
    the drip_runner — verify it returns an int."""

    @pytest.mark.asyncio
    async def test_returns_int(self):
        class _DB:
            async def execute(self, _stmt):
                return _MockScalarResult([42])
        result = await count_sent_today_for_sequence(_DB(), "any-uuid")
        assert result == 42
        assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_messages(self):
        class _DB:
            async def execute(self, _stmt):
                return _MockScalarResult([0])
        result = await count_sent_today_for_sequence(_DB(), "any-uuid")
        assert result == 0

    @pytest.mark.asyncio
    async def test_returns_zero_when_scalar_none(self):
        class _DB:
            async def execute(self, _stmt):
                return _MockScalarResult([None])
        result = await count_sent_today_for_sequence(_DB(), "any-uuid")
        assert result == 0
