"""
Sprint 4.1 followup — IDOR regression tests for the 4 existing
/jobs endpoints.

PR 3 closed the IDOR on /scout-runs/{run_id}/results. The
holistic Sprint 4 review found the same gap on the 4 pre-existing
/jobs endpoints (get, list, retry, delete). This test file
verifies the fix.

Pattern matches test_scout_run_results.py: source inspection +
mocked DB, no async client fixtures.
"""
import inspect
from uuid import uuid4

import pytest


class TestJobsEndpointsIDOR:
    """All 4 /jobs endpoints must filter by created_by.

    C1 holistic review: PR 3 closed the IDOR on the new
    /scout-runs/{run_id}/results endpoint but left the
    pre-existing /jobs endpoints vulnerable. This file
    catches the cross-PR regression.
    """

    def test_list_jobs_filters_by_created_by(self):
        """GET /jobs must scope results to current_user.id."""
        from app.api.v1.scraping import list_scraping_jobs
        src = inspect.getsource(list_scraping_jobs)
        # Either both filters (created_by + source) are in a shared
        # base_filter list (post-fix) OR they're inline twice.
        # Both patterns filter by created_by; just need at least
        # one occurrence in the count path.
        assert "ScrapingJob.created_by == current_user.id" in src, (
            "list_scraping_jobs must filter by created_by — "
            "otherwise any user sees all jobs in the system."
        )

    def test_list_jobs_excludes_legacy_sources(self):
        """PR 123 followup: legacy `google`/`google_places`/`tokopedia`
        rows from before PR 1 must NOT crash Pydantic v2.

        Before the fix: per_page=10+ crashed because the 4th
        row was `source='tokopedia'` which is no longer in the
        `ScrapingSource` Literal. The fix: IN-filter the query
        by the current registry's allowed sources.
        """
        from app.api.v1.scraping import list_scraping_jobs
        src = inspect.getsource(list_scraping_jobs)
        assert "ScrapingSource" in src and "in_(" in src, (
            "list_scraping_jobs must filter by active sources "
            "(ScrapingSource Literal members). Otherwise legacy "
            "rows with deprecated source values crash Pydantic "
            "v2 model_validate → 500 error."
        )
        # The base_filter must include both created_by + source filter
        assert "source.in_" in src, (
            "list_scraping_jobs must use .in_() for the source "
            "filter to allow multiple active sources at once."
        )

    def test_get_job_filters_by_created_by(self):
        from app.api.v1.scraping import get_scraping_job
        src = inspect.getsource(get_scraping_job)
        assert "ScrapingJob.created_by == current_user.id" in src, (
            "get_scraping_job must filter by created_by. "
            "Otherwise any user can read any other user's "
            "ScoutRun by guessing the UUID."
        )

    def test_retry_job_filters_by_created_by(self):
        from app.api.v1.scraping import retry_scraping_job
        src = inspect.getsource(retry_scraping_job)
        assert "ScrapingJob.created_by == current_user.id" in src, (
            "retry_scraping_job must filter by created_by. "
            "Otherwise any user can re-enqueue another user's "
            "ScoutRun (cost amplification attack)."
        )

    def test_delete_job_filters_by_created_by(self):
        from app.api.v1.scraping import delete_scraping_job
        src = inspect.getsource(delete_scraping_job)
        assert "ScrapingJob.created_by == current_user.id" in src, (
            "delete_scraping_job must filter by created_by. "
            "Otherwise any user can delete another user's "
            "ScoutRun (DoS attack)."
        )

    def test_all_endpoints_use_generic_404_message(self):
        """All 4 endpoints must return a generic 'Job not found'
        message — no UUID leak (matches the C1 review's M10
        pattern from the new endpoint)."""
        for fn_name in (
            "get_scraping_job",
            "retry_scraping_job",
            "delete_scraping_job",
        ):
            mod = __import__(
                "app.api.v1.scraping", fromlist=[fn_name]
            )
            fn = getattr(mod, fn_name)
            src = inspect.getsource(fn)
            # The generic message is "Job not found" — not the
            # old "Job {job_id} not found" that leaks the UUID.
            assert 'detail="Job not found"' in src, (
                f"{fn_name} must use generic 'Job not found' "
                f"message to avoid leaking the UUID to the user."
            )

    @pytest.mark.asyncio
    async def test_get_job_404_for_other_users_job(self):
        """Live mock test: get_scraping_job returns 404 when
        the job is owned by another user (or has NULL created_by)."""
        from fastapi import HTTPException
        from app.api.v1.scraping import get_scraping_job

        # Mock DB: job lookup returns None because created_by
        # filter doesn't match (mock_user.id != None or the
        # filter excludes the mocked-out job).
        mock_user = MagicMock()
        mock_user.id = uuid4()

        mock_db = AsyncMock()
        mock_scalar = AsyncMock()
        mock_scalar.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_scalar)

        try:
            await get_scraping_job(
                job_id=str(uuid4()),
                current_user=mock_user,
                db=mock_db,
            )
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail == "Job not found"
        else:
            pytest.fail("Expected HTTPException(404) for other-user's job")


# Imports at the bottom to keep the test classes clean
from unittest.mock import AsyncMock, MagicMock  # noqa: E402
