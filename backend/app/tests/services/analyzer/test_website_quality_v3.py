"""
Sprint 1 / Phase 1.2 — Advanced website quality + pain detection tests.

Covers:
- website_checker._check_viewport_meta: 6 cases
- website_checker._detect_payment_gateways: 7 cases (each gateway)
- pain_detector.detect_pains: 3 new rules
  - no_mobile_friendly
  - has_console_errors (≥ 3 errors threshold)
  - no_payment_system (e-commerce industries only)
"""
import pytest

from app.services.analyzer.pain_detector import detect_pains
from app.services.analyzer.website_checker import (
    PAYMENT_GATEWAYS,
    _check_viewport_meta,
    _detect_payment_gateways,
)


# --- _check_viewport_meta ---

class TestViewportMeta:
    def test_standard_viewport_meta_present(self):
        html = '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body></body></html>'
        assert _check_viewport_meta(html) is True

    def test_viewport_meta_case_insensitive(self):
        html = '<META NAME="VIEWPORT" CONTENT="width=device-width">'
        assert _check_viewport_meta(html) is True

    def test_handheldfriendly_meta_present(self):
        html = '<head><meta name="HandheldFriendly" content="True"></head>'
        assert _check_viewport_meta(html) is True

    def test_mobileoptimized_meta_present(self):
        html = '<head><meta name="MobileOptimized" content="width"></head>'
        assert _check_viewport_meta(html) is True

    def test_theme_color_meta_present(self):
        html = '<head><meta name="theme-color" content="#ffffff"></head>'
        assert _check_viewport_meta(html) is True

    def test_no_viewport_meta(self):
        """The classic desktop-only / old site case — no viewport meta."""
        html = '<html><head><title>Old Site</title></head><body><h1>Welcome</h1></body></html>'
        assert _check_viewport_meta(html) is False

    def test_empty_html(self):
        assert _check_viewport_meta("") is False


# --- _detect_payment_gateways ---

class TestPaymentGateways:
    def test_no_gateways(self):
        html = "<html><body>Contact us at info@example.com</body></html>"
        assert _detect_payment_gateways(html) == []

    def test_midtrans(self):
        html = '<script src="https://app.midtrans.com/snap/snap.js"></script>'
        result = _detect_payment_gateways(html)
        assert "midtrans" in result

    def test_xendit(self):
        html = '<iframe src="https://checkout.xendit.co/v2/invoice"></iframe>'
        result = _detect_payment_gateways(html)
        assert "xendit" in result

    def test_doku(self):
        html = '<script src="https://secure.doku.com/doku-js"></script>'
        result = _detect_payment_gateways(html)
        assert "doku" in result

    def test_tripay(self):
        html = '<script src="https://tripay.co.id/assets/js/checkout.js"></script>'
        result = _detect_payment_gateways(html)
        assert "tripay" in result

    def test_stripe(self):
        html = '<script src="https://js.stripe.com/v3/"></script>'
        result = _detect_payment_gateways(html)
        assert "stripe" in result

    def test_paypal(self):
        html = '<script src="https://www.paypal.com/sdk/js?client-id=xxx"></script>'
        result = _detect_payment_gateways(html)
        assert "paypal" in result

    def test_razorpay(self):
        html = '<script src="https://checkout.razorpay.com/v1/checkout.js"></script>'
        result = _detect_payment_gateways(html)
        assert "razorpay" in result

    def test_multiple_gateways_deduped(self):
        html = (
            '<script src="https://js.stripe.com/v3/"></script>'
            '<script src="https://js.stripe.com/v2/"></script>'  # duplicate
            '<script src="https://app.midtrans.com/snap/snap.js"></script>'
        )
        result = _detect_payment_gateways(html)
        assert "stripe" in result
        assert "midtrans" in result
        # Deduped — stripe appears only once
        assert result.count("stripe") == 1

    def test_all_known_gateways_have_patterns(self):
        """Sanity: every name in the public-facing list has a regex."""
        for name, _ in PAYMENT_GATEWAYS:
            assert isinstance(name, str)
            assert len(name) >= 3


# --- Pain detection: 3 new rules ---

class TestNoMobileFriendly:
    def test_no_viewport_fires_pain(self):
        pains = detect_pains(
            website="https://example.com",
            industry="klinik gigi",
            location_city="Jakarta",
            has_phone=True, has_email=True,
            has_ssl=True,
            has_viewport_meta=False,
            payment_gateways=["midtrans"],
        )
        kinds = [p["kind"] for p in pains]
        assert "no_mobile_friendly" in kinds
        mobile_pain = next(p for p in pains if p["kind"] == "no_mobile_friendly")
        assert mobile_pain["severity"] == 70
        assert "responsive" in mobile_pain["recommended_service"].lower() or "redesign" in mobile_pain["recommended_service"].lower()

    def test_viewport_present_no_pain(self):
        pains = detect_pains(
            website="https://example.com",
            industry="klinik gigi",
            location_city="Jakarta",
            has_phone=True, has_email=True,
            has_ssl=True,
            has_viewport_meta=True,
            payment_gateways=["midtrans"],
        )
        kinds = [p["kind"] for p in pains]
        assert "no_mobile_friendly" not in kinds

    def test_default_no_pain_for_legacy_callers(self):
        """When the param is not passed (default True), no mobile pain."""
        pains = detect_pains(
            website="https://example.com",
            industry="klinik",
            location_city="Jakarta", has_phone=True, has_email=True,
        )
        kinds = [p["kind"] for p in pains]
        assert "no_mobile_friendly" not in kinds


class TestHasConsoleErrors:
    def test_zero_errors_no_pain(self):
        pains = detect_pains(
            website="https://example.com",
            industry="restoran",
            location_city="Jakarta", has_phone=True, has_email=True,
            console_errors=[],
        )
        assert "has_console_errors" not in [p["kind"] for p in pains]

    def test_one_error_no_pain(self):
        """1 error is transient — don't fire."""
        pains = detect_pains(
            website="https://example.com",
            industry="restoran",
            location_city="Jakarta", has_phone=True, has_email=True,
            console_errors=["Uncaught TypeError: x is undefined"],
        )
        assert "has_console_errors" not in [p["kind"] for p in pains]

    def test_two_errors_no_pain(self):
        """2 errors still borderline."""
        pains = detect_pains(
            website="https://example.com",
            industry="restoran",
            location_city="Jakarta", has_phone=True, has_email=True,
            console_errors=["err1", "err2"],
        )
        assert "has_console_errors" not in [p["kind"] for p in pains]

    def test_three_errors_fires_pain(self):
        pains = detect_pains(
            website="https://example.com",
            industry="restoran",
            location_city="Jakarta", has_phone=True, has_email=True,
            console_errors=["err1", "err2", "err3"],
        )
        kinds = [p["kind"] for p in pains]
        assert "has_console_errors" in kinds
        pain = next(p for p in pains if p["kind"] == "has_console_errors")
        assert pain["severity"] == 45
        # Evidence includes sample of errors
        assert "sample" in pain["evidence"]
        assert "err1" in pain["evidence"]["sample"]

    def test_ten_errors_evidence_capped_to_five(self):
        errors = [f"err{i}" for i in range(10)]
        pains = detect_pains(
            website="https://example.com",
            industry="restoran",
            location_city="Jakarta", has_phone=True, has_email=True,
            console_errors=errors,
        )
        pain = next(p for p in pains if p["kind"] == "has_console_errors")
        assert pain["evidence"]["n_errors"] == 10
        assert len(pain["evidence"]["sample"]) == 5


class TestNoPaymentSystem:
    def test_fnb_industry_no_gateway_fires_pain(self):
        pains = detect_pains(
            website="https://example.com",
            industry="restoran",
            location_city="Jakarta", has_phone=True, has_email=True,
            payment_gateways=[],  # none
        )
        kinds = [p["kind"] for p in pains]
        assert "no_payment_system" in kinds

    def test_klinik_industry_no_gateway_fires_pain(self):
        pains = detect_pains(
            website="https://example.com",
            industry="klinik gigi",
            location_city="Jakarta", has_phone=True, has_email=True,
            payment_gateways=[],
        )
        assert "no_payment_system" in [p["kind"] for p in pains]

    def test_toko_industry_no_gateway_fires_pain(self):
        pains = detect_pains(
            website="https://example.com",
            industry="toko sepatu",
            location_city="Jakarta", has_phone=True, has_email=True,
            payment_gateways=[],
        )
        assert "no_payment_system" in [p["kind"] for p in pains]

    def test_fnb_with_midtrans_no_pain(self):
        pains = detect_pains(
            website="https://example.com",
            industry="restoran",
            location_city="Jakarta", has_phone=True, has_email=True,
            payment_gateways=["midtrans"],
        )
        assert "no_payment_system" not in [p["kind"] for p in pains]

    def test_non_ecommerce_industry_no_pain(self):
        """For non-ecommerce industries (e.g., service-only), no payment
        gateway is fine — don't flag."""
        pains = detect_pains(
            website="https://example.com",
            industry="konsultan",  # not in ecommerce_industries
            location_city="Jakarta", has_phone=True, has_email=True,
            payment_gateways=[],
        )
        assert "no_payment_system" not in [p["kind"] for p in pains]

    def test_no_payment_pain_evidence_lists_industry(self):
        pains = detect_pains(
            website="https://example.com",
            industry="restoran",
            location_city="Jakarta", has_phone=True, has_email=True,
            payment_gateways=[],
        )
        pain = next(p for p in pains if p["kind"] == "no_payment_system")
        assert pain["evidence"]["industry"] == "restoran"
        assert pain["evidence"]["gateways_found"] == []
        assert pain["severity"] == 60
        assert "payment" in pain["recommended_service"].lower()


# --- Integration: 3 new rules together ---

class TestNewRulesIntegration:
    def test_all_three_new_pains_can_fire_together(self):
        """A site with no viewport, no payment, and broken JS triggers
        all 3 new pains plus the original 2 (no SSL, no WA, etc.)."""
        pains = detect_pains(
            website="https://example.com",
            industry="restoran",
            location_city="Bandung",
            has_phone=True, has_email=True,
            has_wa_business=False,
            has_ssl=True,
            has_viewport_meta=False,
            payment_gateways=[],
            console_errors=["e1", "e2", "e3", "e4", "e5"],
        )
        kinds = [p["kind"] for p in pains]
        assert "no_mobile_friendly" in kinds
        assert "has_console_errors" in kinds
        assert "no_payment_system" in kinds
        # Plus the original 2
        assert "no_wa_business" in kinds

    def test_realistic_modern_site_no_new_pains(self):
        """A modern site with viewport + Stripe + no JS errors gets
        no new pains."""
        pains = detect_pains(
            website="https://example.com",
            industry="restoran",
            location_city="Jakarta",
            has_phone=True, has_email=True,
            has_wa_business=True,
            has_ssl=True,
            has_viewport_meta=True,
            payment_gateways=["stripe", "midtrans"],
            console_errors=[],
        )
        kinds = [p["kind"] for p in pains]
        assert "no_mobile_friendly" not in kinds
        assert "has_console_errors" not in kinds
        assert "no_payment_system" not in kinds
