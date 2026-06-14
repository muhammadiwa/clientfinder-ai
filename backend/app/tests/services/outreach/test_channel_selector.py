"""
Sprint 3A — Multi-channel outreach unit tests.

Covers:
- render_template: variable substitution, defaults for missing
- canonicalize_industry: alias mapping
- channel_selector: industry-aware pick + phone normalization
- pick_template: industry-specific → umum → any fallback
- Drip runner: enrollments walk, no-template skip, completed flow
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.prospect import Prospect
from app.services.outreach.channel_selector import (
    ChannelPick,
    _normalize_phone,
    pick_channel,
)
from app.services.outreach.template_factory import (
    CATEGORY_BREAKUP,
    CATEGORY_FIRST_TOUCH,
    CATEGORY_FOLLOW_UP,
    INDUSTRIES,
    INDUSTRY_FNB,
    INDUSTRY_KLINIK,
    INDUSTRY_UMUM,
    VAR_DEFAULTS,
    canonicalize_industry,
    render_template,
)


# --- render_template ---

class TestRenderTemplate:
    def test_substitutes_known_var(self):
        result = render_template(
            "Halo {owner_name} dari {company_name}",
            {"owner_name": "Budi", "company_name": "Toko ABC"},
        )
        assert result == "Halo Budi dari Toko ABC"

    def test_unknown_var_uses_default(self):
        result = render_template(
            "{sender_name} | {missing_var}",
            {},
        )
        assert "Tim ClientFinder" in result
        # missing_var has no default — left as-is per VAR_DEFAULTS
        assert "{missing_var}" in result

    def test_empty_var_uses_default(self):
        result = render_template("Halo {owner_name}", {"owner_name": ""})
        assert "Bapak/Ibu" in result

    def test_multi_word_var(self):
        result = render_template(
            "Pekerjaan: {pain_summary}",
            {"pain_summary": "stok tidak terkontrol"},
        )
        assert "stok tidak terkontrol" in result

    def test_no_vars(self):
        assert render_template("plain text", {}) == "plain text"

    def test_var_with_numbers(self):
        result = render_template(
            "Halo, tahun 2026 owner {owner1_name}",
            {"owner1_name": "Andi"},
        )
        assert "Andi" in result


# --- canonicalize_industry ---

class TestCanonicalizeIndustry:
    @pytest.mark.parametrize("raw,expected", [
        ("restoran", INDUSTRY_FNB),
        ("Kafe", INDUSTRY_FNB),
        ("FN B", INDUSTRY_FNB),
        ("toko", "retail"),
        ("Klinik", INDUSTRY_KLINIK),
        ("Apotek", INDUSTRY_KLINIK),
        ("salon", "salon"),
        ("konsultan", "jasa"),
        ("agensi", "jasa"),
        ("agency", "jasa"),
        ("unknown_xyz", INDUSTRY_UMUM),
        ("", INDUSTRY_UMUM),
        (None, INDUSTRY_UMUM),
    ])
    def test_aliases(self, raw, expected):
        assert canonicalize_industry(raw) == expected


# --- _normalize_phone ---

class TestNormalizePhone:
    @pytest.mark.parametrize("raw,expected", [
        ("0812345678", "+62812345678"),
        ("+1234567890", "+1234567890"),
        ("+62 812 345 678", "+62812345678"),
        ("62 812 345 678", "+62812345678"),
        ("00 62 812 345 678", "+62812345678"),
        ("0812-345-678", "+62812345678"),
        ("", None),
        (None, None),
    ])
    def test_normalize(self, raw, expected):
        assert _normalize_phone(raw) == expected


# --- pick_channel ---

def _make_prospect(email: str | None = None, phone: str | None = None) -> Prospect:
    """Build a Prospect with only email + phone set (other fields irrelevant)."""
    p = MagicMock(spec=Prospect)
    p.email = email
    p.phone = phone
    return p


class TestPickChannel:
    def test_no_contact_returns_none(self):
        pick = pick_channel(_make_prospect())
        assert pick.channel is None
        assert pick.recipient is None
        assert "no email" in pick.reason.lower()

    def test_email_only(self):
        pick = pick_channel(_make_prospect(email="a@b.com"))
        assert pick.channel == "email"
        assert pick.recipient == "a@b.com"

    def test_phone_only(self):
        pick = pick_channel(_make_prospect(phone="0812345678"))
        assert pick.channel == "whatsapp"
        assert pick.recipient == "+62812345678"

    def test_wa_preferred_industry_chooses_wa(self):
        # F&B has both: WA preferred
        pick = pick_channel(
            _make_prospect(email="a@b.com", phone="0812345678"),
            industry_canonical=INDUSTRY_FNB,
        )
        assert pick.channel == "whatsapp"
        assert "WA-first" in pick.reason

    def test_non_wa_industry_chooses_email(self):
        # Jasa (B2B): email preferred
        pick = pick_channel(
            _make_prospect(email="a@b.com", phone="0812345678"),
            industry_canonical="jasa",
        )
        assert pick.channel == "email"

    def test_klinik_prefers_wa(self):
        pick = pick_channel(
            _make_prospect(email="a@b.com", phone="0812345678"),
            industry_canonical=INDUSTRY_KLINIK,
        )
        assert pick.channel == "whatsapp"

    def test_preferred_channel_email_respected(self):
        # Even in WA-preferred industry, honor the override
        pick = pick_channel(
            _make_prospect(email="a@b.com", phone="0812345678"),
            preferred_channel="email",
            industry_canonical=INDUSTRY_FNB,
        )
        assert pick.channel == "email"

    def test_preferred_channel_wa_respected(self):
        pick = pick_channel(
            _make_prospect(email="a@b.com", phone="0812345678"),
            preferred_channel="whatsapp",
            industry_canonical="jasa",
        )
        assert pick.channel == "whatsapp"

    def test_preferred_channel_email_without_email(self):
        pick = pick_channel(
            _make_prospect(phone="0812345678"),
            preferred_channel="email",
        )
        assert pick.channel is None
        assert "no email" in pick.reason.lower()

    def test_preferred_channel_wa_without_phone(self):
        pick = pick_channel(
            _make_prospect(email="a@b.com"),
            preferred_channel="whatsapp",
        )
        assert pick.channel is None
        assert "no phone" in pick.reason.lower()
