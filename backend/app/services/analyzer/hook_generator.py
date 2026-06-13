"""
Hook generation — uses LLM (Groq + Gemini fallback) with template
fallback. Used by the analyst pipeline to generate 3 outreach angles
per prospect.

If no LLM key is configured OR both providers fail, falls back to
template hooks generated from the prospect's pain points. This
ensures the system is testable end-to-end without API keys.
"""
from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.lead import Hook
from app.models.prospect import Prospect
from app.services.llm import LLMError, complete, safe_parse_json
from app.services.prompts import build_hook_prompt

logger = logging.getLogger("clientfinder.analyzer.hooks")


async def generate_hooks_for_prospect(
    prospect_id: str | UUID,
    *,
    replace_existing: bool = True,
) -> dict[str, Any]:
    """
    Generate 3 outreach hooks for a prospect.

    Pipeline:
      1. Load prospect + pains + tech_stack from DB
      2. Build prompt
      3. Try LLM (Groq + Gemini fallback)
      4. On LLM failure → template fallback (works always)
      5. Save hooks to DB
      6. Return summary

    Returns a dict with hooks + source ('llm' or 'template').
    """
    pid = UUID(prospect_id) if isinstance(prospect_id, str) else prospect_id

    async with AsyncSessionLocal() as db:
        prospect = (
            await db.execute(select(Prospect).where(Prospect.id == pid))
        ).scalar_one_or_none()
        if not prospect:
            return {"ok": False, "error": "not_found"}

        # Load pain_points (injected into prompt)
        from app.models.prospect import PainPoint, TechStack

        pains = (
            (
                await db.execute(
                    select(PainPoint)
                    .where(PainPoint.prospect_id == pid)
                    .order_by(PainPoint.severity.desc())
                )
            )
            .scalars()
            .all()
        )
        pains_dict = [
            {
                "kind": p.category,
                "severity": p.severity,
                "title": (p.evidence_quote or "").split("\n")[0][:100],
                "description": p.description,
            }
            for p in pains
        ]

        tech = (
            await db.execute(
                select(TechStack).where(TechStack.prospect_id == pid)
            )
        ).scalar_one_or_none()
        tech_dict = (
            {
                "cms": tech.cms,
                "framework": tech.framework,
                "hosting_provider": tech.hosting_provider,
                "has_ssl": tech.has_ssl,
                "page_speed_score": tech.page_speed_score,
                "issues": tech.issues,
            }
            if tech
            else None
        )

        # Try LLM
        hooks, source, provider, error = await _try_llm_hooks(
            prospect, pains_dict, tech_dict
        )

        # Fallback to template if LLM failed
        if not hooks:
            logger.info(
                "Falling back to template hooks for %s: %s",
                pid,
                error,
            )
            hooks = _template_hooks(prospect, pains_dict)
            source = "template"

        # Save hooks (replace existing)
        if replace_existing:
            await db.execute(delete(Hook).where(Hook.prospect_id == pid))
        for h in hooks:
            db.add(
                Hook(
                    prospect_id=pid,
                    hook_text=h["hook_text"],
                    audit_finding=h.get("audit_finding", ""),
                    recommended_service=h.get("recommended_service", ""),
                    confidence=h.get("confidence", 0.5),
                    is_used="false",
                )
            )
        await db.commit()

        logger.info(
            "Generated %d hooks for %s via %s (provider=%s)",
            len(hooks),
            pid,
            source,
            provider or "n/a",
        )
        return {
            "ok": True,
            "prospect_id": str(pid),
            "source": source,
            "provider": provider,
            "hooks": hooks,
            "error": error,
        }


async def _try_llm_hooks(
    prospect: Prospect,
    pains: list[dict],
    tech: dict | None,
) -> tuple[list[dict], str, str | None, str | None]:
    """Try LLM-based hook generation. Returns (hooks, source, provider, error)."""
    system, user = build_hook_prompt(
        company_name=prospect.company_name,
        industry=prospect.industry,
        location=prospect.location_city,
        website=prospect.website,
        pains=pains,
        tech=tech,
    )
    try:
        result = await complete(
            system=system,
            user=user,
            temperature=0.4,
            max_tokens=1500,
            json_mode=True,
        )
    except LLMError as e:
        return [], "template", None, str(e)

    parsed = safe_parse_json(result.content)
    if not parsed or not isinstance(parsed, dict) or "hooks" not in parsed:
        return [], "template", result.provider, "Failed to parse JSON"

    hooks_raw = parsed["hooks"]
    if not isinstance(hooks_raw, list):
        return [], "template", result.provider, "hooks not a list"

    # Normalize to our schema
    hooks = []
    for h in hooks_raw[:3]:  # Cap at 3
        if not isinstance(h, dict):
            continue
        hooks.append(
            {
                "audit_finding": str(h.get("audit_finding", ""))[:500],
                "hook_text": str(h.get("hook_text", ""))[:500],
                "recommended_service": str(
                    h.get("recommended_service", "")
                )[:100],
                "confidence": float(h.get("confidence", 0.5)),
            }
        )
    if not hooks:
        return [], "template", result.provider, "No hooks in response"
    return hooks, "llm", result.provider, None


def _template_hooks(
    prospect: Prospect,
    pains: list[dict],
) -> list[dict]:
    """
    Generate 3 hooks from templates + prospect data + pains.

    Works without any LLM key. Less personal than LLM but
    still useful for testing the UI.
    """
    company = prospect.company_name
    location = prospect.location_city or ""
    industry = prospect.industry or "bisnis Anda"

    # Pick top 2 pains by severity
    sorted_pains = sorted(
        pains, key=lambda p: int(p.get("severity", 0) or 0), reverse=True
    )
    top_pains = sorted_pains[:2]

    # 1. Website-less hook
    if any(p.get("kind") == "growth" for p in top_pains):
        return [
            {
                "audit_finding": f"{company} belum punya website yang terdeteksi online",
                "hook_text": (
                    f"Halo tim {company}! Saya perhatikan bisnis Anda di "
                    f"{location} belum punya website. 70% pelanggan Indonesia "
                    "sekarang cari bisnis lewat Google dulu. Mau diskusi 15 menit?"
                ),
                "recommended_service": "web_dev",
                "confidence": 0.85,
            },
            {
                "audit_finding": f"Bisnis {industry} di {location} umumnya punya Google Business Profile",
                "hook_text": (
                    f"Selamat pagi! Saya lihat {company} belum terdaftar di "
                    "Google Maps / Google Business. Itu free dan langsung "
                    "naikkan visibility 3x lipat. Mau saya bantu setup?"
                ),
                "recommended_service": "gmb_setup",
                "confidence": 0.78,
            },
            {
                "audit_finding": f"Website kompetitor {industry} di area {location} sudah online",
                "hook_text": (
                    f"Halo, saya cek beberapa bisnis {industry} di sekitar "
                    f"{location}. Kompetitor Anda sudah punya website modern. "
                    "Mau tau apa yang mereka lakuin yang Anda belum?"
                ),
                "recommended_service": "web_dev",
                "confidence": 0.72,
            },
        ]

    # 2. Has website but missing digital features
    if any(p.get("kind") in ("customer", "operational") for p in top_pains):
        sev = top_pains[0].get("severity", 50)
        return [
            {
                "audit_finding": f"Tidak ada WhatsApp Business di website {company}",
                "hook_text": (
                    f"Halo tim {company}! Saya cek website Anda — bagus "
                    "sudah online, tapi belum ada link WhatsApp Business. "
                    "Itu channel #1 customer service di Indonesia. Mau setup 5 menit?"
                ),
                "recommended_service": "wa_business_setup",
                "confidence": 0.80,
            },
            {
                "audit_finding": f"Booking system manual untuk bisnis {industry}",
                "hook_text": (
                    f"Selamat pagi {company}! Saya analisis online presence "
                    f"Anda — bisnis {industry} dengan booking system "
                    "otomatis biasanya naik 40% lebih efisien. Mau diskusi?"
                ),
                "recommended_service": "booking_app",
                "confidence": 0.74,
            },
            {
                "audit_finding": f"SSL/security issue di website {company}",
                "hook_text": (
                    f"Halo, browser sekarang nampilkan 'Not Secure' untuk "
                    f"website tanpa SSL. Saya cek {company} belum pakai HTTPS. "
                    "Itu trust killer — pelanggan kabur 80% lebih banyak. "
                    "Mau saya bantu fix?"
                ),
                "recommended_service": "web_dev",
                "confidence": 0.82,
            },
        ]

    # 3. Default: identity hook
    return [
        {
            "audit_finding": f"{company} ada di list scout kami",
            "hook_text": (
                f"Halo tim {company}! Saya analyst dari ClientFinder, "
                f"kami menganalisis {industry} di area {location}. "
                "Mau tau insight digital yang bisa naikkan bisnis Anda?"
            ),
            "recommended_service": "consultation",
            "confidence": 0.60,
        },
        {
            "audit_finding": f"{company} punya digital presence yang bisa dioptimize",
            "hook_text": (
                f"Selamat pagi! Saya lihat {company} sudah punya online "
                "presence. Beberapa optimasi yang saya temukan bisa naikkan "
                "konversi 2-3x. Mau saya share report-nya?"
            ),
            "recommended_service": "consultation",
            "confidence": 0.55,
        },
        {
            "audit_finding": f"Industry trend {industry} 2026",
            "hook_text": (
                f"Halo, saya riset trend {industry} 2026 di {location}. "
                f"Ada 3 insight yang relevan untuk {company}. Mau saya kirim?"
            ),
            "recommended_service": "consultation",
            "confidence": 0.50,
        },
    ]
