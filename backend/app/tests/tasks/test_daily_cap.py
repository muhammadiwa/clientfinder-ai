"""
Sprint 3A sub-task 3 — drip runner daily cap test.

Verifies that when the sequence's daily_send_cap is reached,
the runner returns 'daily_cap_reached' and bumps the
enrollment's next_action_at to tomorrow.
"""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_daily_cap_skips_enrollment():
    """When sent_today >= cap, _process_one_enrollment should
    bump next_action_at to tomorrow and return daily_cap_reached."""
    from app.tasks.drip_runner import _process_one_enrollment

    # Build mock enrollment + sequence
    seq = MagicMock()
    seq.id = "seq-1"
    seq.is_active = True
    seq.steps = [
        {"order": 0, "channel": "auto", "category": "first_touch", "day_offset": 0},
    ]
    seq.daily_send_cap = 50

    enrollment = MagicMock()
    enrollment.id = "enr-1"
    enrollment.sequence_id = "seq-1"
    enrollment.prospect_id = "p-1"
    enrollment.current_step = 0
    enrollment.next_action_at = datetime(2026, 6, 14, 10, 0, tzinfo=timezone.utc)

    class _MockDB:
        async def execute(self, stmt):
            # The first call is the Sequence lookup
            return MagicMock(scalar_one_or_none=MagicMock(return_value=seq))

    # Patch count_sent_today_for_sequence to return cap (50) — cap hit
    with patch(
        "app.services.outreach.analytics.count_sent_today_for_sequence",
        AsyncMock(return_value=50),
    ):
        result = await _process_one_enrollment(_MockDB(), enrollment)

    # Result should signal cap-reached
    assert result["ok"] is False
    assert result["reason"] == "daily_cap_reached"
    assert result["sent_today"] == 50
    assert result["cap"] == 50
    # next_action_at should be bumped to tomorrow (after the bump)
    assert enrollment.next_action_at is not None
    bumped = enrollment.next_action_at
    now = datetime.now(timezone.utc)
    # Bumped time is tomorrow midnight, must be in the future
    assert bumped > now


@pytest.mark.asyncio
async def test_daily_cap_below_threshold_proceeds():
    """When sent_today < cap, the cap check should not interfere
    (the rest of the function may still fail for other reasons
    like missing prospect — but the cap itself shouldn't be the
    blocker)."""
    from app.tasks.drip_runner import _process_one_enrollment

    seq = MagicMock()
    seq.id = "seq-1"
    seq.is_active = True
    seq.steps = [
        {"order": 0, "channel": "auto", "category": "first_touch", "day_offset": 0},
    ]
    seq.daily_send_cap = 50

    enrollment = MagicMock()
    enrollment.id = "enr-1"
    enrollment.sequence_id = "seq-1"
    enrollment.prospect_id = "p-1"
    enrollment.current_step = 0
    enrollment.next_action_at = datetime(2026, 6, 14, 10, 0, tzinfo=timezone.utc)

    class _MockDB:
        async def execute(self, stmt):
            # First call: sequence lookup → returns seq
            # Second call: prospect lookup → returns None (forces 'prospect_missing')
            call_count = getattr(self, "_calls", 0) + 1
            self._calls = call_count
            if call_count == 1:
                return MagicMock(scalar_one_or_none=MagicMock(return_value=seq))
            return MagicMock(scalar_one_or_none=MagicMock(return_value=None))

    with patch(
        "app.services.outreach.analytics.count_sent_today_for_sequence",
        AsyncMock(return_value=10),  # below cap
    ):
        result = await _process_one_enrollment(_MockDB(), enrollment)

    # Cap not the blocker — the function should have proceeded and
    # then failed at 'prospect_missing'
    assert result.get("reason") != "daily_cap_reached"
    assert result.get("reason") == "prospect_missing"
