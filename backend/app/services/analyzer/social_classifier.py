"""
T9.0 / Sprint 2 sub-task 2.4 — Social Signal Classifier.

Consumes a list of SocialPost (from Twitter or Threads scrapers)
and returns a list of detected signals. Each signal is a dict
ready to be persisted to the `signals` table.

Pipeline:
    1. List[SocialPost] from Twitter/Threads scrapers
    2. Build prompt via prompts.build_social_signal_classification_prompt
    3. Call LLM (via existing service) with the prompt
    4. Parse JSON response (with retry on parse fail)
    5. Validate + normalize (severity 0-100, kind in allowed list)
    6. Return list of signal dicts

The signals are then persisted by the pipeline integration
(Sprint 2 sub-task 2.5) and counted in the lead score
(signal_strength = number of detected signals).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.services.llm import LLMError, complete, safe_parse_json
from app.services.prompts import (
    SOCIAL_SIGNAL_KINDS,
    build_social_signal_classification_prompt,
)
from app.services.scraper.twitter import SocialPost

logger = logging.getLogger("clientfinder.analyzer.social")


# Cap on posts sent to the LLM in one call. LLM context windows
# are large but prompt cost grows linearly; 20 posts ≈ 4 KB of
# JSON which is a sweet spot for a single classification call.
MAX_POSTS_PER_CALL = 20


def _build_post_dicts(posts: list[SocialPost]) -> list[dict]:
    """Convert SocialPost objects to JSON-safe dicts for the LLM prompt."""
    out: list[dict] = []
    for p in posts[:MAX_POSTS_PER_CALL]:
        d = p.to_dict()
        # Trim to the fields the LLM actually needs (saves tokens)
        out.append({
            "i": len(out),  # explicit index for the LLM to reference
            "text": d["text"][:1000],  # cap each post to 1000 chars
            "author_handle": d["author_handle"],
            "url": d["url"],
            "language": d.get("language", "id"),
        })
    return out


def _validate_signal(s: dict) -> dict | None:
    """Normalize + validate a single LLM-output signal dict.

    Returns the dict on success, None if invalid.
    """
    if not isinstance(s, dict):
        return None
    kind = s.get("kind")
    if kind not in SOCIAL_SIGNAL_KINDS:
        return None
    try:
        severity = int(s.get("severity", 0))
    except (TypeError, ValueError):
        return None
    severity = max(0, min(100, severity))  # clamp
    evidence = (s.get("evidence_text") or "").strip()[:500]  # cap
    rationale = (s.get("rationale") or "").strip()[:200]
    return {
        "kind": kind,
        "severity": severity,
        "evidence_text": evidence,
        "rationale": rationale,
    }


async def classify_social_signals(
    posts: list[SocialPost],
) -> list[dict]:
    """Detect 'needs software' signals in a batch of social posts.

    Returns a list of validated signal dicts. Empty list = LLM
    found no relevant signals (or LLM call failed — in which case
    we log a warning and return []).

    Each dict has shape:
        {
            "kind": str,                  # one of SOCIAL_SIGNAL_KINDS
            "severity": int,              # 0-100
            "evidence_text": str,         # direct quote
            "rationale": str,            # why this is a signal
            "source": str,                # "twitter" | "threads" | ...
            "source_url": str,            # original post URL
            "weight": float,              # 0-1, derived from severity
        }
    """
    if not posts:
        return []
    # Cap batch size; if more, run multiple calls and concatenate
    if len(posts) > MAX_POSTS_PER_CALL:
        all_signals: list[dict] = []
        for i in range(0, len(posts), MAX_POSTS_PER_CALL):
            batch = posts[i:i + MAX_POSTS_PER_CALL]
            all_signals.extend(await classify_social_signals(batch))
        return all_signals

    post_dicts = _build_post_dicts(posts)
    system, user = build_social_signal_classification_prompt(post_dicts)

    # Map post index → source metadata (url, source name) for
    # attaching the right source_url to each detected signal.
    idx_to_post = {p_dict["i"]: p for p, p_dict in zip(posts, post_dicts)}

    logger.info(
        "Social signal classifier: %d posts, kinds=%s",
        len(posts), SOCIAL_SIGNAL_KINDS,
    )

    try:
        result = await complete(
            system=system,
            user=user,
            temperature=0.2,  # low — we want consistent extraction
            max_tokens=1500,
        )
    except LLMError as e:
        logger.warning("Social signal LLM call failed: %s", e)
        return []

    # LLMResult.content is the string; safe_parse_json expects str
    content = getattr(result, "content", result) if result else ""
    if not isinstance(content, str):
        content = str(content)
    parsed = safe_parse_json(content)
    if parsed is None:
        logger.warning("Social signal LLM returned non-JSON; skipping")
        return []
    if not isinstance(parsed, list):
        logger.warning("Social signal LLM returned non-list; skipping")
        return []

    # Validate + attach source metadata
    signals: list[dict] = []
    for s in parsed:
        normalized = _validate_signal(s)
        if normalized is None:
            continue
        # Attach source URL + name from the post index
        i = s.get("i")
        post = idx_to_post.get(i) if isinstance(i, int) else None
        if post is not None:
            normalized["source"] = post.url.split("/")[2] if "//" in post.url else "social"
            # source=hostname (x.com / threads.net); refined in pipeline
            # integration to canonical names
            if "threads.net" in post.url:
                normalized["source"] = "threads"
            elif "x.com" in post.url or "twitter.com" in post.url:
                normalized["source"] = "twitter"
            normalized["source_url"] = post.url
            # weight derived from severity: 0-100 → 0.0-1.0
            normalized["weight"] = round(normalized["severity"] / 100.0, 2)
        signals.append(normalized)

    logger.info(
        "Social signal classifier: %d → %d signals (%s)",
        len(posts), len(signals),
        [s["kind"] for s in signals],
    )
    return signals
