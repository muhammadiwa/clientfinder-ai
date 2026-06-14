"""
Unit tests for HomepageEnricher.extract_address.

Covers:
- Microdata (itemprop="address")
- OpenGraph (business:contact_data:street_address)
- Indonesian footer regex (Jl., Jalan, Ruko, Komp., etc.)
- Length filter (8-200 chars)
- Priority ordering
- Negative cases (no address, too short, too long)
"""
import pytest

from app.services.scraper.enricher import HomepageEnricher


class TestMicrodata:
    def test_simple_microdata(self):
        html = '<div itemprop="address">Jl. Sudirman No. 45, Jakarta Selatan</div>'
        out = HomepageEnricher.extract_address(html, "")
        assert "Sudirman" in out

    def test_microdata_with_attributes(self):
        html = '<span itemprop="address" class="foo">Ruko Blok B-12, Bandung</span>'
        out = HomepageEnricher.extract_address(html, "")
        assert "Ruko" in out


class TestOpenGraph:
    def test_og_address(self):
        html = (
            '<meta property="business:contact_data:street_address" '
            'content="Jl. Thamrin No. 1, Jakarta Pusat">'
        )
        out = HomepageEnricher.extract_address(html, "")
        assert "Thamrin" in out

    def test_og_with_other_props(self):
        html = (
            '<meta property="business:contact_data:locality" content="Jakarta">'
            '<meta property="business:contact_data:street_address" '
            'content="Jl. Gatot Subroto Kav. 56">'
        )
        out = HomepageEnricher.extract_address(html, "")
        assert "Gatot Subroto" in out


class TestFooterRegex:
    def test_jl_pattern(self):
        text = "Alamat: Jl. Sudirman No. 45, Jakarta Selatan 12190"
        out = HomepageEnricher.extract_address("", text)
        assert "Sudirman" in out
        assert "12190" in out

    def test_ruko_pattern(self):
        text = "Kunjungi kami di Ruko Blok B-12, Kel. Kebon Jeruk"
        out = HomepageEnricher.extract_address("", text)
        assert "Ruko" in out
        assert "Kebon Jeruk" in out

    def test_kompleks_pattern(self):
        text = "Komp. Permata Hijau Blok C No. 5"
        out = HomepageEnricher.extract_address("", text)
        assert "Permata Hijau" in out

    def test_kelurahan_pattern(self):
        text = "Berlokasi di Kel. Cipete, Kec. Cilandak"
        out = HomepageEnricher.extract_address("", text)
        assert "Cipete" in out

    def test_first_match_wins(self):
        text = (
            "Kantor: Jl. Asia Afrika No. 100\n"
            "Cabang: Ruko D-12, Bandung"
        )
        out = HomepageEnricher.extract_address("", text)
        assert "Asia Afrika" in out


class TestPriority:
    def test_microdata_beats_og(self):
        html = (
            '<meta property="business:contact_data:street_address" '
            'content="Jl. OG-Street No. 1">'
            '<div itemprop="address">Jl. Microdata-Street No. 2</div>'
        )
        out = HomepageEnricher.extract_address(html, "")
        assert "Microdata" in out

    def test_microdata_beats_text(self):
        html = '<div itemprop="address">Jl. Structured No. 1</div>'
        text = "Jl. Footer No. 2"
        out = HomepageEnricher.extract_address(html, text)
        assert "Structured" in out


class TestEdgeCases:
    def test_empty(self):
        assert HomepageEnricher.extract_address("", "") is None

    def test_no_address(self):
        assert HomepageEnricher.extract_address(
            "<p>Just a paragraph</p>",
            "Some text but no address markers"
        ) is None

    def test_too_short_text_skipped(self):
        text = "Jl."  # 3 chars, too short
        assert HomepageEnricher.extract_address("", text) is None

    def test_too_long_text_skipped(self):
        text = "Jl. " + ("x" * 250)
        assert HomepageEnricher.extract_address("", text) is None
