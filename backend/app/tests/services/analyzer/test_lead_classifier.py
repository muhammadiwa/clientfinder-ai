"""
Sprint 3B — Lead classification unit tests.

Covers:
- parse_revenue_idr: free-text parsing
- classify_tier: heuristic classification
- tier_score: scoring function
- industry_specificity_score: scoring function
- compute_score: kwargs bug regression test (3rd carryover)
"""
import math
from datetime import datetime, timezone

import pytest

from app.services.analyzer.lead_classifier import (
    TIER_ENTERPRISE,
    TIER_MID,
    TIER_SMB,
    TIER_UNKNOWN,
    classify_tier,
    parse_revenue_idr,
)
from app.services.analyzer.scorer import (
    compute_score,
    industry_specificity_score,
    risk_penalty_score,
    tier_score,
)


# --- parse_revenue_idr ---

class TestParseRevenue:
    @pytest.mark.parametrize("raw,expected", [
        ("Rp 50jt/bulan", 50_000_000),
        ("Rp 50 jt", 50_000_000),
        ("Rp 100jt", 100_000_000),
        ("Rp 1.2M", 1_200_000_000),    # M = miliar (1B)
        ("Rp 600jt", 600_000_000),
        ("Rp 50000000", 50_000_000),
        ("Rp 1 miliar", 1_000_000_000),
        ("rp 50jt", 50_000_000),        # lowercase
    ])
    def test_parses(self, raw, expected):
        assert parse_revenue_idr(raw) == expected

    @pytest.mark.parametrize("raw", [None, "", "free text", "abc"])
    def test_unparseable(self, raw):
        result = parse_revenue_idr(raw)
        assert result is None


# --- classify_tier ---

class TestClassifyTier:
    def test_smb_low_revenue(self):
        r = classify_tier(revenue_estimate="Rp 30jt/bulan")
        assert r["tier"] == TIER_SMB

    def test_smb_low_employees(self):
        r = classify_tier(employee_count=5)
        assert r["tier"] == TIER_SMB

    def test_mid_revenue(self):
        r = classify_tier(revenue_estimate="Rp 100jt/bulan")
        assert r["tier"] == TIER_MID

    def test_mid_employees(self):
        r = classify_tier(employee_count=30)
        assert r["tier"] == TIER_MID

    def test_enterprise_revenue(self):
        r = classify_tier(revenue_estimate="Rp 600jt/bulan")
        assert r["tier"] == TIER_ENTERPRISE

    def test_enterprise_employees(self):
        r = classify_tier(employee_count=60)
        assert r["tier"] == TIER_ENTERPRISE

    def test_unknown_when_no_data(self):
        r = classify_tier()
        assert r["tier"] == TIER_UNKNOWN
        assert r["confidence"] == 0.0

    def test_confidence_grows_with_data(self):
        none = classify_tier()
        just_emp = classify_tier(employee_count=10)
        both = classify_tier(employee_count=10, revenue_estimate="Rp 100jt")
        assert none["confidence"] < just_emp["confidence"] < both["confidence"]

    def test_revenue_wins_over_employees_when_conflicting(self):
        # 5 employees but Rp 600jt → enterprise (revenue is more
        # reliable than employee count for tier classification)
        r = classify_tier(
            employee_count=5, revenue_estimate="Rp 600jt",
        )
        # The revenue check is the first thing done
        assert r["tier"] == TIER_ENTERPRISE

    def test_employee_50_overrides_mid_revenue(self):
        # Mid revenue but 50+ employees → enterprise
        r = classify_tier(
            employee_count=50, revenue_estimate="Rp 100jt",
        )
        assert r["tier"] == TIER_ENTERPRISE

    def test_signals_boost_confidence(self):
        base = classify_tier(employee_count=5)
        boosted = classify_tier(employee_count=5, n_signals=3)
        assert boosted["confidence"] >= base["confidence"]


# --- tier_score ---

class TestTierScore:
    def test_smb_high(self):
        s, _ = tier_score("smb", 1.0)
        assert s == 85.0

    def test_enterprise_low(self):
        s, _ = tier_score("enterprise", 1.0)
        assert s == 45.0

    def test_unknown_neutral(self):
        s, _ = tier_score("unknown", 0.0)
        assert s == 50.0

    def test_low_confidence_pulls_toward_50(self):
        s_high, _ = tier_score("smb", 0.9)
        s_low, _ = tier_score("smb", 0.1)
        # Lower confidence → closer to 50
        assert 50.0 < s_low < s_high < 100.0

    def test_none_treated_as_unknown(self):
        s, reasons = tier_score(None, 0.0)
        assert s == 50.0
        assert any("unknown" in r for r in reasons)

    def test_score_in_range(self):
        for tier in ["smb", "mid", "enterprise", "unknown", None]:
            for conf in [0.0, 0.5, 1.0]:
                s, _ = tier_score(tier, conf)
                assert 0.0 <= s <= 100.0


# --- industry_specificity_score ---

class TestIndustrySpecificityScore:
    def test_generic(self):
        s, _ = industry_specificity_score(False, False)
        assert s == 40.0

    def test_specific_only(self):
        s, _ = industry_specificity_score(True, False)
        assert s == 75.0

    def test_specific_with_pain_match(self):
        s, _ = industry_specificity_score(True, True)
        assert s == 95.0

    def test_specific_no_pain_match(self):
        s, reasons = industry_specificity_score(True, False)
        assert s == 75.0
        assert "Specific" in reasons[0]


# --- compute_score kwargs bug regression (3rd carryover) ---

class TestComputeScoreKwargsBug:
    """Regression test for the 3rd-checkpoint-carryover risk-penalty
    arg-order bug. The signature is:
        risk_penalty_score(source, has_phone, has_email, has_industry, has_website)
    And the call MUST pass has_website as the 5th arg (not
    bool(location_city)). If the call is positional with
    bool(location_city) in the 5th slot, the bug surfaces:
    a prospect with website + no city gets the 'no website'
    penalty incorrectly."""

    def test_website_no_city_no_website_penalty(self):
        """The bug case: prospect has website but no city.
        Should NOT get the 'no website' penalty (because has_website
        is True). With the bug (bool(location_city) as 5th arg),
        it would get the penalty since location_city is None.
        """
        penalty, reasons = risk_penalty_score(
            source="manual",
            has_phone=True,
            has_email=True,
            has_industry=True,
            has_website=True,  # the prospect HAS a website
        )
        # Should NOT contain "No website" penalty
        for r in reasons:
            assert "No website" not in r, (
                f"BUG: got 'No website' penalty despite has_website=True. "
                f"Reasons: {reasons}"
            )

    def test_no_website_does_get_penalty(self):
        """Negative case: prospect has no website, should get penalty."""
        penalty, reasons = risk_penalty_score(
            source="manual",
            has_phone=True,
            has_email=True,
            has_industry=True,
            has_website=False,
        )
        assert any("No website" in r for r in reasons)

    def test_website_present_in_compute_score(self):
        """Integration: compute_score with has_website=True,
        location_city=None should not surface 'No website' penalty."""
        score = compute_score(
            n_signals=2,
            pains=[{"kind": "no_booking", "severity": 60}],
            industry="klinik",
            location_city=None,  # key: no city
            discovered_at=datetime(2026, 6, 14, tzinfo=timezone.utc),
            has_phone=True,
            has_email=True,
            has_social=True,
            has_address=True,
            has_website=True,  # key: has website
            source="maps",
        )
        # The breakdown's risk_penalty should NOT include
        # 'No website' reason
        for r in score.reasoning:
            assert "No website" not in r, (
                f"BUG: compute_score surfaces 'No website' penalty when "
                f"has_website=True. Reasoning: {score.reasoning}"
            )

    def test_kwargs_in_compute_score(self):
        """Verify the call site uses kwargs (defensive). This test
        inspects the source code of compute_score to ensure
        risk_penalty_score is called with kwargs, not positional
        args (which would be brittle)."""
        import inspect
        from app.services.analyzer import scorer as scorer_mod
        src = inspect.getsource(scorer_mod.compute_score)
        # Find the risk_penalty_score call (multi-line)
        idx = src.find("risk_penalty_score(")
        assert idx >= 0, "risk_penalty_score call not found"
        # Find the matching close-paren by counting depth
        end = idx
        depth = 0
        for i in range(idx, len(src)):
            if src[i] == "(":
                depth += 1
            elif src[i] == ")":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        call = src[idx:end + 1]
        # Ensure the call uses has_website=... (kwarg form)
        assert "has_website=" in call, (
            f"compute_score should call risk_penalty_score with has_website= "
            f"as kwarg. Call: {call}"
        )
        # And ensure the call does NOT use bool(location_city) as
        # a positional arg (the bug)
        assert "bool(location_city)" not in call, (
            f"BUG REGRESSION: compute_score still calls risk_penalty_score "
            f"with bool(location_city) in 5th positional slot. Call: {call}"
        )


# --- compute_score with new tier + industry_specificity ---

class TestComputeScoreSprint3B:
    def test_tier_factor(self):
        smb = compute_score(
            n_signals=2, pains=[], industry="fnb", location_city="Jakarta",
            discovered_at=datetime.now(timezone.utc),
            tier="smb", tier_confidence=0.9,
        )
        ent = compute_score(
            n_signals=2, pains=[], industry="fnb", location_city="Jakarta",
            discovered_at=datetime.now(timezone.utc),
            tier="enterprise", tier_confidence=0.9,
        )
        assert smb.tier > ent.tier
        # Total is influenced by tier
        assert smb.total > ent.total

    def test_industry_specificity_factor(self):
        generic = compute_score(
            n_signals=2, pains=[], industry="fnb", location_city="Jakarta",
            discovered_at=datetime.now(timezone.utc),
        )
        specific = compute_score(
            n_signals=2, pains=[], industry="fnb", location_city="Jakarta",
            discovered_at=datetime.now(timezone.utc),
            has_specific_industry=True, industry_match_with_pains=True,
        )
        assert specific.industry_specificity > generic.industry_specificity
        # When industry matches the detected pains, total should be
        # at least as high (and likely higher)
        assert specific.total >= generic.total - 0.01

    def test_weights_sum_with_new_factors(self):
        score = compute_score(
            n_signals=2, pains=[], industry="klinik", location_city="Bandung",
            discovered_at=datetime.now(timezone.utc),
        )
        # Should not raise (the WEIGHTS assertion at import time
        # ensures sum = 0.95)
        assert score.total is not None
