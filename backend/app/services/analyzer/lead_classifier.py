"""
T9.0 / Sprint 3B — Lead Classification Upgrade.

Two classifiers:
  1. classify_tier() — heuristic tier (SMB / Mid / Enterprise)
     based on employee_count + revenue_estimate + signal density.
  2. classify_industry_deep() — LLM-based industry refinement.
     Takes the existing industry string + company_name + website
     snippet, returns a more specific subcategory (e.g. "klinik"
     → "klinik gigi" or "klinik kecantikan").

Both run cheaply:
  - tier is a pure function (no I/O)
  - industry deep is a single LLM call, only when invoked
    (via /classify endpoint or by the orchestrator when it
    detects an ambiguous industry)
"""
from __future__ import annotations

import logging
import re
from typing import Any

from app.services.llm import LLMError, complete, safe_parse_json

logger = logging.getLogger("clientfinder.analyzer.lead_classifier")

# --- Tier constants ---

TIER_SMB = "smb"
TIER_MID = "mid"
TIER_ENTERPRISE = "enterprise"
TIER_UNKNOWN = "unknown"

TIERS = [TIER_SMB, TIER_MID, TIER_ENTERPRISE, TIER_UNKNOWN]


# --- Tier heuristic ---

# Indonesia-UMKM-style revenue brackets. Revenue values come in
# as free-text strings (e.g. "Rp 50jt/bulan", "50000000",
# "Rp 1.2M/bulan"). We parse to monthly IDR where possible.
REVENUE_PATTERNS = [
    # "Rp 50jt/bulan" or "Rp 50 jt"
    (re.compile(r"rp\s*([\d.,]+)\s*jt", re.I), 1_000_000, "jt"),
    (re.compile(r"rp\s*([\d.,]+)\s*m", re.I), 1_000_000_000, "m"),  # juta
    # "Rp 1.2M" (interpret as juta, since M=miliar in ID but
    # could be ambiguous — fall through to other patterns)
    (re.compile(r"rp\s*([\d.,]+)\s*(miliar|m)", re.I), 1_000_000_000, "miliar"),
    # Bare numbers like "50000000"
    (re.compile(r"^\s*rp\s*([\d]{6,})\s*$", re.I), 1, "raw"),
]


def parse_revenue_idr(rev: str | None) -> int | None:
    """Parse a free-text revenue string to monthly IDR.
    Returns None if the input is None or unparseable.

    Number parsing is locale-aware: in ID, '.' is the thousands
    separator and ',' is the decimal (e.g. "Rp 1.200.000" = 1.2M).
    We normalize by:
      1. Replace ',' with '.' (so commas act as decimal point)
      2. Strip any remaining '.': they were thousands separators
    """
    if not rev:
        return None
    s = rev.strip()
    for pat, mult, kind in REVENUE_PATTERNS:
        m = pat.search(s)
        if m:
            raw = m.group(1)
            # Locale-aware: treat comma as decimal, strip dots
            # (which were thousands separators)
            normalized = raw.replace(",", ".").replace(".", "")
            try:
                n = float(normalized)
            except ValueError:
                continue
            # But wait — if the original had a single '.' and no
            # comma, it might be a decimal (e.g. "1.2M"). Re-parse:
            if "." in raw and "," not in raw:
                # Decimal interpretation
                try:
                    n = float(raw)
                except ValueError:
                    continue
            return int(n * mult)
    return None


def classify_tier(
    *,
    employee_count: int | None = None,
    revenue_estimate: str | None = None,
    n_signals: int = 0,
    n_pains: int = 0,
) -> dict[str, Any]:
    """Heuristic tier classification.

    Returns:
        {
            "tier": "smb" | "mid" | "enterprise" | "unknown",
            "confidence": 0.0-1.0,
            "reasoning": str,
        }

    Logic (per brief's UMKM-first design — Indonesia context):
      - Enterprise: employee_count >= 50 OR revenue >= 500jt/month
      - Mid:        employee_count 10-49 OR revenue 50-500jt/month
      - SMB:        employee_count <= 9 OR revenue < 50jt/month
      - Unknown:    no signal at all (operator fills in via UI)

    Signal density is a tie-breaker — high signals on a small
    business still classifies as SMB (they need our help more
    than a big enterprise that may have internal IT).
    """
    rev_idr = parse_revenue_idr(revenue_estimate)
    reasons: list[str] = []

    # Big wins: revenue
    if rev_idr is not None:
        if rev_idr >= 500_000_000:
            reasons.append(
                f"revenue {rev_idr/1_000_000:.0f}jt/month >= 500jt"
            )
            return {
                "tier": TIER_ENTERPRISE,
                "confidence": 0.85,
                "reasoning": "; ".join(reasons),
            }
        if rev_idr >= 50_000_000:
            reasons.append(
                f"revenue {rev_idr/1_000_000:.0f}jt/month in 50-500jt range"
            )
            tier = TIER_MID
        elif rev_idr > 0:
            reasons.append(
                f"revenue {rev_idr/1_000_000:.0f}jt/month < 50jt"
            )
            tier = TIER_SMB
        else:
            tier = TIER_UNKNOWN
    else:
        tier = TIER_UNKNOWN
        reasons.append("revenue unknown")

    # Employee count: cross-check
    if employee_count is not None:
        if employee_count >= 50:
            reasons.append(f"employees {employee_count} >= 50")
            tier = TIER_ENTERPRISE
        elif employee_count >= 10:
            reasons.append(f"employees {employee_count} in 10-49 range")
            # Only override if we don't have a conflicting revenue
            if tier not in (TIER_ENTERPRISE,):
                tier = TIER_MID
        else:
            reasons.append(f"employees {employee_count} < 10")
            if tier == TIER_UNKNOWN:
                tier = TIER_SMB

    # Confidence: based on how many signals we have
    data_points = sum([
        1 if rev_idr is not None else 0,
        1 if employee_count is not None else 0,
    ])
    confidence = min(1.0, 0.5 + 0.2 * data_points + 0.05 * (n_signals + n_pains))
    if tier == TIER_UNKNOWN:
        confidence = 0.0

    # If signals are very high (e.g. 3+), boost confidence in whichever
    # direction the existing tier points — operator filled something in
    if n_signals >= 3 and tier != TIER_UNKNOWN:
        confidence = min(1.0, confidence + 0.1)

    return {
        "tier": tier,
        "confidence": round(confidence, 2),
        "reasoning": "; ".join(reasons) or "insufficient data",
    }


# --- Industry deep classifier (LLM) ---

INDUSTRY_DEEP_SYSTEM = (
    "Anda adalah industry classifier untuk sales prospecting di Indonesia. "
    "Tugas: dari data bisnis (nama, deskripsi, industri yang sudah "
    "dikategorikan, snippet website), klasifikasikan industri yang LEBIH "
    "SPESIFIK. Output HARUS JSON valid."
)

INDUSTRY_DEEP_PROMPT_TEMPLATE = """\
# TUGAS

Klasifikasikan industri spesifik untuk bisnis berikut.
Industri saat ini (heuristik): {current_industry}
Subkategori yang valid: {valid_subkategori}

Bisnis:
- Nama: {company_name}
- Industri heuristik: {current_industry}
- Lokasi: {location}
- Snippet website: {website_snippet}
- Deskripsi (jika ada): {description}
- Owner / signal: {owner_name}

Output JSON dengan field:
- industry_specific: string (subkategori spesifik, e.g. "klinik gigi", "kafe specialty", "salon bridal")
- industry_category: salah satu dari {valid_subkategori}
- confidence: 0-100
- rationale: 1-2 kalimat kenapa

# OUTPUT (JSON, no other text)
"""


async def classify_industry_deep(
    *,
    company_name: str,
    current_industry: str | None,
    location: str | None = None,
    website_snippet: str | None = None,
    description: str | None = None,
    owner_name: str | None = None,
) -> dict[str, Any]:
    """LLM-based industry refinement.

    Returns:
        {
            "industry_specific": str,
            "industry_category": str,
            "confidence": 0-100,
            "rationale": str,
        }

    On any error returns the input industry as the answer
    (graceful degradation).
    """
    user = INDUSTRY_DEEP_PROMPT_TEMPLATE.format(
        current_industry=current_industry or "(unknown)",
        valid_subkategori=", ".join([
            "fnb (restoran/kafe/warung/rumah makan)",
            "retail (toko/minimarket/online shop)",
            "klinik (klinik/apotek/dokter/rumah sakit)",
            "salon (salon/spa/fitness/gym/barbershop)",
            "jasa (konsultan/agensi/B2B/service)",
            "umum (lainnya)",
        ]),
        company_name=company_name or "(no name)",
        location=location or "Indonesia",
        website_snippet=(website_snippet or "(no snippet)")[:500],
        description=(description or "(no description)")[:300],
        owner_name=owner_name or "(no owner)",
    )
    try:
        result = await complete(
            system=INDUSTRY_DEEP_SYSTEM,
            user=user,
            temperature=0.1,  # low — we want consistent classification
            max_tokens=300,
        )
    except LLMError as e:
        logger.warning("industry_deep LLM failed: %s", e)
        return {
            "industry_specific": current_industry or "unknown",
            "industry_category": current_industry or "umum",
            "confidence": 0,
            "rationale": f"LLM call failed: {e!s}",
        }

    # LLMResult.content is the string; safe_parse_json expects str
    content = getattr(result, "content", result) if result else ""
    if not isinstance(content, str):
        content = str(content)
    parsed = safe_parse_json(content)
    if not isinstance(parsed, dict):
        return {
            "industry_specific": current_industry or "unknown",
            "industry_category": current_industry or "umum",
            "confidence": 0,
            "rationale": "LLM returned non-JSON",
        }
    return {
        "industry_specific": str(
            parsed.get("industry_specific", current_industry or "unknown")
        )[:200],
        "industry_category": str(
            parsed.get("industry_category", current_industry or "umum")
        )[:100],
        "confidence": int(parsed.get("confidence", 0)),
        "rationale": str(parsed.get("rationale", ""))[:300],
    }


# --- Sprint 3B sub-task 3: persist to prospect (auto-classify helper) ---


async def classify_and_persist(
    db: Any,
    prospect: Any,
) -> dict[str, Any]:
    """Run tier + industry classifiers and persist the result to
    the prospect row. Idempotent — overwrites previous tier/industry.

    Designed to be called from the orchestrator's enrich step so
    the lead score has a real tier signal instead of the
    "unknown" default.

    On LLM failure: tier still gets persisted (heuristic, no LLM),
    industry_specific stays None.
    """
    from sqlalchemy import select
    from app.models.prospect import TechStack

    # Tier (heuristic, instant)
    n_signals = 0
    n_pains = 0
    try:
        from app.models.prospect import PainPoint, Signal
        n_signals = len(
            (
                await db.execute(
                    select(Signal).where(Signal.prospect_id == prospect.id)
                )
            ).scalars().all()
        )
        n_pains = len(
            (
                await db.execute(
                    select(PainPoint).where(PainPoint.prospect_id == prospect.id)
                )
            ).scalars().all()
        )
    except Exception:  # noqa: BLE001
        pass

    tier_result = classify_tier(
        employee_count=prospect.employee_count,
        revenue_estimate=prospect.revenue_estimate,
        n_signals=n_signals,
        n_pains=n_pains,
    )

    # Persist tier immediately (heuristic, no failure mode)
    prospect.tier = tier_result["tier"]
    prospect.tier_confidence = tier_result["confidence"]

    # Industry deep (LLM) — best-effort, never raises
    ind_result = {
        "industry_specific": "unknown",
        "industry_category": prospect.industry or "umum",
        "confidence": 0,
        "rationale": "skipped (no DB or no tech stack)",
    }
    try:
        tech = (
            await db.execute(
                select(TechStack).where(TechStack.prospect_id == prospect.id)
            )
        ).scalar_one_or_none()
        website_snippet = ""
        if tech:
            website_snippet = (
                (tech.extra_metadata or {}).get("page_title", "")
                or (tech.extra_metadata or {}).get("description", "")
            )
        ind_result = await classify_industry_deep(
            company_name=prospect.company_name or "",
            current_industry=prospect.industry,
            location=prospect.location_city,
            website_snippet=website_snippet,
            description=prospect.description,
            owner_name=prospect.owner_name,
        )
    except Exception as e:  # noqa: BLE001
        # LLM failures must not break the tier persistence —
        # operator can re-classify later via the manual endpoint
        logger.warning(
            "classify_and_persist: industry LLM failed for %s: %s",
            prospect.id, e,
        )
    # Persist industry_specific only if LLM was confident enough
    if ind_result["industry_specific"] and ind_result["industry_specific"] != "unknown":
        if ind_result.get("confidence", 0) >= 50:
            prospect.industry_specific = ind_result["industry_specific"][:255]
    await db.commit()
    return {
        "tier": tier_result,
        "industry": ind_result,
    }
