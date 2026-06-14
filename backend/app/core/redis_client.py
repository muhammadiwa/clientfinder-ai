"""
Redis client (T8 — used by rate limiting + monitoring).

For v1: in-memory rate limiting (slowapi). Redis is optional
storage; falls back to in-memory if Redis is unavailable.
"""
from __future__ import annotations

import logging

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger("clientfinder.redis")

_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get (or create) the async Redis client.

    Falls back to in-memory (returns a fake client) if connection
    fails — for v1 development convenience.
    """
    global _client
    if _client is None:
        try:
            _client = aioredis.from_url(
                settings.redis_url,
                max_connections=settings.redis_max_connections,
                decode_responses=True,
            )
            # Quick ping to verify
            await _client.ping()
        except Exception as e:  # noqa: BLE001
            logger.warning("Redis unavailable (%s), using fake client", e)
            _client = _FakeRedis()
    return _client


class _FakeRedis:
    """Fallback fake (no-op) Redis client for when Redis is down.

    Used for in-memory rate limiting fallback + health check.
    """

    async def ping(self) -> bool:
        return False

    async def get(self, _key: str) -> str | None:
        return None

    async def set(self, _key: str, _value: str, ex: int | None = None) -> bool:
        return True

    async def incr(self, _key: str) -> int:
        return 0

    async def expire(self, _key: str, _time: int) -> bool:
        return True
