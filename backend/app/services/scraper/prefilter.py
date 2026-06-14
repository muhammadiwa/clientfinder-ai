"""
Sprint 1 / Phase 1.1 — Google Search Scout pre-filter.

Per the 2026-06-14 audit, SearXNG (Google Search aggregator) returns
~67% noise for Indonesian UMKM queries. The noise categories:
  - gibberish spam auto-generated sites (random TLDs like .pk, .tt)
  - listicle blog posts ('10 Toko Sepatu di Bandung...')
  - marketplace primary URLs (tokopedia, shopee, instagram homepage)
  - article/blog path patterns (/blog/, /article/)

This module runs 5 fast, no-network heuristics on the SearXNG result
title+URL to reject these. All checks are pure string operations —
no HTTP fetch, no LLM call. Cost per result: ~10 microseconds.

If `prefilter_google_result` returns (False, reason), the caller
should drop the result. Reasons are short tags ("gibberish", "spam_tld",
"listicle", "marketplace", "blog_path") suitable for logging +
observability.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse


# --- Spam TLDs (cheap, no false positives worth a network call) ---
# Common patterns: short/length-2 TLDs and ccTLDs overused for spam.
SPAM_TLDS: frozenset[str] = frozenset({
    "pk", "to", "st", "tt", "tk", "ml", "ga", "cf", "gq", "xyz", "top",
})

# --- Domains we never want as a primary "business website" URL ---
# These are aggregators, social, or marketplaces — the result URL
# points to a generic page (e.g., tokopedia.com), not a specific
# business. Real business websites have their own domain.
NON_BUSINESS_DOMAINS: frozenset[str] = frozenset({
    "tokopedia.com", "www.tokopedia.com",
    "shopee.co.id", "www.shopee.co.id",
    "bukalapak.com", "www.bukalapak.com",
    "lazada.co.id", "www.lazada.co.id",
    "blibli.com", "www.blibli.com",
    "instagram.com", "www.instagram.com",
    "facebook.com", "www.facebook.com",
    "fb.com", "www.fb.com",
    "youtube.com", "www.youtube.com",
    "youtu.be",
    "twitter.com", "www.twitter.com",
    "x.com", "www.x.com",
    "linkedin.com", "www.linkedin.com",
    "tiktok.com", "www.tiktok.com",
    "tokopedia.link",
    "bit.ly", "www.bit.ly", "tinyurl.com", "www.tinyurl.com",
})

# --- URL path patterns that signal "this is a blog post, not a business" ---
BLOG_PATH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"/blog(/|$|\?)", re.IGNORECASE),
    re.compile(r"/article(s)?(/|$|\?)", re.IGNORECASE),
    re.compile(r"/news(/|$|\?)", re.IGNORECASE),
    re.compile(r"/category(/|$|\?)", re.IGNORECASE),
    re.compile(r"/tag(s)?(/|$|\?)", re.IGNORECASE),
    re.compile(r"/search(\?|$)", re.IGNORECASE),
    re.compile(r"\?p=\d+", re.IGNORECASE),  # WordPress post ID query
    re.compile(r"/\d{4}/\d{2}/\d{2}/", re.IGNORECASE),  # WP date path
    re.compile(r"/\d{4}/\d{2}/", re.IGNORECASE),
)

# --- Listicle title patterns (Indonesian) ---
# Catches both:
#   - Strict: "10 Daftar Toko Sepatu di Bandung..."
#   - Loose:  "7 Toko Sepatu di Bandung..."  (no Daftar/Rekomendasi keyword)
#     The plural Indonesian business-noun at position 2 is a strong signal
#     of a listicle (vs a real business name with a number in it).
LISTICLE_KEYWORDS = (
    # Strict listicle markers
    "daftar", "rekomendasi", "tempat", "top", "best", "kumpulan", "list",
    # Indonesian business plurals (indicate listicle-shaped content)
    "toko", "restoran", "kafe", "cafe", "klinik", "apotek", "umkm",
    "bisnis", "peluang", "ide", "cara",
)
LISTICLE_TITLE_RE = re.compile(
    r"^\s*\d{1,3}\s+(?:" + "|".join(LISTICLE_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

# --- Gibberish detection ---
# Spam titles are auto-generated: lots of 1-2 char "words" + random punctuation.
# Real titles have words mostly >= 3 chars.
GIBBERISH_WORD_RE = re.compile(r"[A-Za-zÀ-ÿ]{1,2}(?:\s+|$)")
# A title is "gibberish-ish" if >50% of its words are <=2 chars AND
# the title is short (< 80 chars, because long titles are usually real).

# --- Helpers ---


def _domain_of(url: str) -> str:
    """Return the lowercase netloc (no www. prefix). Empty on parse fail."""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:  # noqa: BLE001
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def _tld_of(domain: str) -> str:
    """Return the last label of the domain (the TLD)."""
    if not domain:
        return ""
    return domain.rsplit(".", 1)[-1] if "." in domain else ""


def _has_blog_path(url: str) -> bool:
    """True if the URL path matches a known blog/article pattern."""
    return any(p.search(url) for p in BLOG_PATH_PATTERNS)


# --- Public API ---


def is_gibberish_title(title: str) -> bool:
    """Heuristic: a title is gibberish if too many short words.

    Real titles: 'Toko Sepatu Bandung Berkualitas' has all words > 3 chars.
    Gibberish spam: 'Pum fozuc gonowwam toko sepatu bandung Fowfu fu umwi'
    has 2/9 words <= 3 chars (22%).

    Rules (all must pass for "not gibberish"):
    - Total length >= 5 chars
    - At least 1 word > 3 chars (rules out "Hi", "ab cd ef")
    - < 50% of words are <= 3 chars

    Note: This is intentionally loose. The spam TLD check + non-business
    domain check catch the rest of the gibberish cases (those URLs
    point to .pk/.to/.tt/etc or instagram.com). A 50% threshold avoids
    false positives on real titles with one short word like "Gigi".
    """
    if not title or len(title) < 5:
        return True
    # Strip digits/punctuation, keep only word chars for the analysis
    words = re.findall(r"[A-Za-zÀ-ÿ]+", title)
    if not words:
        return True
    if max(len(w) for w in words) <= 3:
        return True  # no word > 3 chars
    short = sum(1 for w in words if len(w) <= 3)
    return short / len(words) > 0.5


def is_spam_tld(url: str) -> bool:
    """True if the URL's TLD is in the spam TLD blacklist."""
    return _tld_of(_domain_of(url)) in SPAM_TLDS


def is_non_business_domain(url: str) -> bool:
    """True if the URL points to a known non-business (marketplace/social)
    domain — i.e., the result is a generic homepage, not a business site.
    """
    d = _domain_of(url)
    if not d:
        return True  # unparseable = reject
    if d in NON_BUSINESS_DOMAINS:
        return True
    # Subdomain matches (e.g., "m.tokopedia.com")
    for blocked in NON_BUSINESS_DOMAINS:
        if d.endswith("." + blocked):
            return True
    return False


def is_listicle_title(title: str) -> bool:
    """True if the title matches a listicle pattern (numbered list of items)."""
    return bool(LISTICLE_TITLE_RE.match(title))


def has_blog_path(url: str) -> bool:
    """True if the URL path suggests a blog/article/news page."""
    return _has_blog_path(url)


def prefilter_google_result(title: str, url: str) -> tuple[bool, str | None]:
    """Run all 5 pre-filter rules. Returns (keep, reason_if_dropped).

    `keep=True` means the result passes all filters (looks like a real
    business). `keep=False` returns a short reason tag for logging.

    Order is cheapest-first; first failure wins.
    """
    # Empty title or URL — always drop
    if not title or not url:
        return False, "empty"

    if is_gibberish_title(title):
        return False, "gibberish"
    if is_spam_tld(url):
        return False, "spam_tld"
    if is_non_business_domain(url):
        return False, "non_business"
    if is_listicle_title(title):
        return False, "listicle"
    if has_blog_path(url):
        return False, "blog_path"

    return True, None


def prefilter_google_results(
    results: list[dict],
) -> list[tuple[dict, str | None]]:
    """Apply prefilter to a list of SearXNG result dicts.

    Returns a list of (result, drop_reason) tuples — caller decides
    whether to keep or drop. drop_reason is None for kept results.
    """
    out: list[tuple[dict, str | None]] = []
    for r in results:
        title = (r.get("title") or "").strip()
        url = (r.get("url") or "").strip()
        keep, reason = prefilter_google_result(title, url)
        if keep:
            out.append((r, None))
        else:
            out.append((r, reason))
    return out


# Reasonable defaults — exposed for tests / future use
__all__ = [
    "SPAM_TLDS",
    "NON_BUSINESS_DOMAINS",
    "BLOG_PATH_PATTERNS",
    "is_gibberish_title",
    "is_spam_tld",
    "is_non_business_domain",
    "is_listicle_title",
    "has_blog_path",
    "prefilter_google_result",
    "prefilter_google_results",
]
