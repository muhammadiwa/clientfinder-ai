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
        """per_page > 100 is rejected at the FastAPI layer (422).

        Source inspection: verify the bounds exist in the
        function source code. The Query() call must include
        le=100 + ge=1 for per_page and ge=1 for page.
        """
        import inspect
        from app.api.v1.scraping import get_scout_run_results
        src = inspect.getsource(get_scout_run_results)
        # per_page must bound 1..100
        assert "per_page: int = Query(25, ge=1, le=100)" in src, (
            "per_page must be bounded [1, 100] via Query(le=100) "
            "to prevent unbounded result-set sizes"
        )
        # page must be >= 1
        assert "page: int = Query(1, ge=1)" in src, (
            "page must be bounded >=1 via Query(ge=1) "
            "to prevent negative offsets"
        )

    @pytest.mark.asyncio
    async def test_invalid_uuid_raises_400(self):
        """A non-UUID run_id returns 400."""
        from fastapi import HTTPException
        from app.api.v1.scraping import get_scout_run_results

        # The function takes current_user + db as direct args;
        # the patch below is intentionally a no-op (the type
        # CurrentUser is a class hint, not a DI target). The
        # test passes because we call the function directly.
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
        """A valid UUID but unknown run_id returns 404.

        C1 review: the query must filter by created_by. We
        mock current_user.id so the filter fails (run.created_by
        is None on the mock → filter excludes it).
        """
        from fastapi import HTTPException
        from app.api.v1.scraping import get_scout_run_results

        # Mock current_user with an id
        mock_user = MagicMock()
        mock_user.id = uuid4()

        # Mock DB: the run lookup with created_by filter returns None
        # (because mock_job has no created_by attribute set, or the
        # filter simply doesn't match the mock's auto-spec'd values).
        mock_db = AsyncMock()
        mock_scalar = AsyncMock()
        mock_scalar.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_scalar)

        try:
            await get_scout_run_results(
                run_id=str(uuid4()),
                current_user=mock_user,
                db=mock_db,
            )
        except HTTPException as e:
            assert e.status_code == 404
            # M10: generic message — UUID should not leak
            assert "not found" in e.detail
            assert "ScoutRun" in e.detail
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
        # C1 review: must filter by created_by (prevent IDOR)
        assert "created_by" in src, (
            "get_scout_run_results must filter by created_by to "
            "prevent cross-tenant data leak. The fix is in the "
            "PR 3 review patch."
        )
        # I3 review: must have a stable secondary sort key
        assert "Prospect.id" in src or "Prospect_id" in src, (
            "Pagination ordering must include a stable secondary "
            "key (Prospect.id) to avoid skipping/duplicating rows "
            "when created_at ties on batch inserts."
        )
        # I6 review: must filter out soft-deleted prospects
        assert "deleted_at" in src, (
            "Results query must filter Prospect.deleted_at.is_(None) "
            "to match the rest of the prospect API. Otherwise "
            "soft-deleted rows appear in the table and 404 on click."
        )


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
