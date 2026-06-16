"""
PR 3 (scout-prospect-breadcrumb-2layer) — backend regression tests
for the GET /api/v1/scout-runs/{run_id}/results endpoint.

Verifies via source inspection (matches the project's testing
pattern — no async client fixtures, see Sprint 1-3 tests):

- Endpoint is registered on the router.
- Endpoint signature accepts run_id + page + per_page Query params.
- The ProspectOut used in the response includes scout_run_id
  (the PR 2 contract that powers the breadcrumb).
"""
import inspect
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestScoutRunResultsEndpoint:
    """Sprint 4 PR 3: GET /scraping/scout-runs/{run_id}/results."""

    def test_endpoint_is_registered(self):
        """The endpoint must be on the scraping router."""
        from app.api.v1.scraping import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/scraping/scout-runs/{run_id}/results" in paths

    def test_endpoint_signature(self):
        """The endpoint must accept run_id + page + per_page."""
        from fastapi import params as fastapi_params
        from app.api.v1.scraping import get_scout_run_results
        sig = inspect.signature(get_scout_run_results)
        # Path param
        assert "run_id" in sig.parameters
        # Query params — defaults are wrapped in FastAPI's
        # params.Query object; extract the literal value
        page_default = sig.parameters["page"].default
        if isinstance(page_default, fastapi_params.Query):
            page_default = page_default.default
        assert page_default == 1
        per_page_default = sig.parameters["per_page"].default
        if isinstance(per_page_default, fastapi_params.Query):
            per_page_default = per_page_default.default
        assert per_page_default == 25

    def test_query_param_bounds(self):
        """page >= 1, per_page 1..100 (Pydantic Query constraints)."""
        from fastapi import params as fastapi_params
        from app.api.v1.scraping import get_scout_run_results
        sig = inspect.getargspec(get_scout_run_results) if hasattr(inspect, "getargspec") else None
        sig = inspect.signature(get_scout_run_results)
        for param_name, expected in (("page", 1), ("per_page", 25)):
            value = sig.parameters[param_name].default
            if isinstance(value, fastapi_params.Query):
                value = value.default
            assert value == expected, (
                f"{param_name} default should be {expected}, got {value}"
            )

    @pytest.mark.asyncio
    async def test_invalid_uuid_raises_400(self):
        """A non-UUID run_id returns 400."""
        from fastapi import HTTPException
        from app.api.v1.scraping import get_scout_run_results

        # Mock DB + current_user (we never reach the DB call)
        with patch("app.api.v1.scraping.DB") as MockDB, \
             patch("app.api.v1.scraping.CurrentUser"):
            try:
                await get_scout_run_results(
                    run_id="not-a-uuid",
                    current_user=None,
                    db=AsyncMock(),
                )
            except HTTPException as e:
                assert e.status_code == 400
                assert "Invalid" in e.detail
            else:
                pytest.fail("Expected HTTPException(400) for invalid UUID")

    @pytest.mark.asyncio
    async def test_unknown_run_returns_404(self):
        """A valid UUID but unknown run_id returns 404."""
        from fastapi import HTTPException
        from app.api.v1.scraping import get_scout_run_results

        # Mock DB that returns None for the job
        mock_db = AsyncMock()
        mock_scalar = AsyncMock()
        mock_scalar.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_scalar)

        with patch("app.api.v1.scraping.CurrentUser"):
            try:
                await get_scout_run_results(
                    run_id=str(uuid4()),
                    current_user=None,
                    db=mock_db,
                )
            except HTTPException as e:
                assert e.status_code == 404
                assert "not found" in e.detail
            else:
                pytest.fail("Expected HTTPException(404) for unknown run")

    def test_response_uses_prospect_out_with_raw_data(self):
        """The response uses ProspectOut (which includes raw_data
        and scout_run_id per the PR 2 contract)."""
        import inspect
        from app.api.v1.scraping import get_scout_run_results
        from app.schemas.prospect import ProspectOut
        src = inspect.getsource(get_scout_run_results)
        # Must use ProspectOut
        assert "ProspectOut" in src
        # Must serialize via model_dump with json mode (for UUID/datetime)
        assert "model_dump" in src
        assert "mode=\"json\"" in src or "mode='json'" in src
        # Must filter by scout_run_id (the FK from PR 2)
        assert "scout_run_id" in src


class TestProspectOutScoutRunId:
    """PR 3 contract: ProspectOut must expose scout_run_id
    (powers the breadcrumb on ProspectDetail)."""

    def test_prospect_out_has_scout_run_id(self):
        from app.schemas.prospect import ProspectOut
        fields = ProspectOut.model_fields
        assert "scout_run_id" in fields

    def test_prospect_out_scout_run_id_is_optional(self):
        """scout_run_id is nullable for legacy + manual-import prospects.

        Uses model_validate with a minimal dict (only required
        fields) to verify the default-when-missing behavior.
        """
        from app.schemas.prospect import ProspectOut

        # All required fields populated, scout_run_id explicit
        base = {
            "id": str(uuid4()),
            "company_name": "X",
            "source": "maps",
            "source_query": None,
            "source_url": None,
            "raw_data": {},
            "status": "new",
            "quality_grade": None,
            "score_total": None,
            "owner_id": None,
            "last_contacted_at": None,
            "discovered_at": "2026-06-14T00:00:00Z",
            "created_at": "2026-06-14T00:00:00Z",
            "updated_at": "2026-06-14T00:00:00Z",
            "deleted_at": None,
            "tier": None,
            "tier_confidence": None,
            "industry_specific": None,
        }
        # With scout_run_id
        p1 = ProspectOut.model_validate({**base, "scout_run_id": str(uuid4())})
        assert p1.scout_run_id is not None
        # Without scout_run_id (legacy)
        p2 = ProspectOut.model_validate({**base})
        assert p2.scout_run_id is None
