"""
Orchestrator — runs the full analyst pipeline on a prospect (T5, A29).

Pipeline:
  1. Load prospect from DB
  2. Audit website (HTTP HEAD) — only if prospect has a URL
  3. Tech fingerprint (headers + optional HTML snippet)
  4. Detect pains (heuristic rules)
  5. Compute score (5-factor formula)
  6. Persist to DB (TechStack, PainPoint[], LeadScore, Prospect)
  7. Return summary dict

Adapter note: existing model schemas (lead.py, prospect.py) define
specific field names (category/severity-text for PainPoint, has_ssl
for TechStack). We map our internal detection model → these.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.activity import Activity
from app.models.lead import LeadScore
from app.models.prospect import PainPoint, Prospect, TechStack
from app.services.analyzer.pain_detector import detect_pains
from app.services.analyzer.scorer import compute_score
from app.services.analyzer.tech_auditor import audit_tech
from app.services.analyzer.website_checker import audit_website

logger = logging.getLogger("clientfinder.analyzer")


# --- Mappings from our detection model to existing DB schema ---

# Pain kind → category (the existing model uses category, not kind)
PAIN_CATEGORY_MAP: dict[str, str] = {
    "no_website": "growth",
    "stale_website": "technical",
    "no_ssl": "technical",
    "slow_site": "technical",
    "no_wa_business": "customer",
    "no_booking_system": "operational",
    "no_pos": "operational",
    "no_email": "growth",
    "no_phone": "growth",
    "no_gbp": "growth",
}

# Service label for evidence_quote (since model has no recommended_service)
SERVICE_LABEL_MAP: dict[str, str] = {
    "web_dev": "Layanan: Pembuatan website profesional",
    "perf_optimization": "Layanan: Performance optimization",
    "wa_business_setup": "Layanan: Setup WhatsApp Business",
    "booking_app": "Layanan: Sistem booking online",
    "pos_system": "Layanan: Sistem POS",
    "email_setup": "Layanan: Setup email profesional",
    "gmb_setup": "Layanan: Setup Google Business Profile",
}


def _severity_to_text(sev: int) -> str:
    if sev >= 70:
        return "high"
    if sev >= 40:
        return "medium"
    return "low"


async def enrich_prospect(
    prospect_id: str | UUID,
    *,
    html_snippet: str | None = None,
    has_wa_business: bool = False,
    has_booking_system: bool = False,
    has_pos: bool = False,
) -> dict[str, Any]:
    """
    Run the full analyst pipeline for one prospect.

    Returns a summary dict suitable for activity log + API response.
    """
    pid = UUID(prospect_id) if isinstance(prospect_id, str) else prospect_id

    async with AsyncSessionLocal() as db:
        prospect = (
            await db.execute(select(Prospect).where(Prospect.id == pid))
        ).scalar_one_or_none()
        if not prospect:
            logger.warning("enrich_prospect: prospect %s not found", pid)
            return {"ok": False, "error": "not_found"}

        # 1. Website audit
        site = await audit_website(prospect.website)

        # 2. Tech audit
        tech = audit_tech(site, html_snippet=html_snippet)

        # 3. Pain detection
        pains = detect_pains(
            website=prospect.website,
            industry=prospect.industry,
            location_city=prospect.location_city,
            has_phone=bool(prospect.phone),
            has_email=bool(prospect.email),
            has_wa_business=has_wa_business,
            has_booking_system=has_booking_system,
            has_pos=has_pos,
            response_time_ms=site.response_time_ms,
            has_ssl=site.has_ssl,
        )

        # 4. Score (7 factors + risk penalty, Sprint 1)
        n_signals = 0  # TODO: count from signals table (T9.0)
        # Sprint 1: read has_social from extra (T8.6 enrichment stores it)
        has_social = bool((prospect.raw_data or {}).get("social"))
        has_address = bool((prospect.raw_data or {}).get("location_address"))
        score = compute_score(
            n_signals=n_signals,
            pains=pains,
            industry=prospect.industry,
            location_city=prospect.location_city,
            discovered_at=prospect.discovered_at or datetime.now(timezone.utc),
            has_phone=bool(prospect.phone),
            has_email=bool(prospect.email),
            has_social=has_social,
            has_address=has_address,
            has_website=bool(prospect.website),
            source=prospect.source,
        )

        # 5. Persist TechStack (1:1, upsert)
        await _upsert_tech_stack(db, pid, tech, site)

        # 6. Replace pain_points
        await db.execute(delete(PainPoint).where(PainPoint.prospect_id == pid))
        for p in pains:
            category = PAIN_CATEGORY_MAP.get(p["kind"], "operational")
            sev_text = _severity_to_text(p["severity"])
            service_label = SERVICE_LABEL_MAP.get(
                p["recommended_service"],
                f"Layanan: {p['recommended_service']}",
            )
            # Combine title + description + service into one text
            quote_parts = [
                f"[{sev_text.upper()}] {p['title']}",
                p["description"],
                f"→ {service_label}",
            ]
            if p["evidence"]:
                quote_parts.append(
                    f"Bukti: {json.dumps(p['evidence'], ensure_ascii=False)}"
                )
            db.add(
                PainPoint(
                    prospect_id=pid,
                    category=category,
                    severity=sev_text,
                    description=p["description"],
                    source="heuristic_v1",
                    evidence_quote="\n".join(quote_parts),
                    detected_at=datetime.now(timezone.utc),
                )
            )

        # 7. Upsert LeadScore
        await _upsert_lead_score(
            db,
            pid,
            score,
            reasoning_text="; ".join(score.reasoning[:5]) or None,
        )

        # 8. Update Prospect top-level
        prospect.score_total = int(round(score.total))
        prospect.quality_grade = score.grade
        await db.commit()

        # 9. Activity log
        db.add(
            Activity(
                prospect_id=pid,
                user_id=prospect.owner_id,
                action="prospect_enriched",
                details={
                    "grade": score.grade,
                    "total_score": score.total,
                    "n_pains": len(pains),
                    "components": {
                        "signal_strength": score.signal_strength,
                        "pain_severity": score.pain_severity,
                        "budget_indicator": score.budget_indicator,
                        "solution_fit": score.solution_fit,
                        "timing_urgency": score.timing_urgency,
                        "contact_availability": score.contact_availability,
                        "personalization_quality": score.personalization_quality,
                        "risk_penalty": score.risk_penalty,
                    },
                },
            )
        )
        await db.commit()

        logger.info(
            "Enriched %s: %s (%.0f), %d pains",
            pid,
            score.grade,
            score.total,
            len(pains),
        )
        return {
            "ok": True,
            "prospect_id": str(pid),
            "grade": score.grade,
            "total_score": score.total,
            "n_pains": len(pains),
            "components": {
                "signal_strength": score.signal_strength,
                "pain_severity": score.pain_severity,
                "budget_indicator": score.budget_indicator,
                "solution_fit": score.solution_fit,
                "timing_urgency": score.timing_urgency,
                "contact_availability": score.contact_availability,
                "personalization_quality": score.personalization_quality,
                "risk_penalty": score.risk_penalty,
            },
            "reasoning": score.reasoning,
            "site": {
                "reachable": site.reachable,
                "has_ssl": site.has_ssl,
                "response_time_ms": site.response_time_ms,
                "status_code": site.status_code,
                "error": site.error,
            },
            "tech": {
                "cms": tech.cms,
                "cdn": tech.cdn,
                "framework": tech.framework,
                "server": tech.server,
            },
        }


async def _upsert_tech_stack(
    db: AsyncSession,
    pid: UUID,
    tech,  # TechAudit
    site,  # WebsiteAudit
) -> None:
    """Upsert the prospect's TechStack row (1:1) using existing schema fields."""
    existing = (
        await db.execute(
            select(TechStack).where(TechStack.prospect_id == pid)
        )
    ).scalar_one_or_none()

    # Build extra JSONB fields from our detection
    technologies: list[str] = []
    if tech.cms:
        technologies.append(f"cms:{tech.cms}")
    if tech.cdn:
        technologies.append(f"cdn:{tech.cdn}")
    if tech.framework:
        technologies.append(f"framework:{tech.framework}")
    if tech.server:
        technologies.append(f"server:{tech.server}")

    issues: list[str] = []
    if not site.reachable:
        issues.append(f"website_unreachable:{site.error or 'unknown'}")
    if site.reachable and not site.has_ssl:
        issues.append("no_ssl")
    if site.response_time_ms and site.response_time_ms > 3000:
        issues.append(f"slow_site:{site.response_time_ms}ms")
    if site.status_code and site.status_code >= 400:
        issues.append(f"http_{site.status_code}")

    fields = dict(
        cms=tech.cms,
        framework=tech.framework,
        programming_languages=[],
        hosting_provider=tech.cdn or tech.server,
        has_ssl=site.has_ssl if site.reachable else None,
        ssl_issuer=None,
        mobile_friendly=None,
        page_speed_score=None,
        technologies=technologies,
        security_headers={},
        issues=issues,
        audited_at=datetime.now(timezone.utc),
    )

    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        db.add(TechStack(prospect_id=pid, **fields))


async def _upsert_lead_score(
    db: AsyncSession,
    pid: UUID,
    score,  # ScoreBreakdown
    reasoning_text: str | None,
) -> None:
    """Upsert the prospect's LeadScore row (1:1)."""
    existing = (
        await db.execute(
            select(LeadScore).where(LeadScore.prospect_id == pid)
        )
    ).scalar_one_or_none()

    fields = dict(
        signal_strength=score.signal_strength,
        pain_severity=score.pain_severity,
        budget_indicator=score.budget_indicator,
        solution_fit=score.solution_fit,
        timing_urgency=score.timing_urgency,
        total_score=score.total,
        grade=score.grade,
        reasoning=reasoning_text,
        scored_at=datetime.now(timezone.utc),
    )

    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        db.add(LeadScore(prospect_id=pid, **fields))
