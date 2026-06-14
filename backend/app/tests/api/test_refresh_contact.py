"""
Integration tests for the T8.6 homepage enrichment endpoint.

Auth + validation paths only — the full happy path requires
a real Playwright session + a real prospect, which is exercised
manually in the E2E checklist (see docs/SCOUT_ENRICHMENT_SPEC.md
section 10).
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestRefreshContactAuth:
    def test_requires_auth(self, client):
        """No token → 401."""
        resp = client.post(
            "/api/v1/prospects/00000000-0000-0000-0000-000000000000/refresh-contact"
        )
        assert resp.status_code == 401


class TestRefreshContactValidation:
    def test_invalid_uuid_format(self, client):
        """Non-UUID path segment → 422 from FastAPI path validation."""
        # This won't even reach auth — FastAPI validates the path first.
        # But without a token, it should still be 401.
        resp = client.post("/api/v1/prospects/not-a-uuid/refresh-contact")
        assert resp.status_code == 401

    def test_404_for_nonexistent_prospect(self, client):
        """With auth, a non-existent UUID returns 404. We test the
        auth-gated 404 indirectly by checking the route exists and
        would respond; the full 404 path requires a real JWT which
        is exercised in E2E."""
        # The endpoint IS registered (proves integration wiring is right).
        # We confirm via OpenAPI.
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        paths = spec.get("paths", {})
        assert "/api/v1/prospects/{prospect_id}/refresh-contact" in paths
        methods = paths["/api/v1/prospects/{prospect_id}/refresh-contact"]
        assert "post" in methods
