"""
Lead scoring — 7-factor formula + risk penalty (Sprint 1 / T5 v3).

Aligns with the project brief's 7-component formula. The previous
5-factor version was a v1 placeholder; this version adds the 3
components that were missing:

  + contact_availability    0.10  phone/email/social/address present
  + personalization_quality  0.05  pain specificity + industry match
  - risk_penalty           0.20  bad data + risky source

  Original 5 (rebalanced to match brief):
  ~ signal_strength        0.10  external signals + pains (brief: online_activity)
  ~ pain_severity          0.30  avg severity (brief: need_signal)
  ~ budget_indicator       0.15  industry + location (brief: budget_potential)
  ~ solution_fit           0.15  service match (brief: business_fit)
  ~ timing_urgency         0.15  freshness (brief: urgency)

Total positive weights = 1.00. Formula:

    total = clamp(sum(weight * factor) - risk_penalty, 0, 100)

Grade thresholds (aligned with brief's 5-tier classification, using
the simpler A/B/C/D mapping — A=Hot, B=Warm, C=Cold, D=Ignore):
  80+ A (Hot Lead, 24h SLA)
  60+ B (Warm Lead, nurture)
  40+ C (Cold Lead, revisit)
  <40 D (Ignore)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable


# --- Grade thresholds (T9 playbook color map applied) ---
GRADE_THRESHOLDS = [
    (80.0, "A"),
    (60.0, "B"),
    (40.0, "C"),
    (0.0, "D"),
]

# --- Factor weights (per brief, Sprint 1 rebalance) ---
WEIGHTS = {
    "signal_strength": 0.08,
    "pain_severity": 0.25,
    "budget_indicator": 0.13,
    "solution_fit": 0.13,
    "timing_urgency": 0.13,
    "contact_availability": 0.08,
    "personalization_quality": 0.05,
    "tier": 0.05,           # Sprint 3B: SMB/Mid/Enterprise tier signal
    "industry_specificity": 0.05,  # Sprint 3B: deeper industry = better fit
    # Sum: 0.95 — leaves 0.05 headroom for future factors
}
# Recalibrate the assertion to match the new sum (0.95)
assert abs(sum(WEIGHTS.values()) - 0.95) < 1e-6, (
    f"WEIGHTS must sum to 0.95 (with 0.05 headroom for future factors), "
    f"got {sum(WEIGHTS.values())}"
)

# --- Risk penalty: source reputation (per R7 pragmatic-legal) ---
# google search results are noisy (R8 audit 2026-06-14: ~67% noise).
# Manual imports are assumed vetted. Maps = cleanest.
SOURCE_RISK_PENALTY = {
    "google": 10.0,         # noisy SearXNG aggregates
    "google_maps": 0.0,     # clean Playwright scrape
    "maps": 0.0,
    "manual": 2.0,
    "twitter": 5.0,         # TODO: real Twitter scraper (T9.0)
    "threads": 5.0,        # TODO: real Threads scraper (T9.0)
}

# Max risk penalty (per brief: -20)
RISK_PENALTY_MAX = 20.0

# Industries with high digital-pain + decent budget for our services
HIGH_FIT_INDUSTRIES = {
    "klinik gigi": 80,
    "klinik kecantikan": 80,
    "restoran": 70,
    "kafe": 70,
    "apotek": 75,
    "fnb": 70,
    "salon": 65,
    "spa": 65,
    "fitness": 60,
    "bengkel": 60,
    "laundry": 55,
    "minimarket": 55,
}

# Indonesian cities with active digital adoption (proxy for budget)
ACTIVE_MARKETS = {
    "jakarta": 70,
    "bandung": 65,
    "surabaya": 65,
    "yogyakarta": 60,
    "medan": 55,
    "semarang": 55,
    "makassar": 50,
    "denpasar": 55,
    "jabodetabek": 75,
}

# Freshness decay (older prospect = lower urgency)
FRESHNESS_DECAY_DAYS = 90
FRESHNESS_MIN_SCORE = 30.0


@dataclass
class ScoreBreakdown:
    """Detailed score components for UI display."""

    signal_strength: float
    pain_severity: float
    budget_indicator: float
    solution_fit: float
    timing_urgency: float
    contact_availability: float
    personalization_quality: float
    tier: float               # Sprint 3B
    industry_specificity: float  # Sprint 3B
    risk_penalty: float
    total: float
    grade: str
    reasoning: list[str] = field(default_factory=list)


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def grade_for_score(total: float) -> str:
    """Map a 0-100 total to A/B/C/D grade."""
    for threshold, grade in GRADE_THRESHOLDS:
        if total >= threshold:
            return grade
    return "D"


def signal_strength_score(
    n_signals: int,
    n_pains: int,
) -> tuple[float, list[str]]:
    """Score the signal/pain density for a prospect (0-100)."""
    if n_signals == 0 and n_pains == 0:
        return 30.0, ["No signals or pains — limited visibility"]
    # 1 signal = 20, 2 = 40, 3 = 60, 4 = 80, 5+ = 100
    sig = _clamp(n_signals * 20.0, 0, 100)
    # Bonus: more pains = stronger buy intent
    sig = _clamp(sig + n_pains * 5.0, 0, 100)
    reasons: list[str] = []
    if n_signals >= 3:
        reasons.append(f"{n_signals} signals — strong visibility")
    if n_pains >= 3:
        reasons.append(f"{n_pains} pain points — high buy intent")
    return sig, reasons


def pain_severity_score(
    pains: Iterable[dict],
) -> tuple[float, list[str]]:
    """Score based on the severity of detected pains (0-100)."""
    pains_list = list(pains)
    if not pains_list:
        return 20.0, ["No pain detected — prospect may already be digital"]
    severities = [int(p.get("severity", 0) or 0) for p in pains_list]
    avg = sum(severities) / len(severities)
    # Slight bump for # pains (more pains = more buying opportunities)
    score = _clamp(avg * 0.9 + len(pains_list) * 3.0, 0, 100)
    reasons = [
        f"{len(pains_list)} pain(s), avg severity {avg:.0f}",
    ]
    return score, reasons


def budget_indicator_score(
    industry: str | None,
    location_city: str | None,
) -> tuple[float, list[str]]:
    """Proxy for budget based on industry + location."""
    industry_key = (industry or "").lower().strip()
    location_key = (location_city or "").lower().strip()

    industry_score = 30.0  # baseline
    for key, val in HIGH_FIT_INDUSTRIES.items():
        if key in industry_key:
            industry_score = val
            break

    location_score = 30.0
    for key, val in ACTIVE_MARKETS.items():
        if key in location_key:
            location_score = val
            break

    # Combined: average weighted (industry 60% + location 40%)
    combined = _clamp(industry_score * 0.6 + location_score * 0.4, 0, 100)
    reasons = [
        f"Industry: {industry or 'unknown'} (score {industry_score:.0f})",
        f"Location: {location_city or 'unknown'} (score {location_score:.0f})",
    ]
    return combined, reasons


def solution_fit_score(
    industry: str | None,
    pains: list[dict],
) -> tuple[float, list[str]]:
    """How well our services match the prospect's needs."""
    industry_key = (industry or "").lower().strip()

    # Base: industry fit (we have services for all our ICP industries)
    base = 60.0
    for key in HIGH_FIT_INDUSTRIES:
        if key in industry_key:
            base = 85.0
            break

    # Bonus: matching pain to service mapping
    pain_kinds = {p.get("kind", "") for p in pains}
    matched_services: list[str] = []
    if "no_website" in pain_kinds or "stale_website" in pain_kinds:
        matched_services.append("web dev")
    if "no_booking_system" in pain_kinds or "manual_booking" in pain_kinds:
        matched_services.append("scheduling app")
    if "no_wa_business" in pain_kinds:
        matched_services.append("WhatsApp bot")
    if "no_pos" in pain_kinds:
        matched_services.append("POS system")
    if "no_gbp" in pain_kinds:
        matched_services.append("Google Business setup")
    if "slow_site" in pain_kinds:
        matched_services.append("performance optimization")

    fit_bonus = min(15, len(matched_services) * 5)
    final = _clamp(base + fit_bonus, 0, 100)
    reasons = [
        f"Industry fit: {industry or 'unknown'} (base {base:.0f})",
    ]
    if matched_services:
        reasons.append(f"Matched services: {', '.join(matched_services[:3])}")
    return final, reasons


def timing_urgency_score(
    discovered_at: datetime,
) -> tuple[float, list[str]]:
    """Freshness: newer leads = more urgent."""
    if discovered_at.tzinfo is None:
        discovered_at = discovered_at.replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - discovered_at).days
    if age_days <= 0:
        return 100.0, ["Discovered today — peak urgency"]
    if age_days <= 7:
        return 90.0, [f"Discovered {age_days}d ago — fresh"]
    if age_days <= 30:
        return 75.0, [f"Discovered {age_days}d ago — recent"]
    if age_days <= 90:
        return 55.0, [f"Discovered {age_days}d ago — aging"]
    # Linear decay from 90d onward, floored at FRESHNESS_MIN_SCORE
    score = max(
        FRESHNESS_MIN_SCORE,
        55.0 - (age_days - 90) * 0.5,
    )
    return _clamp(score, 0, 100), [
        f"Discovered {age_days}d ago — stale (decay applied)"
    ]


def contact_availability_score(
    has_phone: bool,
    has_email: bool,
    has_social: bool,
    has_website: bool,
    has_address: bool,
) -> tuple[float, list[str]]:
    """Sprint 1 / brief: 'Email/WA/LinkedIn tersedia' (max 10/100).

    A prospect we can't reach is worth less. Strong contact info
    across multiple channels = higher score. We accept partial
    coverage (only 1 channel is OK) but penalize zero-coverage.
    """
    channels: list[str] = []
    if has_phone:
        channels.append("phone")
    if has_email:
        channels.append("email")
    if has_social:
        channels.append("social")
    if has_website:
        channels.append("website")
    if has_address:
        channels.append("address")

    n = len(channels)
    if n == 0:
        return 0.0, ["No contact channels — unreachable"]
    if n == 1:
        return 40.0, [f"1 contact channel: {channels[0]}"]
    if n == 2:
        return 70.0, [f"2 contact channels: {', '.join(channels)}"]
    if n == 3:
        return 90.0, [f"3 contact channels: {', '.join(channels[:3])}"]
    return 100.0, [f"{n} contact channels available"]


def personalization_quality_score(
    pains: list[dict],
    industry: str | None,
) -> tuple[float, list[str]]:
    """Sprint 1 / brief: 'Ada insight spesifik untuk outreach' (max 5/100).

    Measures how much *specific* signal we have to personalize the
    opening message. Generic pains ("no website") score lower than
    specific pains ("no booking system + slow response 4.2s + manual
    WA handling"). 1-2 specific pains is enough for a good hook.
    """
    if not pains:
        return 10.0, ["No pains — generic outreach only"]

    # Specific pain kinds (concrete, actionable in a message) vs
    # generic (less personal).
    SPECIFIC_KINDS = frozenset({
        "no_booking_system", "no_wa_business", "no_pos",
        "slow_site", "stale_website", "no_ssl", "no_payment",
        "no_mobile_friendly", "has_console_errors",
    })
    GENERIC_KINDS = frozenset({
        "no_website",  # rare; if no site, we have nothing to audit
    })

    specific = sum(1 for p in pains if p.get("kind") in SPECIFIC_KINDS)
    generic = sum(1 for p in pains if p.get("kind") in GENERIC_KINDS)
    other = len(pains) - specific - generic

    # Score: more specific = better. Industry match is a small bonus
    industry_bonus = 10.0 if (industry and any(
        k in (industry or "").lower() for k in HIGH_FIT_INDUSTRIES
    )) else 0.0

    if specific >= 3:
        base = 90.0
    elif specific == 2:
        base = 75.0
    elif specific == 1:
        base = 50.0
    else:
        base = 20.0  # only generic/other pains

    base += industry_bonus
    base = _clamp(base, 0, 100)

    reasons = [f"{specific} specific, {generic} generic pain(s)"]
    if industry_bonus:
        reasons.append("Industry match — good hook material")
    return base, reasons


def risk_penalty_score(
    source: str | None,
    has_phone: bool,
    has_email: bool,
    has_industry: bool,
    has_website: bool,
) -> tuple[float, list[str]]:
    """Sprint 1 / brief: 'Data tidak valid, sumber rawan ToS, kontak
    tidak jelas' (max 20).

    Penalties (additive, capped at RISK_PENALTY_MAX):
      + source reputation  (e.g., google noisy = -10)
      + missing both phone AND email   (-8, hard to outreach)
      + missing industry (we can't score fit)  (-3)
      + no website (can't audit)             (-2)
    """
    penalties: list[tuple[float, str]] = []

    # Source reputation
    src_pen = SOURCE_RISK_PENALTY.get((source or "").lower(), 5.0)
    penalties.append(
        (src_pen, f"Source '{source or 'unknown'}' (reputation)")
    )

    # Contact info (both missing is bad)
    if not has_phone and not has_email:
        penalties.append((8.0, "No phone AND no email — hard to outreach"))

    # Industry unknown
    if not has_industry:
        penalties.append((3.0, "Industry unknown — can't score fit"))

    # No website
    if not has_website:
        penalties.append((2.0, "No website — can't audit"))

    total = sum(p for p, _ in penalties)
    capped = min(total, RISK_PENALTY_MAX)
    reasons = [f"-{p}: {r}" for p, r in penalties if p > 0]
    if capped < total:
        reasons.append(f"(capped at -{RISK_PENALTY_MAX})")
    return capped, reasons


# --- Tier scoring (Sprint 3B) ---


def tier_score(
    tier: str | None,
    tier_confidence: float = 0.0,
) -> tuple[float, list[str]]:
    """Sprint 3B: convert tier to a 0-100 score for the new
    'tier' factor in compute_score.

    Per the brief's UMKM-first design (Indonesia context):
    - SMB → highest score (most likely to need our help)
    - Mid → mid score (good fit)
    - Enterprise → lower score (often have internal IT)
    - Unknown → 50 (neutral)

    Confidence is a multiplier: low confidence → pull toward 50.
    """
    base = {
        "smb": 85.0,
        "mid": 65.0,
        "enterprise": 45.0,
        "unknown": 50.0,
    }.get(tier or "unknown", 50.0)
    # Confidence-weighted: pull toward 50 as confidence drops
    adjusted = base * tier_confidence + 50.0 * (1.0 - tier_confidence)
    adjusted = _clamp(adjusted, 0, 100)
    reasons: list[str] = []
    if tier:
        reasons.append(
            f"tier={tier} conf={tier_confidence:.2f} → {adjusted:.0f}"
        )
    else:
        reasons.append("tier unknown → 50")
    return adjusted, reasons


def industry_specificity_score(
    has_specific_industry: bool,
    industry_match_with_pains: bool = False,
) -> tuple[float, list[str]]:
    """Sprint 3B: a specific subcategory (e.g. 'klinik gigi')
    gives the orchestrator more hooks + better template
    matching than a generic 'klinik'.

    Score:
    - No specific subcategory: 40
    - Has specific subcategory: 75
    - Has specific subcategory AND matches the detected pains: 95
    """
    if has_specific_industry and industry_match_with_pains:
        return 95.0, ["Specific industry + pain-aligned"]
    if has_specific_industry:
        return 75.0, ["Specific industry subcategory"]
    return 40.0, ["Generic industry only"]


def compute_score(
    n_signals: int,
    pains: list[dict],
    industry: str | None,
    location_city: str | None,
    discovered_at: datetime,
    *,
    # Sprint 1 / brief: extra inputs for the 3 new factors
    has_phone: bool = False,
    has_email: bool = False,
    has_social: bool = False,
    has_address: bool = False,
    has_website: bool = False,
    source: str | None = None,
    # Sprint 3B: tier + industry specificity
    tier: str | None = None,
    tier_confidence: float = 0.0,
    has_specific_industry: bool = False,
    industry_match_with_pains: bool = False,
) -> ScoreBreakdown:
    """Compute the 9-factor score + risk penalty breakdown.

    Sprint 3B adds 2 new factors: tier (SMB/Mid/Enterprise) and
    industry_specificity (deeper classification).
    Sprint 1 has 7 factors. Weights redistribute to keep the
    sum at 0.95 (with 0.05 headroom for future factors).
    """
    sig, sig_reasons = signal_strength_score(n_signals, len(pains))
    pain_s, pain_reasons = pain_severity_score(pains)
    budget, budget_reasons = budget_indicator_score(industry, location_city)
    fit, fit_reasons = solution_fit_score(industry, pains)
    timing, timing_reasons = timing_urgency_score(discovered_at)
    contact, contact_reasons = contact_availability_score(
        has_phone, has_email, has_social, has_website, has_address,
    )
    personalization, personalization_reasons = personalization_quality_score(
        pains, industry,
    )
    # Sprint 3B: NEW
    tier_s, tier_reasons = tier_score(tier, tier_confidence)
    industry_spec_s, industry_spec_reasons = industry_specificity_score(
        has_specific_industry, industry_match_with_pains,
    )
    # BUG FIX (3rd carryover): use kwargs at the call site so
    # the 5th arg is unambiguously has_website, not bool(location_city).
    risk, risk_reasons = risk_penalty_score(
        source=source,
        has_phone=has_phone,
        has_email=has_email,
        has_industry=bool(industry),
        has_website=has_website,
    )

    weighted = (
        sig * WEIGHTS["signal_strength"]
        + pain_s * WEIGHTS["pain_severity"]
        + budget * WEIGHTS["budget_indicator"]
        + fit * WEIGHTS["solution_fit"]
        + timing * WEIGHTS["timing_urgency"]
        + contact * WEIGHTS["contact_availability"]
        + personalization * WEIGHTS["personalization_quality"]
        + tier_s * WEIGHTS["tier"]                            # Sprint 3B
        + industry_spec_s * WEIGHTS["industry_specificity"]   # Sprint 3B
    )
    total = _clamp(weighted - risk, 0, 100)
    grade = grade_for_score(total)

    reasoning = (
        sig_reasons
        + pain_reasons
        + budget_reasons
        + fit_reasons
        + timing_reasons
        + contact_reasons
        + personalization_reasons
        + tier_reasons
        + industry_spec_reasons
        + risk_reasons
    )
    return ScoreBreakdown(
        signal_strength=round(sig, 1),
        pain_severity=round(pain_s, 1),
        budget_indicator=round(budget, 1),
        solution_fit=round(fit, 1),
        timing_urgency=round(timing, 1),
        contact_availability=round(contact, 1),
        personalization_quality=round(personalization, 1),
        tier=round(tier_s, 1),                                # Sprint 3B
        industry_specificity=round(industry_spec_s, 1),       # Sprint 3B
        risk_penalty=round(risk, 1),
        total=round(total, 1),
        grade=grade,
        reasoning=reasoning,
    )
