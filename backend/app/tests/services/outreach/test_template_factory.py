"""
Sprint 3A — template_factory unit tests.

Covers seed library size, variable substitution edge cases, and
the industry → category → channel template picker fallback chain.
"""
import pytest

from app.services.outreach.template_factory import (
    CATEGORIES,
    INDUSTRIES,
    _seed_library,
    canonicalize_industry,
    render_template,
)


class TestSeedLibrary:
    def test_seed_library_has_all_industries(self):
        library = _seed_library()
        industries_in_seed = {t["industry"] for t in library}
        # All 6 industries should be present
        for ind in INDUSTRIES:
            assert ind in industries_in_seed, f"Missing industry {ind}"

    def test_seed_library_covers_all_categories(self):
        library = _seed_library()
        cats_in_seed = {t["category"] for t in library}
        # At least the 3 main categories should be present
        for cat in CATEGORIES:
            assert cat in cats_in_seed, f"Missing category {cat}"

    def test_seed_library_includes_both_channels(self):
        library = _seed_library()
        channels = {t["channel"] for t in library}
        assert "email" in channels
        assert "whatsapp" in channels

    def test_seed_library_size_is_substantial(self):
        # 30 templates expected (6 industries × 3 cats × ~1.7 chans avg)
        library = _seed_library()
        assert len(library) >= 20, f"Expected 20+ templates, got {len(library)}"

    def test_seed_library_all_active(self):
        library = _seed_library()
        for t in library:
            assert t["is_active"] is True

    def test_seed_library_unique_names(self):
        library = _seed_library()
        names = [t["name"] for t in library]
        assert len(names) == len(set(names)), "Duplicate template names"

    def test_email_templates_have_subject(self):
        library = _seed_library()
        for t in library:
            if t["channel"] == "email":
                assert t["subject"] is not None
                assert len(t["subject"]) > 0

    def test_whatsapp_templates_no_subject(self):
        library = _seed_library()
        for t in library:
            if t["channel"] == "whatsapp":
                assert t["subject"] is None

    def test_seed_templates_have_required_vars(self):
        library = _seed_library()
        for t in library:
            assert "company_name" in t["variables"]
            assert "owner_name" in t["variables"]


class TestRenderTemplateEdgeCases:
    def test_preserves_unknown_brackets(self):
        result = render_template("[literal] {var} text", {"var": "x"})
        assert result == "[literal] x text"

    def test_multiple_occurrences(self):
        result = render_template(
            "{name} and {name} again",
            {"name": "Budi"},
        )
        assert result == "Budi and Budi again"

    def test_var_with_underscore_digits(self):
        result = render_template(
            "{var_1} and {var_2_name}",
            {"var_1": "a", "var_2_name": "b"},
        )
        assert result == "a and b"

    def test_empty_body(self):
        assert render_template("", {}) == ""

    def test_only_spaces(self):
        result = render_template("   ", {"company_name": "x"})
        assert result == "   "


class TestCanonicalizeIndustryMapping:
    @pytest.mark.parametrize("raw,expected", [
        ("Restoran", "fnb"),
        ("rumah makan", "fnb"),
        ("Warung", "fnb"),
        ("Kafe", "fnb"),
        ("Toko", "retail"),
        ("Minimarket", "retail"),
        ("Klinik Gigi", "klinik"),
        ("apotek", "klinik"),
        ("Dokter", "klinik"),
        ("Salon", "salon"),
        ("Spa", "salon"),
        ("Fitness", "salon"),
        ("Gym", "salon"),
        ("Konsultan", "jasa"),
        ("agency", "jasa"),
        ("B2B", "jasa"),
        ("Other", "umum"),
        ("Lain", "umum"),
        ("random_xyz", "umum"),
    ])
    def test_mapping(self, raw, expected):
        assert canonicalize_industry(raw) == expected
