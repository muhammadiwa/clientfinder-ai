"""
AI endpoints — proxy LLM calls (T5 Group 2).

Frontend calls /api/v1/ai/* to generate hooks + pain analysis.
API key stays server-side. This avoids exposing GROQ_API_KEY in
the browser bundle.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser
from app.services.analyzer.hook_generator import generate_hooks_for_prospect

logger = logging.getLogger("clientfinder.api.ai")

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/hooks/{prospect_id}")
async def generate_hooks(
    prospect_id: UUID,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Generate 3 outreach hooks for a prospect (T5, A29).

    Pipeline: load prospect + pains + tech → LLM (or template
    fallback) → save to DB → return hooks + source.

    Returns: {ok, source: 'llm'|'template', provider, hooks: [...]}
    """
    result = await generate_hooks_for_prospect(str(prospect_id))
    if not result.get("ok"):
        if result.get("error") == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prospect {prospect_id} not found",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "hook generation failed"),
        )
    return result


@router.post("/hooks-batch")
async def generate_hooks_batch(
    current_user: CurrentUser,
    payload: dict[str, list[str]],
) -> dict[str, Any]:
    """
    Generate hooks for multiple prospects sequentially.

    Payload: {"prospect_ids": ["uuid", ...]}
    """
    pids = payload.get("prospect_ids", [])
    if not isinstance(pids, list) or not pids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="prospect_ids must be a non-empty list",
        )
    results = []
    for pid in pids[:20]:  # cap
        r = await generate_hooks_for_prospect(pid)
        results.append(r)
    return {"ok": True, "results": results, "n": len(results)}


@router.get("/status")
async def ai_status_endpoint(current_user: CurrentUser) -> dict:
    """Check whether the LLM is configured (frontend polling)."""
    from app.core.config import settings
    from app.services.llm import get_active_providers

    primary_configured = bool(
        settings.llm_primary_api_key
        and not settings.llm_primary_api_key.startswith("PLACEHOLDER")
    )
    fallback_configured = bool(
        settings.llm_fallback_api_key
        and not settings.llm_fallback_api_key.startswith("PLACEHOLDER")
    )
    providers = get_active_providers()
    any_configured = any(p["configured"] for p in providers)
    return {
        "available": any_configured,
        "primary": {
            "provider": settings.llm_primary_provider,
            "model": settings.llm_primary_model,
            "configured": primary_configured,
        },
        "fallback": {
            "provider": settings.llm_fallback_provider,
            "model": settings.llm_fallback_model,
            "configured": fallback_configured,
        },
        "providers": providers,
    }


# --- LLM proxy endpoint (for frontend ai-analyzer.ts direct calls) ---

from typing import Annotated
from pydantic import BaseModel, Field


class CompleteRequest(BaseModel):
    system: str = Field(..., min_length=1, max_length=20000)
    user: str = Field(..., min_length=1, max_length=20000)
    temperature: float = Field(0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(2048, ge=50, le=8000)
    json_mode: bool = False
    provider: str | None = None
    prefer_fallback: bool = False


@router.post("/complete")
async def llm_complete(
    payload: CompleteRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Generic LLM completion proxy. Used by frontend ai-analyzer.ts
    for direct LLM calls (e.g. live email generation preview).

    API key stays server-side.
    """
    from app.services.llm import complete as llm_complete_fn, LLMError

    try:
        result = await llm_complete_fn(
            system=payload.system,
            user=payload.user,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            json_mode=payload.json_mode,
            prefer_fallback=payload.prefer_fallback,
        )
        return {
            "content": result.content,
            "provider": result.provider,
            "model": result.model,
            "tokens_used": result.tokens_used,
            "error": result.error,
        }
    except LLMError as e:
        return {
            "content": "",
            "provider": payload.provider or "unknown",
            "model": "",
            "tokens_used": 0,
            "error": str(e),
        }
