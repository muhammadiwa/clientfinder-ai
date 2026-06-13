"""
Analyst service — deterministic scoring + pain detection for T5.

A29 (analyst) = tech audit + pain detection + 0-100 scoring.
This module handles the deterministic parts (no LLM).
LLM hook generation is a separate module (see app.services.llm).
"""
from app.services.analyzer.scorer import (
    ScoreBreakdown,
    compute_score,
    grade_for_score,
)
from app.services.analyzer.pain_detector import (
    Pain,
    detect_pains,
)
from app.services.analyzer.website_checker import (
    WebsiteAudit,
    audit_website,
)
from app.services.analyzer.tech_auditor import (
    TechAudit,
    audit_tech,
)
from app.services.analyzer.orchestrator import enrich_prospect

__all__ = [
    "ScoreBreakdown",
    "compute_score",
    "grade_for_score",
    "Pain",
    "detect_pains",
    "WebsiteAudit",
    "audit_website",
    "TechAudit",
    "audit_tech",
    "enrich_prospect",
]
