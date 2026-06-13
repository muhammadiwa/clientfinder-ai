"""
Lead scoring — 5-factor deterministic formula (T5, A29, A10 v2).

5 factors per the existing `lead_scores` table schema:
  - signal_strength: how many external signals (signals table) we have
  - pain_severity: average pain severity × # pains
  - budget_indicator: industry + location proxy for budget
  - solution_fit: how well our services match the industry
  - timing_urgency: how recent the prospect is (freshness decay)

Total = weighted sum, clamped to [0, 100].
Grade: A (80+), B (60-79), C (40-59), D (0-39).

Weights tuned for Indonesian UMKM lead-gen:
  pain_severity 0.30 (most important — high pain = buy intent)
  signal_strength 0.20
  budget_indicator 0.15
  solution_fit 0.20
  timing_urgency 0.15

Total weights = 1.00.
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

# --- Factor weights ---
WEIGHTS = {
    "signal_strength": 0.20,
    "pain_severity": 0.30,
    "budget_indicator": 0.15,
    "solution_fit": 0.20,
    "timing_urgency": 0.15,
}

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


def compute_score(
    n_signals: int,
    pains: list[dict],
    industry: str | None,
    location_city: str | None,
    discovered_at: datetime,
) -> ScoreBreakdown:
    """Compute the full 5-factor score breakdown."""
    sig, sig_reasons = signal_strength_score(n_signals, len(pains))
    pain_s, pain_reasons = pain_severity_score(pains)
    budget, budget_reasons = budget_indicator_score(industry, location_city)
    fit, fit_reasons = solution_fit_score(industry, pains)
    timing, timing_reasons = timing_urgency_score(discovered_at)

    weighted = (
        sig * WEIGHTS["signal_strength"]
        + pain_s * WEIGHTS["pain_severity"]
        + budget * WEIGHTS["budget_indicator"]
        + fit * WEIGHTS["solution_fit"]
        + timing * WEIGHTS["timing_urgency"]
    )
    total = _clamp(weighted, 0, 100)
    grade = grade_for_score(total)

    reasoning = sig_reasons + pain_reasons + budget_reasons + fit_reasons + timing_reasons
    return ScoreBreakdown(
        signal_strength=round(sig, 1),
        pain_severity=round(pain_s, 1),
        budget_indicator=round(budget, 1),
        solution_fit=round(fit, 1),
        timing_urgency=round(timing, 1),
        total=round(total, 1),
        grade=grade,
        reasoning=reasoning,
    )
