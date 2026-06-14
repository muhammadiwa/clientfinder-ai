"""
Unit tests for the 7-factor lead scorer (Sprint 1).

Covers:
- contact_availability_score: 0/1/2/3/5 channels
- personalization_quality_score: 0/1/2/3+ specific pains, industry match bonus
- risk_penalty_score: source reputation, missing contacts, missing industry
- compute_score integration: all 7 factors + risk penalty, weights sum to 1.0
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.services.analyzer.scorer import (
    ScoreBreakdown,
    contact_availability_score,
    personalization_quality_score,
    risk_penalty_score,
    compute_score,
)


# --- contact_availability_score ---

class TestContactAvailability:
    def test_no_channels(self):
        score, reasons = contact_availability_score(
            has_phone=False, has_email=False, has_social=False,
            has_website=False, has_address=False,
        )
        assert score == 0.0
        assert "unreachable" in reasons[0].lower()

    def test_one_channel(self):
        score, reasons = contact_availability_score(
            has_phone=True, has_email=False, has_social=False,
            has_website=False, has_address=False,
        )
        assert score == 40.0
        assert "phone" in reasons[0].lower()

    def test_two_channels(self):
        score, reasons = contact_availability_score(
            has_phone=True, has_email=True, has_social=False,
            has_website=False, has_address=False,
        )
        assert score == 70.0
        assert "phone" in reasons[0].lower()
        assert "email" in reasons[0].lower()

    def test_three_channels(self):
        score, _ = contact_availability_score(
            has_phone=True, has_email=True, has_social=True,
            has_website=False, has_address=False,
        )
        assert score == 90.0

    def test_five_channels(self):
        score, reasons = contact_availability_score(
            has_phone=True, has_email=True, has_social=True,
            has_website=True, has_address=True,
        )
        assert score == 100.0
        assert "5 contact channels" in reasons[0]


# --- personalization_quality_score ---

class TestPersonalizationQuality:
    def test_no_pains(self):
        score, reasons = personalization_quality_score([], None)
        assert score == 10.0
        assert "generic" in reasons[0].lower()

    def test_one_specific_pain(self):
        score, _ = personalization_quality_score(
            [{"kind": "no_booking_system", "severity": 70}], None,
        )
        assert score == 50.0

    def test_two_specific_pains(self):
        score, _ = personalization_quality_score(
            [
                {"kind": "no_booking_system", "severity": 70},
                {"kind": "slow_site", "severity": 60},
            ],
            None,
        )
        assert score == 75.0

    def test_three_specific_pains(self):
        score, _ = personalization_quality_score(
            [
                {"kind": "no_booking_system", "severity": 70},
                {"kind": "slow_site", "severity": 60},
                {"kind": "no_wa_business", "severity": 50},
            ],
            None,
        )
        assert score == 90.0

    def test_industry_match_bonus(self):
        score, reasons = personalization_quality_score(
            [{"kind": "no_booking_system", "severity": 70}],
            "klinik gigi jakarta",
        )
        # 1 specific = 50 base + 10 industry match = 60
        assert score == 60.0
        assert any("industry" in r.lower() for r in reasons)

    def test_only_generic_pains(self):
        score, _ = personalization_quality_score(
            [{"kind": "no_website", "severity": 90}],
            "klinik gigi",
        )
        # 0 specific = 20 base + 10 industry match = 30
        assert score == 30.0


# --- risk_penalty_score ---

class TestRiskPenalty:
    def test_clean_prospect_no_penalty(self):
        score, reasons = risk_penalty_score(
            source="maps", has_phone=True, has_email=True,
            has_industry=True, has_website=True,
        )
        assert score == 0.0
        assert reasons == []

    def test_google_source_penalty(self):
        score, reasons = risk_penalty_score(
            source="google", has_phone=True, has_email=True,
            has_industry=True, has_website=True,
        )
        assert score == 10.0
        assert any("google" in r.lower() for r in reasons)

    def test_no_phone_no_email_penalty(self):
        score, reasons = risk_penalty_score(
            source="maps", has_phone=False, has_email=False,
            has_industry=True, has_website=True,
        )
        assert score == 8.0
        assert any("no phone" in r.lower() for r in reasons)

    def test_no_industry_penalty(self):
        score, _ = risk_penalty_score(
            source="maps", has_phone=True, has_email=True,
            has_industry=False, has_website=True,
        )
        assert score == 3.0

    def test_cumulative_capped_at_max(self):
        # 10 (google) + 8 (no contact) + 3 (no industry) + 2 (no website) = 23, capped at 20
        score, reasons = risk_penalty_score(
            source="google", has_phone=False, has_email=False,
            has_industry=False, has_website=False,
        )
        assert score == 20.0
        assert any("capped" in r.lower() for r in reasons)


# --- compute_score integration ---

class TestComputeScoreIntegration:
    def test_weights_sum_to_one(self):
        from app.services.analyzer.scorer import WEIGHTS
        assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-6

    def test_hot_lead(self):
        """A real klinik in Jakarta with full data + specific pains."""
        pains = [
            {"kind": "no_booking_system", "severity": 80},
            {"kind": "slow_site", "severity": 60},
            {"kind": "no_wa_business", "severity": 70},
        ]
        score = compute_score(
            n_signals=0,
            pains=pains,
            industry="klinik gigi",
            location_city="Jakarta",
            discovered_at=datetime.now(timezone.utc) - timedelta(days=2),
            has_phone=True, has_email=True, has_social=True,
            has_address=True, has_website=True,
            source="maps",
        )
        assert isinstance(score, ScoreBreakdown)
        assert score.total >= 70, f"Expected Hot Lead, got {score.total}"
        assert score.grade in ("A", "B")
        # Verify all 7 components are present
        assert score.contact_availability > 0
        assert score.personalization_quality > 0
        assert score.risk_penalty == 0.0  # maps = no penalty

    def test_google_noisy_cold_lead(self):
        """Google search result with no contact = D grade."""
        score = compute_score(
            n_signals=0,
            pains=[{"kind": "no_website", "severity": 90}],
            industry=None,
            location_city=None,
            discovered_at=datetime.now(timezone.utc) - timedelta(days=60),
            has_phone=False, has_email=False, has_social=False,
            has_address=False, has_website=None,
            source="google",
        )
        # Heavy risk penalty + stale + no contact = low
        assert score.risk_penalty >= 18  # source + no contact + no industry
        assert score.grade == "D", f"Expected D, got {score.grade} ({score.total})"

    def test_warm_lead_with_partial_data(self):
        """Realistic mid-tier prospect."""
        score = compute_score(
            n_signals=0,
            pains=[
                {"kind": "no_booking_system", "severity": 75},
                {"kind": "stale_website", "severity": 50},
            ],
            industry="restoran",
            location_city="Bandung",
            discovered_at=datetime.now(timezone.utc) - timedelta(days=10),
            has_phone=True, has_email=False, has_social=True,
            has_address=True, has_website=True,
            source="maps",
        )
        # 2 specific + 1 channel = warm range
        assert 40 <= score.total <= 79, f"Expected warm, got {score.total}"
        assert score.grade in ("B", "C")

    def test_ignoring_due_to_risk(self):
        """Same data quality, but google source pushes it below ignore threshold."""
        clean = compute_score(
            n_signals=0, pains=[{"kind": "no_booking_system", "severity": 80}],
            industry="klinik gigi", location_city="Jakarta",
            discovered_at=datetime.now(timezone.utc) - timedelta(days=3),
            has_phone=True, has_email=True, has_social=True,
            has_address=True, has_website=True,
            source="maps",
        )
        google = compute_score(
            n_signals=0, pains=[{"kind": "no_booking_system", "severity": 80}],
            industry="klinik gigi", location_city="Jakarta",
            discovered_at=datetime.now(timezone.utc) - timedelta(days=3),
            has_phone=True, has_email=True, has_social=True,
            has_address=True, has_website=True,
            source="google",
        )
        # Google penalty = 10 points lower
        assert google.total < clean.total
        assert clean.total - google.total >= 9
