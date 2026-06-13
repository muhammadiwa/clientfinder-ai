"""
LLM service — generic OpenAI-compatible provider + Gemini (non-OAI).

Architecture (per user request): all providers are configured in .env,
fully toggleable, any can be primary. Supports:
  - OpenAI-compatible APIs (OpenAI, Groq, Together, OpenRouter, custom)
  - Gemini (Google AI Studio) — uses its own protocol
  - Template fallback (always works, no key needed)

Provider config sources (in priority order):
  1. LLM_PROVIDERS_JSON env var (JSON array, recommended for 3+ providers)
  2. LLM_PRIMARY_* + LLM_FALLBACK_* (simple 2-slot config, backward compat)

Each provider entry:
  {
    "name": "tokenrouter",            // unique identifier for logs
    "type": "openai-compatible",     // "openai-compatible" or "gemini"
    "base_url": "https://...",        // for OAI-compatible only
    "api_key": "sk-...",              // any string (can be "ollama" for local)
    "model": "MiniMax-M3",
    "enabled": true,                  // toggleable
    "order": 1,                      // 1 = primary, 2 = fallback, 3+ = chain
    "display_name": "TokenRouter"    // optional human label
  }
"""
from __future__ import annotations

import json
import logging
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
    """Abstract base — all LLM providers implement `complete()`."""

    def __init__(
        self,
        name: str,
        api_key: str,
        model: str,
        **kwargs: Any,
    ) -> None:
        self.name = name
        self.api_key = api_key
        self.model = model

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


class OpenAICompatibleProvider(BaseProvider):
    """
    Generic provider for any OpenAI-compatible chat completions API.

    Tested with:
      - OpenAI (https://api.openai.com/v1)
      - Groq (https://api.groq.com/openai/v1)
      - OpenRouter (https://openrouter.ai/api/v1)
      - TokenRouter (https://api.tokenrouter.com/v1)
      - Ollama (http://localhost:11434/v1) — set api_key to "ollama"
      - LocalAI (http://localhost:8080/v1) — set api_key to any string

    Endpoint: POST {base_url}/chat/completions
    Auth: Bearer token
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, api_key=api_key, model=model, **kwargs)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

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
            raise LLMError(f"{self.name}: API key not configured")
        if not self.base_url:
            raise LLMError(f"{self.name}: base_url not configured")

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

        url = f"{self.base_url}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise LLMError(
                    f"{self.name} HTTP {resp.status_code}: {resp.text[:300]}"
                )
            data = resp.json()
        except httpx.HTTPError as e:
            raise LLMError(f"{self.name} request failed: {e!s}") from e
        except Exception as e:  # noqa: BLE001
            raise LLMError(f"{self.name} parse failed: {e!s}") from e

        try:
            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
        except (KeyError, IndexError) as e:
            raise LLMError(f"Malformed {self.name} response: {e}") from e

        return LLMResult(
            content=content,
            provider=self.name,
            model=self.model,
            tokens_used=tokens,
            raw=data,
        )


class GeminiProvider(BaseProvider):
    """Google Gemini — uses its own protocol (NOT OpenAI-compatible)."""

    DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        name: str = "gemini",
        api_key: str = "",
        model: str = "gemini-1.5-flash",
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, api_key=api_key, model=model, **kwargs)
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")

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
            raise LLMError("Gemini: API key not configured")

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

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise LLMError(
                    f"Gemini HTTP {resp.status_code}: {resp.text[:300]}"
                )
            data = resp.json()
        except httpx.HTTPError as e:
            raise LLMError(f"Gemini request failed: {e!s}") from e

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


# --- Provider configuration ---

# Known OpenAI-compatible providers with default base URLs
KNOWN_OAI_BASE_URLS: dict[str, str] = {
    "groq": "https://api.groq.com/openai/v1",
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "together": "https://api.together.xyz/v1",
    "anyscale": "https://api.endpoints.anyscale.com/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
    "deepinfra": "https://api.deepinfra.com/v1/openai",
    "ollama": "http://localhost:11434/v1",
    "lmstudio": "http://localhost:1234/v1",
    "localai": "http://localhost:8080/v1",
    "vllm": "http://localhost:8000/v1",
    "custom": "",  # must provide base_url
    "tokenrouter": "https://api.tokenrouter.com/v1",  # the user's custom
}


def _resolve_base_url(name: str, type_: str, override: str | None) -> str:
    """Pick the right base URL based on provider name + override."""
    if override:
        return override
    if type_ == "gemini":
        return GeminiProvider.DEFAULT_BASE_URL
    return KNOWN_OAI_BASE_URLS.get(name.lower(), "")


def _build_provider(entry: dict[str, Any]) -> BaseProvider:
    """Build a provider instance from a config dict."""
    name = entry.get("name") or entry.get("type", "custom")
    type_ = (entry.get("type") or "").lower()
    if not type_:
        # Infer type from name
        if name.lower() == "gemini":
            type_ = "gemini"
        else:
            type_ = "openai-compatible"

    api_key = entry.get("api_key", "")
    model = entry.get("model", "")
    base_url = _resolve_base_url(
        name, type_, entry.get("base_url") or None
    )

    if type_ == "gemini":
        return GeminiProvider(
            name=name,
            api_key=api_key,
            model=model,
            base_url=entry.get("base_url") or None,
        )
    # Default: OpenAI-compatible
    if not base_url:
        raise ValueError(
            f"Provider {name!r} needs base_url (not in KNOWN_OAI_BASE_URLS)"
        )
    return OpenAICompatibleProvider(
        name=name,
        base_url=base_url,
        api_key=api_key,
        model=model,
    )


def _parse_providers_json() -> list[dict[str, Any]] | None:
    """
    Parse LLM_PROVIDERS_JSON env var. If unset, returns None
    (caller falls back to legacy primary+fallback config).
    """
    raw = settings.llm_providers_json.strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning(
            "LLM_PROVIDERS_JSON malformed (falling back to simple config): %s", e
        )
        return None
    if not isinstance(data, list):
        logger.warning("LLM_PROVIDERS_JSON must be a list, got %s", type(data).__name__)
        return None
    return data


def _load_legacy_config() -> list[dict[str, Any]]:
    """
    Build provider list from simple LLM_PRIMARY_* + LLM_FALLBACK_* env vars.
    Backward-compatible with v1.
    """
    entries: list[dict[str, Any]] = []
    if settings.llm_primary_model and settings.llm_primary_api_key:
        entries.append({
            "name": settings.llm_primary_provider,
            "type": "openai-compatible"
            if settings.llm_primary_provider != "gemini"
            else "gemini",
            "api_key": settings.llm_primary_api_key,
            "model": settings.llm_primary_model,
            "base_url": settings.llm_primary_base_url,
            "enabled": True,
            "order": 1,
            "display_name": "primary",
        })
    if settings.llm_fallback_model and settings.llm_fallback_api_key:
        entries.append({
            "name": settings.llm_fallback_provider,
            "type": "openai-compatible"
            if settings.llm_fallback_provider != "gemini"
            else "gemini",
            "api_key": settings.llm_fallback_api_key,
            "model": settings.llm_fallback_model,
            "base_url": settings.llm_fallback_base_url,
            "enabled": True,
            "order": 2,
            "display_name": "fallback",
        })
    return entries


def get_active_providers() -> list[dict[str, Any]]:
    """
    Return the configured provider chain (for the /ai/providers endpoint).
    Each entry: name, type, model, enabled, order, configured, base_url.
    """
    raw = _parse_providers_json() or _load_legacy_config()
    out: list[dict[str, Any]] = []
    for entry in raw:
        out.append(
            {
                "name": entry.get("name", "?"),
                "type": entry.get("type", "openai-compatible"),
                "model": entry.get("model", "?"),
                "enabled": entry.get("enabled", True),
                "order": entry.get("order", 0),
                "display_name": entry.get("display_name"),
                "configured": bool(
                    entry.get("api_key")
                    and not str(entry.get("api_key", "")).startswith("PLACEHOLDER")
                ),
                "base_url": _resolve_base_url(
                    entry.get("name", ""),
                    entry.get("type", "openai-compatible"),
                    entry.get("base_url") or None,
                ),
            }
        )
    out.sort(key=lambda p: p["order"])
    return out


def _build_chain() -> list[BaseProvider]:
    """Build the active provider chain, sorted by order, enabled first."""
    raw = _parse_providers_json() or _load_legacy_config()
    chain: list[BaseProvider] = []
    for entry in raw:
        if not entry.get("enabled", True):
            continue
        if not entry.get("api_key") or str(entry.get("api_key")).startswith(
            "PLACEHOLDER"
        ):
            continue
        try:
            chain.append(_build_provider(entry))
        except Exception as e:  # noqa: BLE001
            logger.warning("Skip provider %r: %s", entry.get("name"), e)
    chain.sort(
        key=lambda p: next(
            (
                e.get("order", 999)
                for e in (raw or [])
                if e.get("name") == p.name
            ),
            999,
        )
    )
    return chain


# --- Public API ---

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
    Try the configured provider chain in order until one succeeds.

    - prefer_fallback=True → try fallback first (for testing).
    - On total failure → raises LLMError.
    - Template fallback is the caller's responsibility (see
      app/services/analyzer/hook_generator.py).
    """
    chain = _build_chain()
    if prefer_fallback:
        chain = list(reversed(chain))

    if not chain:
        raise LLMError(
            "No LLM providers configured. Set LLM_PROVIDERS_JSON or "
            "LLM_PRIMARY_API_KEY in .env"
        )

    last_err: str | None = None
    for provider in chain:
        try:
            return await provider.complete(
                system=system,
                user=user,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )
        except LLMError as e:
            logger.warning("Provider %s failed: %s", provider.name, e)
            last_err = str(e)
    raise LLMError(f"All providers failed. Last: {last_err}")


# --- JSON parsing (response-side, not config) ---

def safe_parse_json(text: str) -> dict | list | None:
    """
    Extract JSON from LLM response. Handles ```json code blocks
    and bare JSON. Returns None if parsing fails.
    """
    import re

    if not text:
        return None
    fence_match = re.search(
        r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL
    )
    if fence_match:
        text = fence_match.group(1)
    text = text.strip()
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
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
