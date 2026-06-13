"""
Backend LLM service — Groq + Gemini providers with template fallback.

API key NEVER exposed to frontend. Frontend calls /api/v1/ai/...
endpoints which proxy here.
"""
from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("clientfinder.llm")


@dataclass
class LLMResult:
    content: str
    provider: str
    model: str
    tokens_used: int = 0
    error: str | None = None
    raw: dict[str, Any] | None = None


class LLMError(Exception):
    pass


class BaseProvider(ABC):
    name: str
    model: str

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self.api_key = api_key
        self.model = model or self.model

    @abstractmethod
    async def complete(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> LLMResult: ...


class GroqProvider(BaseProvider):
    name = "groq"
    model = "llama-3.1-70b-versatile"
    base_url = "https://api.groq.com/openai/v1"

    async def complete(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> LLMResult:
        if not self.api_key or self.api_key.startswith("PLACEHOLDER"):
            raise LLMError("Groq API key not configured")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
        if resp.status_code != 200:
            raise LLMError(
                f"Groq HTTP {resp.status_code}: {resp.text[:300]}"
            )
        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
        except (KeyError, IndexError) as e:
            raise LLMError(f"Malformed Groq response: {e}") from e
        return LLMResult(
            content=content,
            provider=self.name,
            model=self.model,
            tokens_used=tokens,
            raw=data,
        )


class GeminiProvider(BaseProvider):
    name = "gemini"
    model = "gemini-1.5-flash"
    base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def complete(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> LLMResult:
        if not self.api_key or self.api_key.startswith("PLACEHOLDER"):
            raise LLMError("Gemini API key not configured")
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        payload: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            raise LLMError(
                f"Gemini HTTP {resp.status_code}: {resp.text[:300]}"
            )
        data = resp.json()
        try:
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)
        except (KeyError, IndexError) as e:
            raise LLMError(f"Malformed Gemini response: {e}") from e
        return LLMResult(
            content=content,
            provider=self.name,
            model=self.model,
            tokens_used=tokens,
            raw=data,
        )


# --- Provider registry ---

def _get_provider(name: str) -> BaseProvider:
    name = name.lower()
    if name == "groq":
        return GroqProvider(
            api_key=settings.llm_primary_api_key,
            model=settings.llm_primary_model,
        )
    if name == "gemini":
        return GeminiProvider(
            api_key=settings.llm_fallback_api_key,
            model=settings.llm_fallback_model,
        )
    raise LLMError(f"Unknown LLM provider: {name}")


async def complete(
    *,
    system: str,
    user: str,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    json_mode: bool = False,
    prefer_fallback: bool = False,
) -> LLMResult:
    """
    Try primary provider, then fallback. Returns the first success.
    Raises LLMError if all providers fail (caller can fall back to template).
    """
    order = (
        [settings.llm_fallback_provider, settings.llm_primary_provider]
        if prefer_fallback
        else [settings.llm_primary_provider, settings.llm_fallback_provider]
    )
    last_err: str | None = None
    for name in order:
        try:
            provider = _get_provider(name)
            return await provider.complete(
                system=system,
                user=user,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )
        except LLMError as e:
            logger.warning("Provider %s failed: %s", name, e)
            last_err = str(e)
    raise LLMError(f"All providers failed. Last: {last_err}")


def safe_parse_json(text: str) -> dict | list | None:
    """
    Extract JSON from LLM response. Handles ```json code blocks
    and bare JSON. Returns None if parsing fails.
    """
    if not text:
        return None
    # Strip code fences
    fence_match = re.search(
        r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL
    )
    if fence_match:
        text = fence_match.group(1)
    text = text.strip()
    # Try to find a JSON object/array within
    for start_ch, end_ch in [("{", "}"), ("[", "]")]:
        start = text.find(start_ch)
        if start == -1:
            continue
        end = text.rfind(end_ch)
        if end <= start:
            continue
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    # Last resort: try the whole string
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
