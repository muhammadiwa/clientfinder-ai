"""
T9.0 / Sprint 2 sub-task 2.4 — Social Signal Classifier unit tests.

Covers pure-function _validate_signal and _build_post_dicts
plus the LLM prompt construction. The full async classify_social_signals
is tested via integration in test_social_pipeline.py.
"""
from datetime import datetime, timezone

import pytest

from app.services.analyzer.social_classifier import (
    MAX_POSTS_PER_CALL,
    _build_post_dicts,
    _validate_signal,
)
from app.services.prompts import (
    SOCIAL_SIGNAL_KINDS,
    build_social_signal_classification_prompt,
)
from app.services.scraper.twitter import SocialPost


def _make_post(i: int = 1, text: str = "Butuh developer React") -> SocialPost:
    return SocialPost(
        post_id=str(i),
        text=text,
        author_handle=f"user{i}",
        url=f"https://x.com/user{i}/status/{i}",
        timestamp=datetime(2026, 6, 14, 10, 0, tzinfo=timezone.utc),
        engagement={"likes": i * 3},
        language="id",
    )


class TestValidateSignal:
    def test_valid_signal(self):
        s = {
            "kind": "hiring_developer",
            "severity": 85,
            "evidence_text": "cari backend dev untuk fintech",
            "rationale": "explicit hire signal",
        }
        result = _validate_signal(s)
        assert result is not None
        assert result["kind"] == "hiring_developer"
        assert result["severity"] == 85
        assert result["evidence_text"] == "cari backend dev untuk fintech"

    def test_invalid_kind_rejected(self):
        s = {"kind": "nonexistent_kind", "severity": 80, "evidence_text": "x"}
        assert _validate_signal(s) is None

    def test_missing_kind_rejected(self):
        s = {"severity": 80, "evidence_text": "x"}
        assert _validate_signal(s) is None

    def test_non_dict_rejected(self):
        assert _validate_signal("not a dict") is None
        assert _validate_signal([1, 2, 3]) is None
        assert _validate_signal(None) is None

    def test_severity_clamped_to_range(self):
        for raw, expected in [
            (-50, 0),
            (0, 0),
            (50, 50),
            (100, 100),
            (150, 100),
        ]:
            s = {"kind": "need_software", "severity": raw, "evidence_text": "x"}
            result = _validate_signal(s)
            assert result is not None
            assert result["severity"] == expected, f"severity {raw} should clamp to {expected}"

    def test_non_numeric_severity_zeroed(self):
        s = {"kind": "need_software", "severity": "high", "evidence_text": "x"}
        # int("high") raises — caught, returns None
        assert _validate_signal(s) is None

    def test_evidence_text_capped_to_500(self):
        s = {
            "kind": "need_software",
            "severity": 80,
            "evidence_text": "x" * 1000,
        }
        result = _validate_signal(s)
        assert result is not None
        assert len(result["evidence_text"]) == 500

    def test_evidence_text_defaults_to_empty(self):
        s = {"kind": "need_software", "severity": 80}
        result = _validate_signal(s)
        assert result is not None
        assert result["evidence_text"] == ""


class TestBuildPostDicts:
    def test_caps_at_max_posts(self):
        posts = [_make_post(i) for i in range(30)]
        result = _build_post_dicts(posts)
        assert len(result) == MAX_POSTS_PER_CALL

    def test_passes_through_under_cap(self):
        posts = [_make_post(i) for i in range(5)]
        result = _build_post_dicts(posts)
        assert len(result) == 5
        # Index starts at 0
        assert [d["i"] for d in result] == [0, 1, 2, 3, 4]

    def test_truncates_long_text(self):
        long_text = "a" * 2000
        post = _make_post(text=long_text)
        result = _build_post_dicts([post])
        assert len(result[0]["text"]) == 1000

    def test_only_includes_llm_relevant_fields(self):
        result = _build_post_dicts([_make_post()])
        assert set(result[0].keys()) == {
            "i", "text", "author_handle", "url", "language",
        }


class TestSocialSignalKinds:
    def test_all_kinds_have_string_values(self):
        for kind in SOCIAL_SIGNAL_KINDS:
            assert isinstance(kind, str)
            assert len(kind) > 0

    def test_no_duplicate_kinds(self):
        assert len(SOCIAL_SIGNAL_KINDS) == len(set(SOCIAL_SIGNAL_KINDS))

    def test_includes_brief_signals(self):
        """Per brief: 5 social signal categories — all should be represented."""
        brief_signals = {
            "hiring_developer", "need_software", "need_automation",
            "need_ai", "need_website",
        }
        for sig in brief_signals:
            assert sig in SOCIAL_SIGNAL_KINDS, f"Missing brief signal: {sig}"


class TestBuildSocialSignalPrompt:
    def test_returns_system_and_user(self):
        posts = [
            {
                "i": 0,
                "text": "Butuh developer",
                "author_handle": "budi",
                "url": "https://x.com/budi/status/1",
                "language": "id",
            },
        ]
        system, user = build_social_signal_classification_prompt(posts)
        assert "social signal detector" in system.lower()
        assert "Butuh developer" in user
        assert "budi" in user
        # All kinds must be listed in the prompt
        for kind in SOCIAL_SIGNAL_KINDS:
            assert kind in user

    def test_empty_posts_still_valid_prompt(self):
        system, user = build_social_signal_classification_prompt([])
        assert system
        assert "0 post" in user
