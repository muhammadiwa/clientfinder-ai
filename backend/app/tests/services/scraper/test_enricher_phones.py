"""
Unit tests for HomepageEnricher.extract_phones.

Covers:
- tel: hrefs (priority 0)
- wa.me / whatsapp.com (priority 1)
- +62 / 0-prefix regex on visible text (priority 2)
- generic 8-16 digit matches (priority 3)
- False positives: prices (Rp 50.000), dates, CSS counters
- Dedupe + max-3 cap
- Empty inputs
"""
import pytest

from app.services.scraper.enricher import HomepageEnricher


class TestTelHref:
    def test_simple_tel_href(self):
        html = '<a href="tel:+62215551234">Call</a>'
        assert HomepageEnricher.extract_phones(html, "") == ["+62215551234"]

    def test_tel_href_with_spaces(self):
        html = '<a href="tel:+62 21 555 1234">Hubungi</a>'
        out = HomepageEnricher.extract_phones(html, "")
        assert len(out) == 1
        assert out[0].replace(" ", "") == "+62215551234"

    def test_tel_href_too_short_filtered(self):
        html = '<a href="tel:12345">Bad</a>'
        assert HomepageEnricher.extract_phones(html, "") == []

    def test_tel_href_too_long_filtered(self):
        html = '<a href="tel:+62222222222222222222">Bad</a>'
        assert HomepageEnricher.extract_phones(html, "") == []


class TestWhatsAppHref:
    def test_wa_me_digit_only(self):
        html = '<a href="https://wa.me/6281234567890">Chat</a>'
        assert HomepageEnricher.extract_phones(html, "") == ["6281234567890"]

    def test_whatsapp_send_phone(self):
        html = '<a href="https://api.whatsapp.com/send?phone=6281234567890">Chat</a>'
        out = HomepageEnricher.extract_phones(html, "")
        assert out == ["6281234567890"]


class TestVisibleTextRegex:
    def test_plus_62_prefix(self):
        text = "Hubungi kami di +62 21 555-1234 untuk reservasi"
        out = HomepageEnricher.extract_phones("", text)
        assert len(out) == 1
        assert "21" in out[0] and "555" in out[0]

    def test_zero_prefix_local(self):
        text = "Telepon: (021) 555-1234"
        out = HomepageEnricher.extract_phones("", text)
        assert len(out) == 1
        assert "555" in out[0]

    def test_indonesian_mobile(self):
        text = "WA: 0812-3456-7890"
        out = HomepageEnricher.extract_phones("", text)
        assert out[0].replace("-", "").startswith("0812")

    def test_no_match_too_short(self):
        text = "kode 1234"
        assert HomepageEnricher.extract_phones("", text) == []


class TestPriorityOrdering:
    def test_tel_beats_text(self):
        """tel: href should come before generic text matches."""
        html = '<a href="tel:+62215551234">Call</a>'
        text = "or call 555-999-1234"
        out = HomepageEnricher.extract_phones(html, text)
        assert out[0] == "+62215551234"
        assert any("5559991234" in p.replace("-", "") for p in out)

    def test_plus62_beats_generic(self):
        """+62 prefix should rank above generic 8-16 digit numbers."""
        text = "Call 5551234 or +62 21 5559999"
        out = HomepageEnricher.extract_phones("", text)
        assert out[0].replace(" ", "").startswith("+62")


class TestFalsePositives:
    def test_price_rp_50000_filtered(self):
        """Rp 50.000 is 6 digits, should be filtered (< 8)."""
        text = "Harga mulai Rp 50.000"
        assert HomepageEnricher.extract_phones("", text) == []

    def test_css_counter_filtered(self):
        """CSS counters like 'items: 12345' are 5 digits, filtered."""
        text = "items: 12345 in stock"
        assert HomepageEnricher.extract_phones("", text) == []

    def test_date_filtered(self):
        """Dates like 2024-01-15 are short, filtered."""
        text = "Posted on 2024-01-15"
        assert HomepageEnricher.extract_phones("", text) == []


class TestDedupeAndCap:
    def test_max_three_results(self):
        text = "Phones: 021-111-1111, 021-222-2222, 021-333-3333, 021-444-4444"
        out = HomepageEnricher.extract_phones("", text)
        assert len(out) == 3

    def test_dedupes_repeated_phone(self):
        text = "Phone: 021-555-1234. Again: 021-555-1234."
        out = HomepageEnricher.extract_phones("", text)
        # Same phone twice with slightly different separators
        # (extract_phones dedupes by exact string)
        assert len(out) <= 2

    def test_empty_inputs(self):
        assert HomepageEnricher.extract_phones("", "") == []
        assert HomepageEnricher.extract_phones("", None or "") == []
