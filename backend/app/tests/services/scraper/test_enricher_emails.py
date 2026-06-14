"""
Unit tests for HomepageEnricher.extract_emails.

Covers:
- mailto: hrefs (priority 0)
- Body regex (priority 1)
- Deny-list filtering: noreply, admin, etc.
- Domain deny-list: example.com, yourdomain.com, sentry.io
- Query string / fragment stripping
- Dedupe + max-3 cap
"""
import pytest

from app.services.scraper.enricher import HomepageEnricher


class TestMailtoHref:
    def test_simple_mailto(self):
        html = '<a href="mailto:info@kliniksehat.com">Email</a>'
        assert HomepageEnricher.extract_emails(html) == ["info@kliniksehat.com"]

    def test_mailto_with_query(self):
        html = '<a href="mailto:hello@cafejkt.com?subject=Hi">Email</a>'
        out = HomepageEnricher.extract_emails(html)
        assert out == ["hello@cafejkt.com"]

    def test_mailto_with_fragment(self):
        html = '<a href="mailto:team@startup.id#contact">Email</a>'
        out = HomepageEnricher.extract_emails(html)
        assert out == ["team@startup.id"]


class TestBodyRegex:
    def test_plain_body_email(self):
        html = '<p>Hubungi kami di support@perusahaan.co.id</p>'
        out = HomepageEnricher.extract_emails(html)
        assert "support@perusahaan.co.id" in out

    def test_dotted_local_part(self):
        html = '<p>Email: budi.santoso@klinikgigi.id</p>'
        out = HomepageEnricher.extract_emails(html)
        assert "budi.santoso@klinikgigi.id" in out

    def test_plus_addressing(self):
        html = '<p>info+booking@restaurant.com</p>'
        out = HomepageEnricher.extract_emails(html)
        assert "info+booking@restaurant.com" in out


class TestDenyList:
    def test_noreply_filtered(self):
        html = "<p>Email: noreply@klinik.com</p>"
        assert HomepageEnricher.extract_emails(html) == []

    def test_no_reply_filtered(self):
        html = "<p>Email: no-reply@cafe.id</p>"
        assert HomepageEnricher.extract_emails(html) == []

    def test_admin_filtered(self):
        html = "<p>Admin: admin@perusahaan.com</p>"
        assert HomepageEnricher.extract_emails(html) == []

    def test_webmaster_filtered(self):
        html = "<p>webmaster@site.com</p>"
        assert HomepageEnricher.extract_emails(html) == []

    def test_example_com_filtered(self):
        html = "<p>test@example.com</p>"
        assert HomepageEnricher.extract_emails(html) == []

    def test_yourdomain_filtered(self):
        html = "<p>info@yourdomain.com</p>"
        assert HomepageEnricher.extract_emails(html) == []

    def test_sentry_filtered(self):
        html = "<p>alerts@sentry.io</p>"
        assert HomepageEnricher.extract_emails(html) == []

    def test_wordpress_filtered(self):
        html = "<p>footer@wordpress.com</p>"
        assert HomepageEnricher.extract_emails(html) == []

    def test_mailto_noreply_also_filtered(self):
        """mailto: with deny-listed local part also filtered."""
        html = '<a href="mailto:noreply@klinik.com">Email</a>'
        assert HomepageEnricher.extract_emails(html) == []


class TestPriority:
    def test_mailto_beats_body(self):
        html = (
            '<a href="mailto:hello@real.com">Email</a> '
            '<p>fallback: backup@other.com</p>'
        )
        out = HomepageEnricher.extract_emails(html)
        assert out[0] == "hello@real.com"
        assert "backup@other.com" in out


class TestDedupe:
    def test_same_email_in_mailto_and_body(self):
        html = (
            '<a href="mailto:info@klinik.com">Email</a> '
            '<p>or write to info@klinik.com</p>'
        )
        out = HomepageEnricher.extract_emails(html)
        assert out == ["info@klinik.com"]


class TestEdgeCases:
    def test_empty(self):
        assert HomepageEnricher.extract_emails("") == []

    def test_no_email(self):
        html = "<p>Just text, no email</p>"
        assert HomepageEnricher.extract_emails(html) == []

    def test_malformed_email_filtered(self):
        """'foo@' has no domain — regex won't match."""
        html = "<p>Email: foo@</p>"
        assert HomepageEnricher.extract_emails(html) == []
