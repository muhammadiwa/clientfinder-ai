"""
Sprint 1 / Phase 1.1 — Google Scout pre-filter unit tests.

25 tests covering 5 filter rules + integration. All checks are
pure string operations, no Playwright/httpx required.
"""
import pytest

from app.services.scraper.prefilter import (
    BLOG_PATH_PATTERNS,
    NON_BUSINESS_DOMAINS,
    SPAM_TLDS,
    has_blog_path,
    is_gibberish_title,
    is_listicle_title,
    is_non_business_domain,
    is_spam_tld,
    prefilter_google_result,
    prefilter_google_results,
)


# --- is_gibberish_title ---

class TestGibberishTitle:
    def test_real_business_title(self):
        assert not is_gibberish_title("Toko Sepatu Bandung Berkualitas")

    def test_actual_gibberish_3_short(self):
        """Genuinely gibberish: 3+ very-short words make the ratio > 50%."""
        assert is_gibberish_title("ab cd ef gh ij")

    def test_gibberish_with_numbers(self):
        # Real-world pattern from spammy sites
        assert is_gibberish_title("Xyz abc 123 def ghi")
        assert is_gibberish_title("Qwe rty uio pas dfg")

    def test_short_title_treated_as_gibberish(self):
        assert is_gibberish_title("Hi")
        assert is_gibberish_title("")
        assert is_gibberish_title("ab")  # too short

    def test_real_single_word_passes(self):
        """A single real word is not gibberish (Instagram, Tokopedia, etc.)"""
        assert not is_gibberish_title("Instagram")  # 9 chars, 1 word > 3
        assert not is_gibberish_title("Tokopedia")
        assert not is_gibberish_title("KlinikGigi")

    def test_business_with_qualifier(self):
        # Real-looking title with one short word
        assert not is_gibberish_title("Klinik Gigi Dr. Andi Spesialis Orthodonti")

    def test_acronyms_not_gibberish(self):
        # Short tokens mixed with real words
        assert not is_gibberish_title("PT. ABC Indonesia Manufacturer")


# --- is_spam_tld ---

class TestSpamTld:
    @pytest.mark.parametrize("tld", sorted(SPAM_TLDS))
    def test_blacklisted_tld(self, tld):
        assert is_spam_tld(f"https://example.{tld}/foo")

    def test_normal_tld(self):
        assert not is_spam_tld("https://example.com/foo")
        assert not is_spam_tld("https://example.id/foo")
        assert not is_spam_tld("https://example.co.id/foo")
        assert not is_spam_tld("https://clinic.example.org/foo")

    def test_real_audit_sample(self):
        """From the 2026-06-14 audit, gibberish sites used these TLDs."""
        assert is_spam_tld("http://fi.pk/ofason")
        assert is_spam_tld("http://kifmuzfuk.tt/otvongug")
        assert is_spam_tld("http://cugrij.to/nejouv")
        assert is_spam_tld("http://luammi.st/orega")

    def test_unparseable_url(self):
        """Empty URL has no TLD — not classified as spam, but caught
        earlier by the 'empty' check in prefilter_google_result."""
        assert not is_spam_tld("")


# --- is_non_business_domain ---

class TestNonBusinessDomain:
    @pytest.mark.parametrize("domain", [
        "tokopedia.com",
        "www.tokopedia.com",
        "shopee.co.id",
        "bukalapak.com",
        "lazada.co.id",
        "blibli.com",
        "instagram.com",
        "facebook.com",
        "youtube.com",
        "twitter.com",
        "x.com",
        "linkedin.com",
        "tiktok.com",
        "tokopedia.link",
    ])
    def test_blacklisted_domain(self, domain):
        assert is_non_business_domain(f"https://{domain}/some-path")

    def test_subdomain_match(self):
        """m.tokopedia.com, api.tokopedia.com, etc."""
        assert is_non_business_domain("https://m.tokopedia.com/foo")
        assert is_non_business_domain("https://api.instagram.com/oauth")

    def test_real_business_domain(self):
        assert not is_non_business_domain("https://ventelashoes.com/")
        assert not is_non_business_domain("https://hellosehat.com/")
        assert not is_non_business_domain("https://kliniksehat.co.id/")

    def test_unparseable_url_rejected(self):
        assert is_non_business_domain("not-a-url")


# --- is_listicle_title ---

class TestListicleTitle:
    @pytest.mark.parametrize("title", [
        "10 Daftar Toko Sepatu di Bandung Yang Direkomendasikan Untuk Mel",
        "11 Rekomendasi Tempat Belanja Sepatu di Kota Bandung",
        "7 Toko Sepatu di Bandung Terjangkau dan Lengkap",
        "5 Top Klinik Gigi Jakarta",
        "8 Best Klinik Kecantikan",
        "20 Kumpulan Restoran di Bandung",
        "3 List UMKM Jakarta",
        # Loose pattern: N + Indonesian business plural (no Daftar/Rekomendasi)
        "7 Toko Sepatu di Bandung",
        "10 Restoran Padang di Jakarta",
        "5 Klinik Gigi Recommended",
        "3 Apotek 24 Jam",
    ])
    def test_listicle_detected(self, title):
        assert is_listicle_title(title), f"Should detect listicle: {title!r}"

    def test_real_business_not_listicle(self):
        assert not is_listicle_title("Toko Sepatu Bandung Berkualitas")
        assert not is_listicle_title("Klinik Gigi Jakarta Selatan")
        assert not is_listicle_title("Restoran Padang Sederhana")

    def test_number_after_company_name_not_listicle(self):
        """'Toko Sepatu 10' (a name with a number) shouldn't match."""
        # The pattern requires number AT START
        assert not is_listicle_title("Toko Sepatu 10 Tahun Berdiri")

    def test_number_in_middle(self):
        assert not is_listicle_title("Dr. Andi 5 Star Clinic")


# --- has_blog_path ---

class TestBlogPath:
    @pytest.mark.parametrize("url", [
        "https://example.com/blog/2024/post",
        "https://example.com/articles/health",
        "https://example.com/article/123",
        "https://example.com/news/latest",
        "https://example.com/category/kesehatan",
        "https://example.com/tags/clinic",
        "https://example.com/search?q=clinic",
        "https://example.com/?p=12345",  # WP post ID
        "https://example.com/2024/03/15/post-title/",
        "https://example.com/2024/03/post",
    ])
    def test_blog_path_detected(self, url):
        assert has_blog_path(url), f"Should detect blog path: {url}"

    def test_real_business_path(self):
        assert not has_blog_path("https://ventelashoes.com/products/sepatu")
        assert not has_blog_path("https://kliniksehat.co.id/layanan")
        assert not has_blog_path("https://kliniksehat.co.id/")
        assert not has_blog_path("https://kliniksehat.co.id/kontak")

    def test_subdomain_not_blog(self):
        assert not has_blog_path("https://blog.example.com/")
        # Path is just /, no /blog/ segment
        assert not has_blog_path("https://example.com/")


# --- prefilter_google_result (integration of all 5 rules) ---

class TestPrefilterIntegration:
    def test_real_business_passes(self):
        keep, reason = prefilter_google_result(
            "Klinik Gigi Jakarta Selatan",
            "https://kliniksehat.co.id/layanan",
        )
        assert keep is True
        assert reason is None

    def test_empty_title(self):
        keep, reason = prefilter_google_result("", "https://example.com/")
        assert keep is False
        assert reason == "empty"

    def test_empty_url(self):
        keep, reason = prefilter_google_result("Klinik Gigi", "")
        assert keep is False
        assert reason == "empty"

    def test_audit_sample_caught_by_pipeline(self):
        """The 2026-06-14 audit samples: gibberish slips through on its
        own, but the spam_tld rule catches them when their URL has
        a spam TLD. Test the full prefilter_google_result pipeline."""
        samples = [
            ("Pum fozuc gonowwam toko sepatu bandung Fowfu fu umwi.", "http://fi.pk/ofason"),
            ("Cidvej zo mitu bos toko sepatu bandung Ihobaghij jema.", "http://kifmuzfuk.tt/otvongug"),
            ("Ode hetjijal huw re toko sepatu bandung Bunkorud gamipien.", "http://cugrij.to/nejouv"),
            ("Vapopowis feugeer toko sepatu bandung Wu vacul keciw pomiv.", "http://luammi.st/orega"),
        ]
        for title, url in samples:
            keep, reason = prefilter_google_result(title, url)
            assert keep is False, f"Audit sample NOT caught: {title!r}"
            # Whatever reason — gibberish, spam_tld, etc — we just care
            # that the result is dropped
            assert reason is not None

    def test_marketplace_blocked(self):
        keep, reason = prefilter_google_result(
            "Instagram",
            "https://www.instagram.com/forysport_bdg/",
        )
        assert keep is False
        assert reason == "non_business"

    def test_listicle_blocked(self):
        keep, reason = prefilter_google_result(
            "10 Daftar Toko Sepatu di Bandung Yang Direkomendasikan",
            "https://pergimulu.com/toko-sepatu-di-bandung/",
        )
        assert keep is False
        assert reason == "listicle"

    def test_blog_path_blocked(self):
        keep, reason = prefilter_google_result(
            "Tips Memilih Klinik Gigi",
            "https://healthblog.com/blog/2024/klinik-gigi-terbaik",
        )
        assert keep is False
        assert reason == "blog_path"

    def test_first_failing_rule_wins(self):
        """If multiple rules fail, the first one in the chain is reported.
        Spam TLD is checked before non_business, so spam TLD wins here."""
        keep, reason = prefilter_google_result(
            "Real Business Name",
            "https://example.tk/extra",
        )
        assert keep is False
        assert reason == "spam_tld"


# --- prefilter_google_results (batch) ---

class TestPrefilterBatch:
    def test_mixed_batch(self):
        results = [
            {"title": "Klinik Sehat Jakarta", "url": "https://kliniksehat.co.id/"},
            {"title": "10 Daftar Toko Sepatu", "url": "https://pergimulu.com/foo/"},
            {"title": "Instagram", "url": "https://instagram.com/x"},
            {"title": "ab cd ef gh ij", "url": "https://example.com/x"},  # gibberish
            {"title": "Real Business 2", "url": "https://ventelashoes.com/"},
        ]
        out = prefilter_google_results(results)
        assert len(out) == 5
        reasons = [r[1] for r in out]
        # Item 0: kept, Item 1: listicle (10 Daftar...), Item 2: non_business
        # (Instagram), Item 3: gibberish (ab cd ef gh ij), Item 4: kept
        assert reasons == [None, "listicle", "non_business", "gibberish", None]

    def test_empty_batch(self):
        assert prefilter_google_results([]) == []

    def test_all_kept(self):
        results = [
            {"title": "Klinik A Berkah", "url": "https://klinika.co.id/"},
            {"title": "Restoran B Jaya Sentosa", "url": "https://restob.web.id/"},
        ]
        out = prefilter_google_results(results)
        assert all(r[1] is None for r in out)
