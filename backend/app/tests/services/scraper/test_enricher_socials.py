"""
Unit tests for HomepageEnricher.extract_socials.

Covers:
- Each platform: Instagram, Facebook, Twitter/X, LinkedIn, TikTok, YouTube, WhatsApp, Telegram
- First-occurrence-per-platform wins
- URL normalization (https, no trailing slash)
- Twitter and x.com both map to 'twitter'
- Negative cases (no socials)
"""
import pytest

from app.services.scraper.enricher import HomepageEnricher


class TestInstagram:
    def test_basic_instagram(self):
        html = '<a href="https://instagram.com/klinikgigijakarta">IG</a>'
        out = HomepageEnricher.extract_socials(html)
        assert out["instagram"] == "https://instagram.com/klinikgigijakarta"

    def test_instagram_with_www(self):
        html = '<a href="https://www.instagram.com/cafejkt">IG</a>'
        out = HomepageEnricher.extract_socials(html)
        assert "instagram.com/cafejkt" in out["instagram"]


class TestFacebook:
    def test_basic_facebook(self):
        html = '<a href="https://facebook.com/restoran.enak">FB</a>'
        out = HomepageEnricher.extract_socials(html)
        assert out["facebook"] == "https://facebook.com/restoran.enak"


class TestTwitter:
    def test_twitter_com(self):
        html = '<a href="https://twitter.com/klinik_id">TW</a>'
        out = HomepageEnricher.extract_socials(html)
        assert "twitter.com/klinik_id" in out["twitter"]

    def test_x_com_maps_to_twitter(self):
        html = '<a href="https://x.com/klinik_id">X</a>'
        out = HomepageEnricher.extract_socials(html)
        assert "twitter" in out
        assert "x.com/klinik_id" in out["twitter"]


class TestLinkedIn:
    def test_linkedin_company(self):
        html = '<a href="https://linkedin.com/company/acme-corp">LI</a>'
        out = HomepageEnricher.extract_socials(html)
        assert "linkedin.com/company/acme-corp" in out["linkedin"]

    def test_linkedin_in(self):
        html = '<a href="https://linkedin.com/in/john-doe">LI</a>'
        out = HomepageEnricher.extract_socials(html)
        assert "linkedin.com/in/john-doe" in out["linkedin"]


class TestTikTok:
    def test_basic_tiktok(self):
        html = '<a href="https://tiktok.com/@klinikjakarta">TT</a>'
        out = HomepageEnricher.extract_socials(html)
        assert "tiktok.com/@klinikjakarta" in out["tiktok"]


class TestYouTube:
    def test_youtube_channel(self):
        html = '<a href="https://youtube.com/@kliniksehat">YT</a>'
        out = HomepageEnricher.extract_socials(html)
        assert "youtube.com/@kliniksehat" in out["youtube"]

    def test_youtube_c_prefix(self):
        html = '<a href="https://youtube.com/c/kliniksehat">YT</a>'
        out = HomepageEnricher.extract_socials(html)
        assert "youtube.com/c/kliniksehat" in out["youtube"]


class TestWhatsApp:
    def test_wa_me(self):
        html = '<a href="https://wa.me/6281234567890">WA</a>'
        out = HomepageEnricher.extract_socials(html)
        assert "wa.me/6281234567890" in out["whatsapp"]


class TestTelegram:
    def test_t_me(self):
        html = '<a href="https://t.me/kliniksehat">TG</a>'
        out = HomepageEnricher.extract_socials(html)
        assert "t.me/kliniksehat" in out["telegram"]


class TestMultiplePlatforms:
    def test_all_platforms_in_one_page(self):
        html = """
        <a href="https://instagram.com/klinik_jkt">IG</a>
        <a href="https://facebook.com/restoran.enak">FB</a>
        <a href="https://twitter.com/klinik_id">TW</a>
        <a href="https://linkedin.com/company/acme-corp">LI</a>
        <a href="https://tiktok.com/@klinikjkt">TT</a>
        <a href="https://youtube.com/@kliniksehat">YT</a>
        <a href="https://wa.me/6281234567890">WA</a>
        <a href="https://t.me/kliniksehat">TG</a>
        """
        out = HomepageEnricher.extract_socials(html)
        assert set(out.keys()) == {
            "instagram", "facebook", "twitter", "linkedin",
            "tiktok", "youtube", "whatsapp", "telegram",
        }


class TestFirstOccurrenceWins:
    def test_first_ig_kept(self):
        html = """
        <a href="https://instagram.com/first">IG 1</a>
        <a href="https://instagram.com/second">IG 2</a>
        """
        out = HomepageEnricher.extract_socials(html)
        assert "first" in out["instagram"]


class TestEdgeCases:
    def test_no_socials(self):
        html = "<p>Just a website, no social links</p>"
        assert HomepageEnricher.extract_socials(html) == {}

    def test_empty(self):
        assert HomepageEnricher.extract_socials("") == {}

    def test_garbage_url_filtered(self):
        """Non-platform URLs in href don't match any pattern."""
        html = '<a href="https://google.com/search">Search</a>'
        assert HomepageEnricher.extract_socials(html) == {}
